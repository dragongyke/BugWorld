"""Shared board-space geometry. Coordinates refer to the approved 1122 x 1402 paper board."""
from math import sin, cos, pi

BOX = {'dragonfly': (76,100,563,420), 'honeybee':(154,476,534,783)}
INK = '#4a3529'

def sheet(slug, point):
    x,y=point; l,t,r,b=BOX[slug]
    scale=896/max(r-l,b-t)
    return (512+(x-(l+r)*.5)*scale,512+(y-(t+b)*.5)*scale)

def mix(a,b,t):
    return tuple(x+(y-x)*t for x,y in zip(a,b))

def cubic(curve,t):
    a,b,c,d=curve; q=1-t
    return tuple(q**3*a[i]+3*q*q*t*b[i]+3*q*t*t*c[i]+t**3*d[i] for i in (0,1))

def path(curve,n=40):
    return [cubic(curve,i/n) for i in range(n+1)]

def wing(slug,kind,side,t,q):
    if slug=='dragonfly':
        if kind=='fore':
            top=((310,181),(224,126),(145,150),(96,138)); bot=((310,185),(210,210),(150,231),(96,179))
            # A rounded tip curves forward between the two long rails.
            tip=(79,154)
        else:
            top=((310,195),(235,228),(131,227),(100,254)); bot=((310,197),(266,275),(268,307),(135,305)); tip=(81,283)
    else:
        if kind=='fore' and side==1:
            top=((381,576),(351,506),(283,467),(262,483)); bot=((372,582),(331,569),(293,553),(264,521)); tip=(255,491)
        elif kind=='fore':
            top=((369,600),(306,545),(223,501),(170,519)); bot=((370,603),(294,588),(221,611),(193,577)); tip=(159,536)
        else:
            top=((356,602),(294,581),(237,566),(204,586)); bot=((347,608),(302,597),(258,631),(216,617)); tip=(197,598)
    # Piecewise cubic leading / trailing rails with a soft oblong tip.
    def rail(c):
        if t<=.80: return cubic(c,t/.8)
        a,b,c0,end=c
        ctrl=(end[0]+(end[0]-c0[0])*.18,end[1]+(end[1]-c0[1])*.18)
        ctrl2=(tip[0],tip[1]+(end[1]-tip[1])*.72)
        return cubic((end,ctrl,ctrl2,tip),(t-.8)/.2)
    pt=mix(rail(top),rail(bot),q)
    if slug=='dragonfly' and side==1: return (640-pt[0],pt[1])
    return pt

def wing_cells(slug,kind,side):
    # Numbered from chord leading edge to trailing edge. The separators arc
    # towards the tips before converging with the margins, like the reference.
    def rail(t,index):
        if index==0: return 0.
        if index==3: return 1.
        if index==1: return max(0.,.56-.92*t+.065*sin(t*pi*1.35))
        return min(1.,.51+.57*t+.07*sin(t*pi*1.6))
    out=[]
    for band in range(3):
        points=[wing(slug,kind,side,t/100,rail(t/100,band)) for t in range(101)]
        points += [wing(slug,kind,side,t/100,rail(t/100,band+1)) for t in range(100,-1,-1)]
        out.append(points)
    return out

def ellipse(cx,cy,rx,ry,angle=0,count=72):
    a=angle*pi/180
    return [(cx+rx*cos(t)*cos(a)-ry*sin(t)*sin(a),cy+rx*cos(t)*sin(a)+ry*sin(t)*cos(a)) for t in [i*2*pi/count for i in range(count)]]

def tail_dragon(k,t,q):
    cuts=[216,246,276,309,342,373,396,418]
    half=[9.1,9.3,9.5,11.05,11.1,10.7,8.1,.6]
    lo,hi=cuts[k:k+2]; a,b=half[k:k+2]
    w=a*(1-t)+b*t+.95*sin(pi*t)
    return (320+(q*2-1)*w,lo+(hi-lo)*t+sin(pi*q)*(1.9 if k!=6 else .7))

def bee_abd(t,q):
    # Broad at the attachment, tapering to a rounded point diagonally down-left.
    upper=((323,610),(267,587),(173,671),(186,738))
    lower=((333,651),(286,687),(223,751),(192,745))
    return mix(cubic(upper,t),cubic(lower,t),q)

def patch(func,a=0,b=1):
    return [func(a+(b-a)*i/60,0) for i in range(61)] + [func(b,i/12) for i in range(1,13)] + [func(a+(b-a)*i/60,1) for i in range(59,-1,-1)] + [func(a,1-i/12) for i in range(1,13)]

def tuft_outline():
    anchors=[(320,617),(330,601),(352,597),(364,572),(379,563),(404,568),(422,581),(422,609),(407,631),(400,652),(382,662),(365,664),(347,657),(332,645)]
    pts=[]
    for i,a in enumerate(anchors):
        b=anchors[(i+1)%len(anchors)]
        dx,dy=b[0]-a[0],b[1]-a[1]; length=(dx*dx+dy*dy)**.5
        for t,d in [(0,0),(.31,-1.5),(.65,3.6),(.81,-.8)]:
            x,y=mix(a,b,t); pts.append((x+d*dy/length,y-d*dx/length))
    return pts

def specs(slug):
    items=[]
    def region(name,points,color,kind='body'):
        items.append((name,points,color,kind))
    for kind,side in ([('fore',-1),('fore',1),('hind',-1),('hind',1)] if slug=='dragonfly' else [('fore',1),('hind',-1),('fore',-1)]):
        for j,poly in enumerate(wing_cells(slug,kind,side)):
            if slug=='honeybee' and kind=='hind' and j==0: continue  # hidden behind the forewing
            colors=(['#77a5bf','#d9bf78','#8eb5c4'] if slug=='dragonfly' else ['#d2b1ad','#e5cb97','#b9b2c4'])
            region(f'{kind}_{side}_cell{j+1}',poly,colors[j],'wing')
    if slug=='dragonfly':
        region('head',ellipse(320,140,26.5,19),'#408d96')
        region('thorax_left',ellipse(309.7,165.6,10.6,19.4,13),'#5aaca9')
        region('thorax_right',ellipse(330.3,165.6,10.6,19.4,-13),'#75b4ac')
        region('thorax_lower',ellipse(320,202,11.5,16.1),'#669fa9')
        for k in range(7):
            region('tail'+str(k+1),patch(lambda t,q:tail_dragon(k,t,q)),'#367ba7')
    else:
        for k,(a,b) in enumerate(zip([0,.24,.44,.64,.81,.95],[.24,.44,.64,.81,.95,1])):
            region('abdomen'+str(k+1),patch(bee_abd,a,b),['#e7b24e','#68493a','#efb848','#78523b','#e7af48','#69513d'][k])
        region('thorax',tuft_outline(),'#a36b2d')
        region('head',ellipse(437.3,624,27.5,39.7,8),'#a27b47')
    return items
