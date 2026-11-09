"""Deliverable BugWorld SVG UI assets and an honest asset-only composition board.

Only writes assets-src/v3-review/ui. No app code, conceptual-image sampling,
or changes to the root review page. Rasterization uses the bundled sharp.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes as W
import html
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets-src/v3-review/ui'
LINEART=ROOT/'assets-src/v3-review/lineart'
RUNTIME=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies'
NODE=Path(os.environ.get('BUGWORLD_NODE',str(RUNTIME/'node/bin/node.exe')))
SHARP=os.environ.get('BUGWORLD_SHARP',str(RUNTIME/'node/node_modules/sharp'))
INK='#55416e'
MUTED='#93849d'
ACCENT='#9778be'
BORDER='#e8deed'
PAPER='#fffdf8'
FONT='Microsoft YaHei, sans-serif'


def svg(body,w,h,title):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><title>{html.escape(title)}</title>{body}</svg>'


def p(d,fill='none',stroke=INK,width=1.65):
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>'


def rect(x,y,w,h,r,fill,stroke='none',sw=1,extra=''):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" {extra}/>'


def text(x,y,value,size=24,color=INK,weight=400,anchor='start'):
    return f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{html.escape(value)}</text>'


def fragment(file,prefix=''):
    content=file.read_text(encoding='utf-8')
    content=re.sub(r'^.*?<svg\b[^>]*>','',content,flags=re.S)
    content=re.sub(r'</svg>\s*$','',content)
    content=re.sub(r'<title>.*?</title>','',content,flags=re.S)
    if prefix:
        content=re.sub(r'\bid="([^"]+)"',lambda m:f'id="{prefix}-{m[1]}"',content)
    return content


def placed(content,x,y,width,source=24):
    return f'<g transform="translate({x} {y}) scale({width/source})">{content}</g>'


def make_tools():
    tools={
        'crayon':p('M4 20 L6 14 L16 4 C17 3 18 3 19 4 L20 5 C21 6 21 7 20 8 L10 18 Z')+p('M6 14 L10 18 M14 6 L18 10 M16 4 L20 8 M4 20 L7 19',width=1.4),
        'fill':p('M4 10 L11 3 L19 11 L12 18 Z')+p('M7 2 L12 7 M4 10 L17 10',width=1.4)+p('M20 14 C19 16 17.5 17.5 18.2 19 C19 20.6 21.3 20.5 21.7 19 C22.1 17.6 20.7 15.7 20 14 Z',fill=PAPER,width=1.4),
        'eraser':p('M4 13 L13 4 C14 3 15 3 16 4 L21 9 C22 10 21.7 11 21 12 L12 21 L8 21 L4 17 C2.8 15.8 2.8 14.2 4 13 Z')+p('M8 9 L16 17 M12 21 L22 21',width=1.4),
        'album':p('M12 5 C9 3 5 3 2 4 L2 20 C5 19 9 19 12 21 C15 19 19 19 22 20 L22 4 C19 3 15 3 12 5 Z')+p('M12 5 L12 21',width=1.4),
        'save':p('M4 15 L4 21 L20 21 L20 15 M12 3 L12 16 M7 11 L12 16 L17 11'),
        'leaf':p('M4 20 C1 13 6 4 21 3 C21 13 16 21 7 20 Z')+p('M3 22 L17 7 M8 16 L8 11 M12 12 L17 12',width=1.35),
        'undo':p('M9 5 L3 10 L9 15 M3 10 L13 10 C22 10 23 20 15 21'),
        'redo':p('M15 5 L21 10 L15 15 M21 10 L11 10 C2 10 1 20 9 21'),
        'preview':p('M7 3 L21 12 L7 21 Z',width=1.7),
        'close':p('M6 6 L18 18 M18 6 L6 18',width=1.65),
    }
    return tools


def outlined_wordmark():
    """Windows GDI native quadratic glyph outlines; no font files are copied.

    The delivered logo is paths, so consumers do not need Georgia installed.
    """
    class LOGFONT(ctypes.Structure):
        _fields_=[('height',W.LONG),('width',W.LONG),('escapement',W.LONG),('orientation',W.LONG),('weight',W.LONG),('italic',W.BYTE),('underline',W.BYTE),('strike',W.BYTE),('charset',W.BYTE),('outPrecision',W.BYTE),('clipPrecision',W.BYTE),('quality',W.BYTE),('pitch',W.BYTE),('face',W.WCHAR*32)]
    class GLYPHMETRICS(ctypes.Structure):
        _fields_=[('blackX',W.DWORD),('blackY',W.DWORD),('origin',W.POINT),('advanceX',ctypes.c_short),('advanceY',ctypes.c_short)]
    class FIXED(ctypes.Structure):
        _fields_=[('fract',W.WORD),('value',ctypes.c_short)]
    class MAT2(ctypes.Structure):
        _fields_=[('eM11',FIXED),('eM12',FIXED),('eM21',FIXED),('eM22',FIXED)]
    gdi=ctypes.windll.gdi32
    gdi.CreateCompatibleDC.restype=ctypes.c_void_p
    gdi.CreateFontIndirectW.argtypes=[ctypes.POINTER(LOGFONT)]; gdi.CreateFontIndirectW.restype=ctypes.c_void_p
    gdi.SelectObject.argtypes=[ctypes.c_void_p,ctypes.c_void_p]; gdi.SelectObject.restype=ctypes.c_void_p
    gdi.GetGlyphOutlineW.argtypes=[ctypes.c_void_p,W.UINT,W.UINT,ctypes.POINTER(GLYPHMETRICS),W.DWORD,ctypes.c_void_p,ctypes.POINTER(MAT2)]
    gdi.GetGlyphOutlineW.restype=W.DWORD
    gdi.DeleteObject.argtypes=[ctypes.c_void_p]; gdi.DeleteDC.argtypes=[ctypes.c_void_p]
    dc=gdi.CreateCompatibleDC(None)
    spec=LOGFONT(); spec.height=-200; spec.weight=700; spec.charset=1; spec.face='Georgia'
    font=gdi.CreateFontIndirectW(ctypes.byref(spec)); old=gdi.SelectObject(dc,font)
    matrix=MAT2(FIXED(0,1),FIXED(0,0),FIXED(0,0),FIXED(0,1))
    advance=0; paths=[]
    try:
        for letter in 'BugWorld':
            gm=GLYPHMETRICS()
            count=gdi.GetGlyphOutlineW(dc,ord(letter),2|0x100,ctypes.byref(gm),0,None,ctypes.byref(matrix))
            assert count!=0xffffffff,f'Cannot outline {letter}'
            data=ctypes.create_string_buffer(count)
            gdi.GetGlyphOutlineW(dc,ord(letter),2|0x100,ctypes.byref(gm),count,data,ctypes.byref(matrix))
            raw=data.raw; offset=0; commands=[]
            def point(pos):
                x,y=struct.unpack_from('<ii',raw,pos)
                return (x/65536+advance,-y/65536)
            def fmt(pt): return f'{pt[0]:.4f} {pt[1]:.4f}'
            while offset<count:
                length,kind=struct.unpack_from('<II',raw,offset)
                assert kind==24 and length>=16
                commands.append('M'+fmt(point(offset+8)))
                cursor=offset+16
                while cursor<offset+length:
                    curve,n=struct.unpack_from('<HH',raw,cursor); cursor+=4
                    points=[point(cursor+8*i) for i in range(n)]; cursor+=8*n
                    if curve==1:
                        commands.extend('L'+fmt(pt) for pt in points)
                    elif curve==2:
                        for i in range(n-1):
                            end=points[i+1] if i==n-2 else tuple((a+b)/2 for a,b in zip(points[i],points[i+1]))
                            commands.append('Q'+fmt(points[i])+' '+fmt(end))
                    elif curve==3:
                        assert n%3==0
                        commands.extend('C'+' '.join(fmt(pt) for pt in points[i:i+3]) for i in range(0,n,3))
                    else: raise ValueError(curve)
                commands.append('Z'); offset+=length
            paths.append(p(' '.join(commands),fill=INK,stroke='none',width=0))
            advance+=gm.advanceX-1.6
    finally:
        gdi.SelectObject(dc,old); gdi.DeleteObject(font); gdi.DeleteDC(dc)
    return ''.join(paths),advance


def button(tools,x,y,w,label,icon=None,filled=False):
    body=rect(x,y,w,58,18,ACCENT if filled else '#fffdfa',BORDER if not filled else ACCENT)
    color='white' if filled else INK
    if icon:
        body+=placed(tools[icon].replace(INK,color),x+18,y+16,26)
        body+=text(x+54,y+38,label,20,color,500)
    else: body+=text(x+w/2,y+38,label,20,color,500,'middle')
    return body


def layout_board(tools,logo,logo_width):
    species=['butterfly','beetle','ladybug','caterpillar']
    labels=['蝴蝶','独角仙','瓢虫','毛毛虫']
    icons={name:fragment(LINEART/'icons'/f'{name}.svg',f'nav-{name}') for name in species}
    defs='''<defs>
      <linearGradient id="background" x2="1" y2="1"><stop stop-color="#ece6f0"/><stop offset=".5" stop-color="#f8f3ec"/><stop offset="1" stop-color="#e3dae8"/></linearGradient>
      <linearGradient id="panel" x2=".2" y2="1"><stop stop-color="#fffefc" stop-opacity=".98"/><stop offset="1" stop-color="#f7f2f5" stop-opacity=".98"/></linearGradient>
      <radialGradient id="light"><stop stop-color="white" stop-opacity=".82"/><stop offset="1" stop-color="white" stop-opacity="0"/></radialGradient>
      <filter id="shadow" x="-.3" y="-.3" width="1.6" height="1.7"><feDropShadow dx="0" dy="14" stdDeviation="20" flood-color="#85708c" flood-opacity=".16"/></filter>
      <filter id="paper-shadow" x="-.2" y="-.2" width="1.4" height="1.5"><feDropShadow dx="0" dy="5" stdDeviation="6" flood-color="#847384" flood-opacity=".12"/></filter>
      <pattern id="paper-fiber" width="19" height="17" patternUnits="userSpaceOnUse"><path d="M1 5 L5 3 M10 14 L14 11 M17 5 L19 4" stroke="#bdad95" stroke-width=".55" opacity=".065"/></pattern>
    </defs>'''
    b=defs+rect(0,0,1920,1280,0,'url(#background)')+'<ellipse cx="938" cy="260" rx="900" ry="600" fill="url(#light)"/>'
    b+=text(64,65,'BugWorld · 实际资产排版',32,INK,600)
    b+=text(1856,64,'资产审核示意 · 非 SDK 运行截图',20,MUTED,400,'end')
    # The bar belongs to the paper composition; no independent-window caption.
    b+=text(456,136,'TabBar · 依附画纸的昆虫导航',20,MUTED)
    b+=rect(430,155,1052,110,24,'url(#panel)','#fff',2,extra='filter="url(#shadow)"')
    b+=placed(logo,454,176,267,logo_width)
    b+=p('M750 183 L750 237',stroke='#d5c8de',width=1.4)
    for i,name in enumerate(species):
        x=779+i*100
        if i==0: b+=rect(x-7,172,84,78,18,'#e8daf9','#d8c3f0',1.2)
        b+=placed(icons[name],x,178,68,64)
    b+=p('M1200 184 L1200 237',stroke='#d5c8de',width=1.4)
    b+=placed(tools['album'],1231,192,36)+text(1285,223,'作品册',25,INK,500)
    # Main paper window.
    b+=rect(430,280,1052,842,28,'url(#panel)','#fff',2,extra='filter="url(#shadow)"')
    b+=text(464,338,'蝴蝶',29,INK,600)
    b+='<circle cx="570" cy="327" r="10" fill="#ae96c5"/>'+p('M565 327 L569 331 L576 322',stroke='white',width=1.4)+text(590,335,'草稿已保存',19,MUTED)
    b+=placed(tools['close'],1424,312,28)
    b+=rect(461,371,990,603,18,PAPER,'#f1eadd',1,extra='filter="url(#paper-shadow)"')
    b+=rect(461,371,990,603,18,'url(#paper-fiber)')
    b+=placed(fragment(LINEART/'sheets/butterfly-outline.svg','main-paper'),566,273,780,1024)
    b+=placed(tools['leaf'],470,1030,25)+text(507,1051,'去花园',20,MUTED)
    b+=button(tools,805,1017,155,'保存','save')
    b+=button(tools,976,1017,170,'看看它','preview')
    b+=button(tools,1162,1017,260,'送到大自然','leaf',True)
    # Album uses the four actual paper SVGs, not flattened reference artwork.
    b+=rect(58,300,316,820,27,'url(#panel)','#fff',2,extra='filter="url(#shadow)"')
    b+=text(82,352,'作品册',28,INK,600)+placed(tools['close'],324,327,26)
    b+=text(82,386,'收藏画过的小生命',17,MUTED)
    for i,name in enumerate(species):
        x=80+(i%2)*146; y=410+(i//2)*174
        b+=rect(x,y,126,154,13,PAPER,'#cfb6eb' if i==0 else '#e9e0d9',2.5 if i==0 else 1)
        b+=placed(fragment(LINEART/'sheets'/f'{name}-outline.svg',f'album-{name}'),x+3,y-2,120,1024)
        b+=text(x+63,y+139,labels[i],17,INK,500,'middle')
    b+=rect(80,779,272,93,16,'#fffdfa',BORDER)
    b+=placed(icons['butterfly'],91,795,56,64)+text(161,813,'蝴蝶',22,INK,600)+text(161,848,'10月08日 · 15:24',15,MUTED)
    b+=button(tools,80,895,126,'继续画','crayon')
    b+=button(tools,221,895,131,'预览','preview')
    b+=button(tools,80,974,272,'放入花园','leaf',True)
    # Tool window.
    b+=rect(1550,300,312,820,27,'url(#panel)','#fff',2,extra='filter="url(#shadow)"')
    b+=text(1578,352,'画具',28,INK,600)+placed(tools['close'],1812,326,26)
    for i,(name,label) in enumerate([('crayon','蜡笔'),('fill','填色'),('eraser','橡皮')]):
        x=1571+i*91
        b+=rect(x,388,82,88,16,'#e9dcf8' if i==0 else '#fffdfa','#dfd0ed' if i==0 else BORDER)
        b+=placed(tools[name],x+24,399,34)+text(x+41,460,label,18,INK,500,'middle')
    colors=['#e985b6','#bc8be0','#986bd3','#7e9edf','#78c6ac','#50b3ba','#e7b65e','#eb937d','#d6a6b6','#c5b49e','#a6a5b1','#777484']
    for i,color in enumerate(colors):
        x=1599+(i%4)*68; y=525+(i//4)*69
        b+=f'<circle cx="{x}" cy="{y}" r="25" fill="{color}" stroke="white" stroke-width="2.5"/>'
        if i==2: b+=f'<circle cx="{x}" cy="{y}" r="29" fill="none" stroke="{ACCENT}" stroke-width="1.8"/>'
    for y,label,knob in [(738,'粗细',1740),(804,'轻重',1707)]:
        b+=text(1578,y+8,label,20,INK,500)
        b+=p(f'M1650 {y} L1819 {y}',stroke='#d9d0df',width=6)+p(f'M1650 {y} L{knob} {y}',stroke=ACCENT,width=6)
        b+=f'<circle cx="{knob}" cy="{y+2}" r="12" fill="#8d7b9c" opacity=".13"/><circle cx="{knob}" cy="{y}" r="11" fill="white" stroke="#e0d6e7"/>'
    b+=text(1578,878,'对称绘画',21,INK,500)+rect(1771,853,65,35,18,ACCENT)+'<circle cx="1818" cy="870.5" r="13.5" fill="white"/>'
    for x,name in [(1578,'undo'),(1716,'redo')]:
        b+=rect(x,929,121,66,17,'#fffdfa',BORDER)+placed(tools[name],x+46,947,28)
    b+=text(64,1192,'品牌、图标与画纸均为交付 SVG 的真实排版；背景与窗口只用于检视空间关系。',22,INK)
    b+=text(64,1231,'顶部为 TabBar；画纸、画具、作品册分别呈现。此图不表示 SDK 已实现窗口或交互。',19,MUTED)
    return svg(b,1920,1280,'BugWorld actual vector assets — composition review, not SDK runtime')


def contact_board(tools,logo,logo_width):
    labels={'crayon':'蜡笔','fill':'填色','eraser':'橡皮','album':'画册','save':'保存','leaf':'叶子','undo':'撤销','redo':'重做','preview':'预览','close':'关闭'}
    b=rect(0,0,1600,850,0,'#faf7fc')+text(64,73,'BugWorld · 品牌与工具矢量资产',32,INK,600)
    b+=rect(64,112,1472,188,22,'#fffdf9',BORDER)
    b+=placed(logo,102,158,480,logo_width)+text(684,180,'品牌标志',23,INK,600)+text(684,219,'复用实际蝴蝶图标 · BugWorld 字标已转轮廓',20,MUTED)+text(684,256,'交付 SVG 不依赖字体文件',20,MUTED)
    for i,(name,body) in enumerate(tools.items()):
        x=64+(i%5)*300; y=343+(i//5)*228
        b+=rect(x,y,272,198,20,'#fffdf9',BORDER)
        b+=placed(body,x+38,y+33,48)
        b+=placed(body,x+155,y+25,64)
        b+=text(x+38,y+119,'48 px',15,MUTED)+text(x+154,y+119,'64 px',15,MUTED)
        b+=text(x+31,y+165,labels[name],22,INK,600)+text(x+248,y+164,name,15,MUTED,400,'end')
    b+=text(64,823,'实际 SVG 栅格结果；无概念图像素、外部图像或运行截图。',18,MUTED)
    return svg(b,1600,850,'BugWorld deliverable logo and tool SVG contact sheet')


def main():
    for folder in ('brand','icons','boards'): (OUT/folder).mkdir(parents=True,exist_ok=True)
    tools=make_tools(); jobs=[]
    for name,body in tools.items():
        file=OUT/'icons'/f'{name}.svg'
        file.write_text(svg(body,24,24,f'BugWorld {name} tool icon'),encoding='utf-8')
        for size in (48,64): jobs.append(dict(svg=str(file),png=str(OUT/'icons'/f'{name}-{size}.png'),w=size,h=size))
    word,width=outlined_wordmark(); logo_width=math.ceil(78+width*.27+8)
    mark=fragment(LINEART/'icons/butterfly.svg','brand-butterfly')
    logo=placed(mark,0,4,64,64)+f'<g transform="translate(78 53) scale(.27)">{word}</g>'
    brand=OUT/'brand/bugworld-logo.svg'
    brand.write_text(svg(logo,logo_width,72,'BugWorld logo — butterfly mark and outlined wordmark'),encoding='utf-8')
    (OUT/'brand/bugworld-mark.svg').write_text(svg(mark,64,64,'BugWorld butterfly brand mark'),encoding='utf-8')
    jobs.append(dict(svg=str(brand),png=str(OUT/'brand/bugworld-logo.png'),w=logo_width*2,h=144))
    for name,board,w,h in [('asset-layout-review',layout_board(tools,logo,logo_width),1920,1280),('logo-and-tools-contact',contact_board(tools,logo,logo_width),1600,850)]:
        file=OUT/'boards'/f'{name}.svg'; file.write_text(board,encoding='utf-8')
        jobs.append(dict(svg=str(file),png=str(file.with_suffix('.png')),w=w,h=h))
    for file in OUT.rglob('*.svg'):
        root=ET.fromstring(file.read_text(encoding='utf-8'))
        assert not any(node.tag.endswith('image') for node in root.iter()),f'Unexpected raster embedding: {file}'
    runner="const sharp=require(process.argv[1]);const jobs=JSON.parse(process.argv[2]);(async()=>{for(const j of jobs) await sharp(j.svg,{density:192}).resize(j.w,j.h).png().toFile(j.png);})().catch(e=>{console.error(e);process.exit(1)});"
    subprocess.run([str(NODE),'-e',runner,SHARP,json.dumps(jobs)],check=True)
    manifest={'format':'BugWorld v3-review UI assets 1','status':'asset review candidate; not app integration or SDK screenshot','logo':{'wordmark':'BugWorld','glyphs':'outlined Georgia Bold','mark':'own butterfly optical icon','svg_size':[logo_width,72]},'tools':list(tools),'tool_viewBox':[0,0,24,24],'tool_stroke':1.65,'palette':{'ink':INK,'muted':MUTED,'accent':ACCENT,'border':BORDER,'paper':PAPER},'boards':{'asset-layout-review':[1920,1280],'logo-and-tools-contact':[1600,850]},'actual_source_assets':[f'assets-src/v3-review/lineart/icons/{n}.svg' for n in ('butterfly','beetle','ladybug','caterpillar')]+[f'assets-src/v3-review/lineart/sheets/{n}-outline.svg' for n in ('butterfly','beetle','ladybug','caterpillar')]}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'logo_size':[logo_width,72],'tools':len(tools),'raster_outputs':len(jobs),'svg_count':len(list(OUT.rglob('*.svg')))},ensure_ascii=False,indent=2))


if __name__=='__main__': main()
