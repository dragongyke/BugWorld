"""Control points traced in the two approved profile views. Units are drawing units.

X increases towards the tail in the drawing. A 3D point is (drawing x, lateral
distance from the midline, drawing y). To make a +X facing animal the Blender
builder reverses drawing X and drawing Y.
"""
import math
import re

ANT = {
    "head": "M126 126 C115 112 122 86 132 65 C145 43 160 35 178 37 C197 37 209 48 207 64 C205 85 183 105 158 114 C144 119 140 130 133 132 C129 131 129 126 131 120 Z",
    "thorax": "M205 64 C208 48 224 38 242 39 C260 39 272 45 282 60 C286 67 293 75 292 84 C290 99 277 104 268 99 C261 96 259 89 257 87 C250 96 241 100 229 95 C219 94 214 88 212 82 L202 80 Z",
    "petiole": "M291 79 C292 65 300 58 310 61 C321 64 321 74 319 85 C318 96 310 99 300 94 C293 93 289 87 291 79 Z",
    "gaster": "M319 85 C320 62 334 46 357 40 C382 34 410 37 435 51 C461 66 475 90 476 117 C476 130 475 139 472 143 C455 149 418 148 397 145 C363 142 323 123 319 99 Z",
}
GRASS = {
    "head": "M86 109 C85 92 91 81 104 77 C115 72 135 71 142 79 C150 93 144 121 135 138 C130 148 120 158 114 159 C101 156 90 140 87 127 Z",
    "pronotum": "M138 79 C148 73 161 77 174 77 C185 77 206 77 219 81 C218 93 206 115 196 131 C188 144 184 151 177 151 C159 152 141 145 132 138 C141 123 145 96 138 79 Z",
    "abdomen": "M197 108 C224 97 281 102 335 112 C368 121 414 135 441 149 C451 156 450 166 439 173 C415 190 363 196 318 193 C276 191 239 181 212 174 C194 170 186 151 186 141 Z",
    "tegmen": "M215 84 C237 76 295 74 345 75 C391 77 445 82 471 95 C486 102 491 113 485 121 C470 142 414 155 364 157 C302 156 243 142 203 122 C207 109 213 91 215 84 Z",
    "thigh": "M260 158 C263 144 282 131 298 114 L388 24 C399 13 407 8 415 12 C423 13 424 20 419 28 L330 146 C310 173 285 189 272 183 C262 181 257 174 260 158 Z",
}
# World legs start in the thorax at both sides. Hind coxae sit ahead of the
# abdomen even though the folded jumping femora reach past the wing roots.
LEGS = {
    "ant": [
        [(227,17,85),(230,27,112),(188,35,125),(158,57,188),(145,62,211),(126,66,219)],
        [(251,17,86),(259,25,110),(270,37,126),(263,64,181),(253,69,214),(238,73,224)],
        [(278,17,84),(304,30,115),(341,37,100),(380,56,165),(409,67,204),(435,73,216)],
    ],
    "grasshopper": [
        [(152,18,135),(146,28,160),(109,37,174),(91,49,214),(79,54,224),(60,58,231)],
        [(183,20,137),(172,27,156),(164,36,193),(155,59,218),(143,63,226),(139,67,232)],
        [(202,19,139),(220,29,167),(271,41,170),(410,57,20),(381,81,209),(395,85,221),(435,91,230)],
    ],
}


def curve(path):
    """Sample the closed cubic outline, keeping the actual artists' handles."""
    words = re.findall(r"[MLCZ]|-?(?:\d*\.)?\d+", path)
    result = []
    i = 0
    while i < len(words):
        op = words[i]
        i += 1
        if op == "Z":
            break
        if op in ("M", "L"):
            point = tuple(map(float, words[i:i+2]))
            i += 2
            result.append(point)
        elif op == "C":
            p0 = result[-1]
            a,b,c,d,e,f = map(float, words[i:i+6])
            i += 6
            for j in range(1, 19):
                t = j/18
                q = 1-t
                result.append((q*q*q*p0[0]+3*q*q*t*a+3*q*t*t*c+t*t*t*e,
                               q*q*q*p0[1]+3*q*q*t*b+3*q*t*t*d+t*t*t*f))
        else:
            raise ValueError(op)
    return result


def span(points, x):
    hits = [a[1]+(b[1]-a[1])*(x-a[0])/(b[0]-a[0])
            for a,b in zip(points, points[1:]+points[:1])
            if min(a[0], b[0]) <= x <= max(a[0], b[0]) and abs(a[0]-b[0]) > 1e-7]
    return min(hits), max(hits)


def ellipse(cx, cy, rx, ry, degrees):
    c,s = math.cos(math.radians(degrees)), math.sin(math.radians(degrees))
    return [(cx+rx*math.cos(t)*c-ry*math.sin(t)*s,
             cy+rx*math.cos(t)*s+ry*math.sin(t)*c) for t in [i*math.tau/52 for i in range(52)]]


def page(kind, x, y):
    return (512 + (x-253)*2.05, 512 + (y-(115 if kind == 'ant' else 126))*2.05)


def antennae(kind):
    if kind == "ant":
        return [[(144,14,66),(101,26,54),(87,33,61),(74,37,77),(62,41,99),(54,43,128)],
                [(141,-14,64),(99,-27,24),(78,-33,32),(61,-40,42),(47,-43,54),(34,-46,73)]]
    return [[(96,14,85),(82,22,69),(62,28,57),(35,35,44)],
            [(100,-13,86),(90,-24,59),(74,-30,39),(57,-35,26)]]


GASTER_SEAMS=["M382 37 C391 55 374 104 354 127","M435 51 C442 76 426 122 401 145","M468 87 C473 107 459 137 448 146"]
GRASS_SEAMS=["M174 78 C180 92 171 119 162 138","M216 108 C252 99 294 92 326 88",
             "M353 98 C390 92 426 91 464 94","M313 132 C364 127 426 122 481 106",
             "M331 156 C334 171 330 186 321 193","M364 157 C366 174 362 188 353 193",
             "M414 152 C418 166 411 181 405 185"]
