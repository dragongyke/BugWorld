"""Convert the approved LDR sky to a linear floating-point IBL cubemap.

This does not recover HDR radiance or add new artwork. The 256px / five-level
GGX reflection pyramid and nine pre-scaled diffuse SH coefficients follow the
public Filament IBL profile also found in Spatial Editor's built-in environment.
KTX1 header fields follow Khronos, including the packed-float GL data type.

References (equations/file layout, no external pixels):
https://registry.khronos.org/KTX/specs/1.0/ktxspec.v1.html
https://github.com/google/filament/blob/main/tools/cmgen/src/cmgen.cpp
https://github.com/google/filament/blob/main/libs/ibl/src/CubemapIBL.cpp
https://github.com/google/filament/blob/main/libs/ibl/src/CubemapSH.cpp

Run with Python + NumPy + Pillow. --check validates the checked-in asset only.
The script tests its numerical conventions before generating or validating.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'app/src/main/assets/v3/environment/sky.png'
OUTPUT = SOURCE.with_suffix('.ktx')
MAGIC = b'\xabKTX 11\xbb\r\n\x1a\n'
SIZE, LEVELS, SAMPLES = 256, 5, 1024
FACES = ('+X', '-X', '+Y', '-Y', '+Z', '-Z')
# GL_UNSIGNED_INT_10F_11F_11F_REV, sizeof(uint32), GL_RGB, GL_R11F_G11F_B10F.
FORMAT = (0x8C3B, 4, 0x1907, 0x8C3A, 0x1907)


def srgb_to_linear(rgb):
    return np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4)


def directions(face, size, offset=(.5, .5)):
    u, v = np.meshgrid((np.arange(size) + offset[0]) * 2 / size - 1,
                       (np.arange(size) + offset[1]) * 2 / size - 1)
    one = np.ones_like(u)
    xyz = ((one, -v, -u), (-one, -v, u), (u, one, v),
           (u, -one, -v), (u, -v, one), (-u, -v, -one))[face]
    d = np.stack(xyz, axis=-1)
    return (d / np.linalg.norm(d, axis=-1, keepdims=True)).astype(np.float32)


def panorama_sample(image, d):
    """Y-up; matches cmgen's default X mirror. Top input row is the north pole."""
    height, width = image.shape[:2]
    u = (.5 + np.arctan2(-d[..., 0], d[..., 2]) / (2 * np.pi)) * width - .5
    v = (.5 - np.arcsin(np.clip(d[..., 1], -1, 1)) / np.pi) * height - .5
    v = np.clip(v, 0, height - 1)
    x, y = np.floor(u).astype(np.int32), np.floor(v).astype(np.int32)
    fx, fy = (u - x)[..., None], (v - y)[..., None]
    upper = image[y, x % width] * (1 - fx) + image[y, (x + 1) % width] * fx
    lower = image[np.minimum(y + 1, height - 1), x % width] * (1 - fx)
    lower += image[np.minimum(y + 1, height - 1), (x + 1) % width] * fx
    return (upper * (1 - fy) + lower * fy).astype(np.float32)


def cube_base(image, size):
    # Four samples per output texel reduce aliasing without gamma-space averaging.
    return np.stack([sum(panorama_sample(image, directions(f, size, (u, v)))
                         for u in (.25, .75) for v in (.25, .75)) * .25
                     for f in range(6)])


def solid_angles(size):
    a, b = np.meshgrid(np.arange(size + 1) * 2 / size - 1,
                       np.arange(size + 1) * 2 / size - 1)
    area = np.arctan2(a * b, np.sqrt(a * a + b * b + 1))
    return area[:-1, :-1] - area[1:, :-1] - area[:-1, 1:] + area[1:, 1:]


def diffuse_sh(cube):
    """Lambert convolution / pi, including polynomial reconstruction factors."""
    size = cube.shape[1]
    omega = solid_angles(size)
    coefficients = np.zeros((9, 3), np.float64)
    for face in range(6):
        x, y, z = np.moveaxis(directions(face, size).astype(np.float64), -1, 0)
        polynomial = np.stack((np.ones_like(x), y, z, x, x*y, y*z,
                               3*z*z-1, x*z, x*x-y*y))
        coefficients += np.einsum('ihw,hw,hwc->ic', polynomial, omega, cube[face])
    scale = np.array((1/4, 1/2, 1/2, 1/2, 15/16, 15/16, 5/64, 15/16, 15/64)) / np.pi
    return coefficients * scale[:, None]


def hammersley(count):
    bits = np.arange(count, dtype=np.uint32)
    reverse = np.zeros(count, dtype=np.uint32)
    for _ in range(32):
        reverse = (reverse << 1) | (bits & 1)
        bits >>= 1
    return np.arange(count, dtype=np.float64) / count, reverse.astype(np.float64) / 2**32


def ggx_prefilter(image, size, perceptual_roughness, samples):
    """Normalized GGX importance integration from the original linear panorama.

    Direct importance sampling (cmgen's --ibl-no-prefilter formulation), so these
    mip levels encode roughness, rather than ordinary resized images.
    """
    alpha = perceptual_roughness ** 2
    a, b = hammersley(samples)
    phi = 2 * np.pi * a
    cos_h = np.sqrt((1 - b) / (1 + (alpha * alpha - 1) * b))
    sin_h = np.sqrt(np.maximum(0, 1 - cos_h * cos_h))
    local = np.stack((2*cos_h*sin_h*np.cos(phi), 2*cos_h*sin_h*np.sin(phi),
                      2*cos_h*cos_h-1), axis=-1)
    local = local[local[:, 2] > 0].astype(np.float32)
    weights = local[:, 2] / local[:, 2].sum()
    result = np.empty((6, size, size, 3), np.float32)
    for face in range(6):
        normals = directions(face, size).reshape(-1, 3)
        flat = result[face].reshape(-1, 3)
        # Bounded working memory, independent of face size and sample count.
        for start in range(0, len(normals), 128):
            n = normals[start:start+128]
            up = np.zeros_like(n)
            up[:, 2] = 1
            up[np.abs(n[:, 2]) > .999] = (1, 0, 0)
            tangent = np.cross(up, n)
            tangent /= np.linalg.norm(tangent, axis=1, keepdims=True)
            bitangent = np.cross(n, tangent)
            d = (tangent[:, None, :] * local[None, :, 0:1]
                 + bitangent[:, None, :] * local[None, :, 1:2]
                 + n[:, None, :] * local[None, :, 2:3])
            colors = panorama_sample(image, d)
            flat[start:start+len(n)] = np.einsum('psc,s->pc', colors, weights)
    return result


def pack_float_channel(values, mantissa_bits):
    values = np.asarray(values, np.float64)
    assert np.isfinite(values).all() and (values >= 0).all() and (values <= 64512).all()
    fraction, exponent = np.frexp(values)
    exponent -= 1
    # Rounding can carry into the next exponent; integer addition handles this.
    normal = ((exponent + 15) << mantissa_bits) + np.rint((fraction * 2 - 1) * 2**mantissa_bits).astype(np.int64)
    subnormal = np.rint(values * 2**(14 + mantissa_bits)).astype(np.int64)
    return np.where(values < 2**-14, subnormal, normal).astype(np.uint32)


def packed_rgb(rgb):
    r, g, b = np.moveaxis(rgb, -1, 0)
    return (pack_float_channel(r, 6) | (pack_float_channel(g, 6) << 11)
            | (pack_float_channel(b, 5) << 22)).astype('<u4')


def unpacked_rgb(packed):
    channels = []
    for shift, mantissa in ((0, 6), (11, 6), (22, 5)):
        channel = (packed >> shift) & ((1 << (mantissa + 5)) - 1)
        exponent, fraction = channel >> mantissa, channel & ((1 << mantissa) - 1)
        assert (exponent < 31).all(), 'Non-finite packed float'
        channels.append(np.where(exponent == 0, fraction * 2.0**(-14-mantissa),
                                 (1 + fraction / 2**mantissa) * 2.0**(exponent.astype(int)-15)))
    return np.stack(channels, axis=-1)


def write_ktx(path, levels, sh, source_hash, source_range='LDR sRGB converted to linear float; no recovered HDR radiance'):
    metadata = {'sh': ''.join(' '.join(f'{c:.9g}' for c in row) + '\n' for row in sh),
                'sourceSHA256': source_hash,
                'sourceRange': source_range,
                'filter': 'GGX reflection levels; three-band diffuse SH; cmgen default orientation'}
    key_values = bytearray()
    for key, value in metadata.items():
        data = key.encode() + b'\0' + value.encode() + b'\0'
        key_values += struct.pack('<I', len(data)) + data + bytes((-len(data)) % 4)
    size = levels[0].shape[1]
    header = struct.pack('<13I', 0x04030201, *FORMAT, size, size, 0, 0, 6, len(levels), len(key_values))
    with path.open('wb') as stream:
        stream.write(MAGIC + header + key_values)
        for level in levels:
            face_bytes = level.shape[1] ** 2 * 4
            stream.write(struct.pack('<I', face_bytes))
            stream.write(packed_rgb(level).tobytes())


def validate(path, source_hash, max_linear=1.):
    data = path.read_bytes()
    assert data[:12] == MAGIC
    header = struct.unpack_from('<13I', data, 12)
    assert header[:6] == (0x04030201, *FORMAT)
    assert header[6:12] == (SIZE, SIZE, 0, 0, 6, LEVELS)
    cursor, metadata_end, metadata = 64, 64 + header[12], {}
    while cursor < metadata_end:
        count = struct.unpack_from('<I', data, cursor)[0]
        cursor += 4
        key, value = data[cursor:cursor+count].split(b'\0', 1)
        metadata[key.decode()] = value.rstrip(b'\0').decode()
        cursor += (count + 3) & ~3
    assert cursor == metadata_end and metadata['sourceSHA256'] == source_hash
    sh = np.fromstring(metadata['sh'], sep=' ')
    assert len(sh) == 27 and np.isfinite(sh).all()
    mips = []
    for index in range(LEVELS):
        size = SIZE >> index
        count = struct.unpack_from('<I', data, cursor)[0]
        cursor += 4
        assert count == size * size * 4 and cursor % 4 == 0
        values = unpacked_rgb(np.frombuffer(data, '<u4', 6*size*size, cursor))
        assert (values >= 0).all()
        if max_linear is not None:
            assert (values <= max_linear).all(), 'Source radiance range changed'
        mips.append({'level': index, 'size': size, 'faceBytes': count,
                     'linearMin': float(values.min()), 'linearMax': float(values.max())})
        cursor += 6 * count
    assert cursor == len(data), 'Truncated or trailing payload'
    return {'sourceSHA256': source_hash, 'outputSHA256': hashlib.sha256(data).hexdigest(),
            'bytes': len(data), 'format': 'KTX1 R11F_G11F_B10F linear', 'sourceRange': metadata['sourceRange'],
            'faceOrder': FACES, 'mips': mips, 'diffuseSH': sh.reshape(9, 3).tolist()}


def self_test():
    assert abs(float(srgb_to_linear(np.array(.5))) - .21404114) < 1e-7
    axes = np.array(((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)))
    np.testing.assert_allclose(np.stack([directions(f, 1)[0,0] for f in range(6)]), axes)
    assert abs(solid_angles(32).sum()*6 - 4*np.pi) < 1e-10
    color = np.array((.125, .25, .5), np.float32)
    constant = np.broadcast_to(color, (6,32,32,3))
    coefficients = diffuse_sh(constant)
    np.testing.assert_allclose(coefficients[0], color, atol=1e-8)
    np.testing.assert_allclose(coefficients[1:], 0, atol=1e-7)
    ramp = np.stack([np.broadcast_to((1+.3*directions(f,32)[...,1:2]), (32,32,3)) for f in range(6)])
    ramp_sh = diffuse_sh(ramp)
    np.testing.assert_allclose(ramp_sh[0], 1, atol=1e-6)
    np.testing.assert_allclose(ramp_sh[1], .2, atol=1e-5)
    np.testing.assert_allclose(ramp_sh[2:], 0, atol=1e-6)
    filtered = ggx_prefilter(np.broadcast_to(color, (16,32,3)), 4, .7, 64)
    np.testing.assert_allclose(filtered, np.broadcast_to(color, filtered.shape), atol=1e-6)
    reference = np.array(((0,1,.5), (2**-20,2**-19,2**-19), (10,100,1000)), np.float64)
    np.testing.assert_allclose(unpacked_rgb(packed_rgb(reference)), reference, rtol=.016, atol=2**-19)
    assert int(packed_rgb(np.ones(3))) == 0x781E03C0
    print('PASS: transfer curve, six axes, solid angles, constant/directional SH, GGX energy, packed floats', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    self_test()
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if not args.check:
        with Image.open(SOURCE) as image:
            assert image.width == 2 * image.height and image.mode == 'RGB'
            linear = srgb_to_linear(np.asarray(image, np.float32) / 255)
        levels = [cube_base(linear, SIZE)]
        sh = diffuse_sh(levels[0])
        for index in range(1, LEVELS):
            roughness = 1 - math.sqrt(1 - index / (LEVELS - 1))
            samples = SAMPLES * 2**max(0, index - 1)
            print(f'GGX level {index}: {SIZE >> index}px, perceptual roughness {roughness:.6f}, {samples} samples', flush=True)
            levels.append(ggx_prefilter(linear, SIZE >> index, roughness, samples))
        write_ktx(OUTPUT, levels, sh, source_hash)
    print(json.dumps(validate(OUTPUT, source_hash), indent=2))


if __name__ == '__main__':
    main()
