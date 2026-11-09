"""Explicit native materials for the garden import compatibility review.

This writes review assets only. Applying them to an editor scene is a separate
validated MCP operation; it never changes the installed Android application.
"""
from pathlib import Path
import json
import shutil
import struct

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets-src/emerald-native-materials"
OUT.mkdir(exist_ok=True)
(OUT / "Textures").mkdir(exist_ok=True)


def copy(source, name):
    path = OUT / "Textures" / name
    shutil.copy2(source, path)
    return path.as_posix()


def material(name, albedo, roughness, normal=None, normal_scale=.5, uv_scale=1):
    p = f"/Root/{name}"
    normal_input = f"float3 inputs:normal.connect = <{p}/Normal.outputs:out>" if normal else ""
    normal_nodes = f'''
        def Shader "NormalImage" {{
            uniform token info:id = "ND_image_vector3"
            asset inputs:file = @{normal}@
            float2 inputs:texcoord.connect = <{p}/UVScale.outputs:out>
            float3 outputs:out
        }}
        def Shader "Normal" {{
            uniform token info:id = "ND_normalmap"
            float3 inputs:in.connect = <{p}/NormalImage.outputs:out>
            float3 inputs:normal = (0, 0, 1)
            float3 inputs:tangent = (1, 0, 0)
            float inputs:scale = {normal_scale}
            string inputs:space = "tangent"
            float3 outputs:out
        }}''' if normal else ""
    source = f'''#usda 1.0
(
    defaultPrim = "Root"
    metersPerUnit = 1
)
def Xform "Root" {{
    def Material "{name}" (
        customData = {{
            string materialType = "SHADER_GRAPH"
            string blendingMode = "OPAQUE"
            string cullingMode = "NONE"
            bool depthWrite = 1
            bool depthTest = 1
            bool applyToneMapping = 1
        }}
    ) {{
        token outputs:mtlx:surface.connect = <{p}/Surface.outputs:out>
        def Shader "Surface" {{
            uniform token info:id = "ND_UsdPreviewSurface_surfaceshader"
            color3f inputs:diffuseColor.connect = <{p}/LinearColor.outputs:out>
            float inputs:metallic = 0
            float inputs:roughness = {roughness}
            float inputs:opacity = 1
            {normal_input}
            token outputs:out
        }}
        def Shader "UV" {{
            uniform token info:id = "ND_texcoord_vector2"
            int inputs:index = 0
            float2 outputs:out
        }}
        def Shader "Albedo" {{
            uniform token info:id = "ND_image_color3"
            asset inputs:file = @{albedo}@
            float2 inputs:texcoord.connect = <{p}/UVScale.outputs:out>
            color3f outputs:out
        }}
        def Shader "UVScale" {{
            uniform token info:id = "ND_multiply_vector2FA"
            float2 inputs:in1.connect = <{p}/UV.outputs:out>
            float inputs:in2 = {uv_scale}
            float2 outputs:out
        }}
        def Shader "LinearColor" {{
            uniform token info:id = "ND_power_color3FA"
            color3f inputs:in1.connect = <{p}/Albedo.outputs:out>
            float inputs:in2 = 2.2
            color3f outputs:out
        }}
        {normal_nodes}
    }}
}}
'''
    return "\n".join(line.rstrip() for line in source.splitlines()) + "\n"


forest = ROOT / "assets-src/emerald-forest-v2"
rock = forest / "sources/rock_moss_set_01/textures"
albedo = copy(rock / "rock_moss_set_01_diff_1k.jpg", "RockAlbedo.jpg")
normal = copy(rock / "rock_moss_set_01_nor_gl_1k.jpg", "RockNormal.jpg")
(OUT / "Rock.usda").write_text(material("Rock", albedo, .78, normal), encoding="utf8")
petals = copy(forest / "textures/lotus_petal_daylight.png", "Petal.png")
(OUT / "Petal.usda").write_text(material("Petal", petals, .46), encoding="utf8")
raw = (forest / 'garden.glb').read_bytes()
length = struct.unpack_from('<I', raw, 12)[0]
gltf = json.loads(raw[20:20+length])
binary = raw[28+length:]
def extract_image(name):
    entry = next(im for im in gltf['images'] if im.get('name') == name)
    view = gltf['bufferViews'][entry['bufferView']]
    start = view.get('byteOffset', 0)
    extension = '.jpg' if entry.get('mimeType') == 'image/jpeg' else '.png'
    path = OUT / 'Textures' / (name + extension)
    path.write_bytes(binary[start:start+view['byteLength']])
    return path.as_posix()
leaf = extract_image('lotus_emerald_pigment')
leaf_normal = extract_image('lotus_leaf_normal')
bank = copy(forest/'sources/forest_leaves_02/forest_leaves_02_diffuse_1k.jpg','BankAlbedo.jpg')
bank_normal = copy(forest/'sources/forest_leaves_02/forest_leaves_02_nor_gl_1k.jpg','BankNormal.jpg')
(OUT/'Leaf.usda').write_text(material('Leaf', leaf, .50, leaf_normal, .16), encoding='utf8')
(OUT/'Bank.usda').write_text(material('Bank', bank, .91, bank_normal, .35), encoding='utf8')
fern_image = extract_image('fern_02_diff-fern_02_alpha-fern_02_alpha_1k')
fern_normal = extract_image('fern_02_nor_gl_1k')
fern = material('Fern', fern_image, .8, fern_normal, .3)
fern = fern.replace('string blendingMode = "OPAQUE"',
                    'string blendingMode = "MASKED"\n            float opacityThreshold = 0.45')
fern = fern.replace('float inputs:opacity = 1',
                    'float inputs:opacity.connect = </Root/Fern/Alpha.outputs:out>\n            float inputs:opacityThreshold = 0.45')
fern = fern.replace('        def Shader "UV"', f'''        def Shader "AlphaImage" {{
            uniform token info:id = "ND_image_color4"
            asset inputs:file = @{fern_image}@
            float2 inputs:texcoord.connect = </Root/Fern/UVScale.outputs:out>
            color4f outputs:out
        }}
        def Shader "Alpha" {{
            uniform token info:id = "ND_extract_color4"
            color4f inputs:in.connect = </Root/Fern/AlphaImage.outputs:out>
            int inputs:index = 3
            float outputs:out
        }}
        def Shader "UV"''')
(OUT/'Fern.usda').write_text(fern, encoding='utf8')
# Scan-model rock maps are atlases, not tileable: repeating them on the bed
# exposed their empty atlas cells as a broad dark stripe in the native view.
bed = material('Bed',bank,.91,bank_normal,.20,6)
bed = bed.replace('color3f inputs:diffuseColor.connect = </Root/Bed/LinearColor.outputs:out>',
                  'color3f inputs:diffuseColor.connect = </Root/Bed/SubmergedTint.outputs:out>')
bed = bed.replace('        def Shader "UV"', '''        def Shader "SubmergedTint" {
            uniform token info:id = "ND_multiply_color3"
            color3f inputs:in1.connect = </Root/Bed/LinearColor.outputs:out>
            color3f inputs:in2 = (0.22, 0.53, 0.38)
            color3f outputs:out
        }
        def Shader "UV"''')
(OUT/'Bed.usda').write_text(bed,encoding='utf8')
water_normal = copy(forest / "textures/water_fine_ripple_normal.png", "WaterNormal.png")
water = (ROOT / "assets-src/emerald-water-editor/Sources/Materials/EmeraldWater.usda").read_text(encoding="utf8")
water = water.replace("../Textures/WaterNormal.png", water_normal)
# The probe covers 4 m, while the garden UV spans 12 m. Preserve ripple size and
# reduce slope so the bright reverse view remains a calm pond, not white surf.
water = water.replace("(0.006, 0.025, 0.018)", "(0.02, 0.07, 0.055)")
water = water.replace("float inputs:roughness = 0.06", "float inputs:roughness = 0.10")
water = water.replace("float inputs:scale = 2.0", "float inputs:scale = 0.4")
water = water.replace("</Root/EmeraldWater/UV.outputs:out>",
                      "</Root/EmeraldWater/PondUV.outputs:out>")
water = water.replace('        def Shader "Time"', '''        def Shader "PondUV"
        {
            uniform token info:id = "ND_multiply_vector2FA"
            float2 inputs:in1.connect = </Root/EmeraldWater/UV.outputs:out>
            float inputs:in2 = 3
            float2 outputs:out
        }
        def Shader "Time"''')
(OUT / "Water.usda").write_text(water, encoding="utf8")
shallow = water.replace('string blendingMode = "OPAQUE"', 'string blendingMode = "TRANSPARENT"')
shallow = shallow.replace('bool depthWrite = 1', 'bool depthWrite = 0')
shallow = shallow.replace('float inputs:opacity = 1', 'float inputs:opacity = 0.65')
shallow = shallow.replace('(0.02, 0.07, 0.055)', '(0.01, 0.035, 0.022)')
(OUT / 'WaterShallow.usda').write_text(shallow, encoding='utf8')
(OUT / "bindings.json").write_text(json.dumps({
    "Rock.usda": "/Root/garden/bank_moss_stones",
    "Petal.usda": "/Root/garden/detail_lotus_petal",
    "Leaf.usda": "/Root/garden/observe_front_right",
    "Bank.usda": "/Root/garden/compact_forest_bank",
    "Fern.usda": "/Root/garden/shore_ferns",
    "Bed.usda": "/Root/garden/pond_bed",
    "WaterShallow.usda": "/Root/garden/pond_water",
}, indent=2), encoding="utf8")
print(OUT)
