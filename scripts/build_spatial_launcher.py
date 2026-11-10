"""Bake the Android vector artwork into PICO's ordered color and distance layers."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import cv2
import numpy as np
from PIL import Image, ImageDraw

RES = Path(__file__).resolve().parents[1] / "app/src/main/res"
DRAWABLE = RES / "drawable"
ANDROID = "{http://schemas.android.com/apk/res/android}"
SIZE = 1024


def sample_path(data):
    paths = []
    for command, values in re.findall(r"([MCQZ])([^MCQZ]*)", data):
        numbers = list(map(float, re.findall(r"-?\d+(?:\.\d+)?", values)))
        points = np.array(numbers).reshape(-1, 2)
        if command == "M":
            paths.append([points[0]])
        elif command == "Z":
            paths[-1].append(paths[-1][0])
        else:
            start = paths[-1][-1]
            for t in np.linspace(0, 1, 65)[1:]:
                u = 1 - t
                if command == "Q":
                    position = u*u*start + 2*u*t*points[0] + t*t*points[1]
                else:
                    position = u**3*start + 3*u*u*t*points[0] + 3*u*t*t*points[1] + t**3*points[2]
                paths[-1].append(position)
    return paths


def save_layer(layer, index):
    layer = layer.resize((SIZE, SIZE), Image.Resampling.LANCZOS)
    layer.save(DRAWABLE / f"icon_3d_layer_{index}.png", optimize=True)
    alpha = np.asarray(layer.getchannel("A"))
    solid = (alpha >= 128).astype(np.uint8)
    inner = cv2.distanceTransform(solid, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    outer = cv2.distanceTransform(1 - solid, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    distance = np.clip(128 + (inner - outer) * 9, 0, 255).astype(np.uint8)
    field = Image.fromarray(distance)
    Image.merge("RGBA", (field, field, field, Image.fromarray(alpha))).save(
        DRAWABLE / f"icon_3d_sdf_{index}.png", optimize=True)
    return layer


def main():
    scale = 2
    extent = SIZE * scale
    canvas = (extent, extent)
    background = Image.new("RGBA", canvas)
    color = ET.parse(RES / "values/launcher_colors.xml").getroot().findtext("color")
    ImageDraw.Draw(background).rounded_rectangle((0, 0, extent-1, extent-1), radius=extent*.22, fill=color)
    foreground = Image.new("RGBA", canvas)
    draw = ImageDraw.Draw(foreground)
    multiplier = extent / 108
    for element in ET.parse(DRAWABLE / "ic_launcher_foreground.xml").getroot():
        attrs = element.attrib
        for path in sample_path(attrs[ANDROID + "pathData"]):
            points = [tuple(point * multiplier) for point in path]
            if ANDROID + "fillColor" in attrs:
                draw.polygon(points, fill=attrs[ANDROID + "fillColor"])
            else:
                width = round(float(attrs[ANDROID + "strokeWidth"]) * multiplier)
                draw.line(points, fill=attrs[ANDROID + "strokeColor"], width=width, joint="curve")
    preview = Image.alpha_composite(save_layer(background, 0), save_layer(foreground, 1))
    fallback = RES / "mipmap-xxxhdpi"
    fallback.mkdir(exist_ok=True)
    preview.resize((512, 512), Image.Resampling.LANCZOS).save(fallback / "ic_spatial_launcher.png", optimize=True)


if __name__ == "__main__":
    main()
