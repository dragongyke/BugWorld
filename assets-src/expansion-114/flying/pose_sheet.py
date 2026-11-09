"""Assemble the six clean-import frame renders at their native pixel size."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[3]
def assemble(slug):
    out=ROOT/'assets-src/expansion-114'/slug
    image=Image.new('RGB',(1128,690),'#f7f4e9')
    draw=ImageDraw.Draw(image)
    title=ImageFont.truetype('C:/Windows/Fonts/georgia.ttf',27)
    label=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',18)
    draw.text((18,13),f'{slug.capitalize()}  /  exported GLB poses',font=title,fill='#3b352d')
    for i,clip in enumerate(['idle','walk','takeoff','flight','touch','perch']):
        p=Image.open(out/(clip+'-pose.png')).convert('RGB')
        x=12+(i%3)*372;y=61+(i//3)*315
        image.paste(p,(x,y))
        draw.text((x+4,y+279),clip,font=label,fill='#453e30')
    image.save(out/'animation-contact.png',optimize=True)
if __name__=='__main__':
    for s in ['dragonfly','honeybee']:assemble(s)
