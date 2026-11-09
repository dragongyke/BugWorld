"""Assemble unchanged asset render previews into a labelled review contact sheet."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

root = Path(__file__).resolve().parents[1] / 'assets-src/v3-review'
im = Image.new('RGB', (1600, 1580), '#f6f3ef')
draw = ImageDraw.Draw(im)
font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 30)
small = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 21)
draw.text((40, 26), 'BugWorld · 四种实际模型', font=font, fill='#51435b')
draw.text((40, 73), '真实 Blender 资产渲染 · 固定示例配色 · 尚未接入应用', font=small, fill='#827589')
items = [
    ('蝴蝶', 'butterfly/03-natural-leaf-closeup.png'),
    ('独角仙', 'beetle/natural_setting.png'),
    ('瓢虫', 'ladybug/natural_setting.png'),
    ('毛毛虫', 'caterpillar/03-natural-leaf-closeup.png')
]
for i, (title, relative) in enumerate(items):
    x, y = 40+(i%2)*780, 122+(i//2)*710
    picture = Image.open(root/relative).convert('RGB')
    thumb = ImageOps.contain(picture, (740, 640), Image.Resampling.LANCZOS)
    im.paste(thumb, (x+(740-thumb.width)//2, y+(640-thumb.height)//2))
    draw.text((x+16, y+652), title, font=font, fill='#51435b')
im.save(root/'models-overview.png')
print(root/'models-overview.png')
