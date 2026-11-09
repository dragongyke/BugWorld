"""Hand-authored SVG assets traced against the approved BugWorld drawing sheet.

Writes ONLY assets-src/v3-review/lineart. This is asset production, not app code.
Pillow builds review sheets; sharp/librsvg rasterizes our new SVG geometry.
The approved raster is used only in clearly labelled comparison crops.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets-src/v3-review/lineart"
REFERENCE = ROOT / "docs/visual-redesign/2026-10-08/01-insect-sheets-v1.png"
RUNTIME = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies"
NODE = Path(os.environ.get("BUGWORLD_NODE", str(RUNTIME / "node/bin/node.exe")))
SHARP = os.environ.get("BUGWORLD_SHARP", str(RUNTIME / "node/node_modules/sharp"))
INK = "#49392f"
ICON_INK = "#594771"


def path(d, *, fill="none", stroke=INK, width=2.15, name="", opacity=1):
    identifier=f' id="{name}"' if name else ''
    return f'<path{identifier} d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" opacity="{opacity}"/>'


def oval(x, y, rx, ry, angle=0, *, fill=INK, stroke="none", width=1):
    return f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" transform="rotate({angle} {x} {y})" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>'


# All following coordinates are hand-set control points in the corresponding
# approved crop's own pixel space. No fitting of circles/ellipses to silhouettes.
BUTTERFLY_UPPER = "M245 187 C225 130 178 74 119 37 C82 14 50 7 31 13 C10 18 14 41 22 62 C29 83 34 103 33 123 C28 147 37 166 58 179 C76 190 105 189 134 187 C178 183 214 183 245 190 Z"
BUTTERFLY_LOWER = "M245 190 C208 181 147 183 103 190 C72 195 48 208 54 236 C59 263 75 292 95 315 C111 335 133 357 149 358 C174 363 198 342 215 308 C232 275 245 226 245 190 Z"
BUTTERFLY_TIP = "M31 13 C10 18 14 41 22 62 C29 83 34 103 33 123 C28 147 37 166 58 179 C48 171 40 159 37 143 C33 127 36 112 39 102 C43 92 31 86 35 75 C40 65 28 58 34 50 C40 42 53 47 50 35 C42 27 55 21 74 20 L68.25 14.125 C53.25 10.25 40.5 10 31 13 Z"
BUTTERFLY_EDGE = "M54 232 C59 263 75 292 95 315 C111 335 133 357 149 358 C166 361 181 353 194 340 C185 344 177 351 168 350 C162 349 157 356 150 353 C141 353 138 345 130 345 C121 344 122 335 113 333 C102 330 105 323 97 319 C86 313 90 306 81 302 C73 297 78 286 70 281 C65 276 68 266 63 260 C56 252 59 243 54 232 Z"
BUTTERFLY_VEINS = [
    "M246 188 C219 178 196 167 177 153 C163 143 153 132 145 119 C122 86 82 48 49 32",
    "M166 104 C128 56 90 32 58 29",
    "M145 119 C115 100 72 76 31 63",
    "M163 141 C119 127 73 111 35 111",
    "M177 153 C132 155 86 158 48 161",
    "M243 190 C208 197 177 222 158 247 C137.6 270.8 117.9225 305.4375 105.10875 320.820375",
    "M190 218 C151 219 111 216 69 240",
    "M181 229 C150 238 113 259 85 282",
    "M235 202 C204 232 192 279 167 330",
]

BEETLE_SHELL = "M17 285 C21 238 53 198 102 170 C151 143 217 135 264 140 C275 140 283 141 289 145 C284 160 285 188 290 206 C293 222 282 240 268 246 C252 254 232 258 206 261 C146 270 80 271 17 285 Z"
BEETLE_PRONOTUM = "M289 145 C304 137 328 133 350 124 C371 115 389 97 411 89 C418 86 422 87 421 89 C403 100 398 122 403 142 C406 159 414 171 421 179 C417 196 413 215 402 229 C382 244 350 240 328 233 C307 226 292 211 286 188 C282 169 279 153 289 145 Z"
BEETLE_HORN = "M421 179 C453 169 482 141 499 108 C513 80 513 49 507 20 C504 8 506 4 510 7 C518 16 521 42 521 63 C522 99 511 130 493 158 C477 183 462 200 455 218 C449 231 448 240 451 250 C452 255 449 258 443 258 C428 259 414 258 401 255 C396 253 395 245 399 232 C410 216 418 196 421 179 Z"
BEETLE_BODY = "M18 287 C73 273 149 271 207 262 C250 258 279 249 287 210 C294 223 304 233 318 239 C343 249 373 249 401 237 C401 249 397 256 384 260 C373 263 365 267 357 275 C353 279 351 276 355 272 L360 266 C337 273 320 267 305 264 C297 263 294 268 290 274 C286 280 281 279 278 287 C276 294 272 288 268 294 C264 301 260 293 255 296 C248 301 244 294 238 299 C229 306 221 301 213 301 C201 299 192 292 182 292 C172 291 165 300 157 304 C149 307 146 300 141 306 C136 310 133 302 127 302 C116 298 109 294 102 299 C94 305 84 303 78 305 C68 309 60 306 52 310 C45 312 42 307 36 309 C31 311 28 305 25 305 C23 302 27 299 23 296 C20 294 19 291 18 287 Z"
BEETLE_LEGS = [
    "M107 277 C117 283 108 294 105 300 L98 311 L94 328 C91 338 86 339 79 338 L66 347 C61 349 57 347 55 354 L53 353 L55 347 L49 351 L47 356 L45 354 C46 347 48 345 54 343 L71 334 C70 329 74 319 77 311 L83 300 L80 295 C85 289 93 283 94 278 C97 274 102 274 107 277 Z",
    "M245 267 C255 269 252 279 250 287 L249 308 L245 309 L245 329 L251 337 C257 339 261 343 260 350 L258 351 L255 345 L251 344 L252 353 L249 351 L247 344 C239 342 233 339 231 335 C226 332 227 325 229 316 L232 304 L228 302 L232 281 C233 272 237 268 245 267 Z",
    "M311 256 C318 257 321 266 324 274 L332 294 L328 300 L339 323 C344 330 338 335 347 337 L361 342 C367 342 372 347 370 353 L368 353 L365 348 L361 347 L362 353 L359 352 L356 346 L345 345 C336 342 330 340 328 335 L324 319 L320 305 L315 305 L308 280 C304 273 301 267 304 262 C305 258 307 256 311 256 Z",
]

LADYBUG_LEFT = "M159 54 C120 51 91 57 68 82 C39 111 33 150 40 190 C48 239 76 272 115 288 C129 294 145 297 159 297 Z"
LADYBUG_RIGHT = "M165 54 C207 51 239 62 259 88 C282 117 289 153 282 192 C274 238 250 268 215 285 C199 292 179 296 165 297 Z"
LADYBUG_HEAD = "M121 32 C130 17 144 9 163 10 C181 9 200 16 208 31 C180 29 149 30 121 32 Z"
LADYBUG_PRONOTUM = "M94 59 C99 43 108 35 121 32 C149 30 180 29 208 31 C223 34 232 43 236 60 C213 54 187 53 168 54 L157 54 C139 53 113 53 94 59 Z"
LADYBUG_LEGS = [
    "M64 87 C51 79 44 70 36 70 C29 70 25 78 28 83 C31 87 42 94 53 102 Z",
    "M39 151 C29 150 20 149 13 153 C7 157 7 164 12 168 C18 172 29 169 39 169 Z",
    "M58 234 C47 241 37 246 35 253 C33 258 38 263 45 260 C53 257 59 252 65 247 Z",
    "M259 88 C272 78 281 70 289 71 C298 73 296 82 291 87 L269 103 Z",
    "M285 151 C295 150 305 149 311 154 C317 159 314 168 307 170 L285 170 Z",
    "M272 232 C279 237 288 241 290 248 C291 254 287 260 281 259 C274 257 268 252 263 247 Z",
]

# The approved drawing has ten outlined areas: a tapered tail, eight soft body
# segments, and a right-facing head. Shared seam curves are explicit paths.
CATERPILLAR_OUTER = "M56 72 C69 49 95 49 113 65 C134 46 157 48 177 64 C196 46 223 49 236 64 C253 47 278 49 291 63 C310 47 337 47 354 62 C372 47 399 47 415 62 C433 48 455 47 471 61 C488 48 506 51 515 61 C532 61 547 72 555 87 C565 103 568 124 562 137 C557 145 531 146 507 143 C493 149 480 147 465 141 C450 150 430 150 412 142 C395 151 373 151 354 142 C333 152 313 152 291 142 C270 152 249 153 228 142 C206 153 184 152 165 141 C145 152 121 151 101 141 C84 151 66 151 55 144 C43 154 27 160 18 154 C7 149 9 135 11 119 C14 96 31 73 56 72 Z"
CATERPILLAR_REGIONS = [
    ("tail", "M56 72 C31 73 14 96 11 119 C9 135 7 149 18 154 C27 160 43 154 55 144 C40 128 41 96 56 72 Z"),
    ("segment_01", "M56 72 C69 49 95 49 113 65 C101 86 96 118 101 141 C84 151 66 151 55 144 C40 128 41 96 56 72 Z"),
    ("segment_02", "M113 65 C134 46 157 48 177 64 C163 84 158 118 165 141 C145 152 121 151 101 141 C96 118 101 86 113 65 Z"),
    ("segment_03", "M177 64 C196 46 223 49 236 64 C224 88 221 119 228 142 C206 153 184 152 165 141 C158 118 163 84 177 64 Z"),
    ("segment_04", "M236 64 C253 47 278 49 291 63 C299 88 299 117 291 142 C270 152 249 153 228 142 C221 119 224 88 236 64 Z"),
    ("segment_05", "M291 63 C310 47 337 47 354 62 C363 88 363 118 354 142 C333 152 313 152 291 142 C299 117 299 88 291 63 Z"),
    ("segment_06", "M354 62 C372 47 399 47 415 62 C423 86 423 116 412 142 C395 151 373 151 354 142 C363 118 363 88 354 62 Z"),
    ("segment_07", "M415 62 C433 48 455 47 471 61 C479 87 477 114 465 141 C450 150 430 150 412 142 C423 116 423 86 415 62 Z"),
    ("segment_08", "M471 61 C488 48 506 51 515 61 C505 88 502 120 507 143 C493 149 480 147 465 141 C477 114 479 87 471 61 Z"),
    ("head", "M515 61 C532 61 547 72 555 87 C565 103 568 124 562 137 C557 145 531 146 507 143 C502 120 505 88 515 61 Z"),
]


def build_art():
    art = {}
    upper = path(BUTTERFLY_UPPER, name="forewing-left-outline")
    lower = path(BUTTERFLY_LOWER, name="hindwing-left-outline")
    marks = path(BUTTERFLY_TIP, fill=INK, stroke="none", name="forewing-tip-left") + path(BUTTERFLY_EDGE, fill=INK, stroke="none", name="scalloped-margin-left")
    for x,y,rx,ry,a in [(66,244,4,4.6,-10),(83,271,4.7,5.4,-12),(97,292,5,6.2,16),(116,310,6.7,8.4,18),(140,330,6.6,8.6,14),(168,332,4.5,6.6,18)]:
        marks += oval(x,y,rx,ry,a)
    veins = ''.join(path(d,stroke="#b8aaa0",width=.85,opacity=.86,name=f"vein-left-{i+1}") for i,d in enumerate(BUTTERFLY_VEINS))
    left = upper + lower + veins + marks
    body = path("M248 172 C241 173 241 187 242 210 L243 242 C244 260 246 273 251 274 C256 273 258 260 259 242 L260 210 C261 187 261 173 254 172 Z",fill=INK,stroke="none",name="body")
    body += oval(251,165,7,7)
    body += path("M247 158 C242 135 231 111 224 101 M255 158 C260 135 271 111 278 101",width=1.3,name="antennae")
    body += oval(223,97,3,4,-24,fill="none",stroke=INK,width=1.1) + oval(279,97,3,4,24,fill="none",stroke=INK,width=1.1)
    mirrored=left.replace('-left','-right')
    mirrored_marks=marks.replace('-left','-right')
    art["butterfly"] = dict(box=(0,0,506,373), crop=(126,178,632,551), label="Butterfly", regions=[("forewing_left",BUTTERFLY_UPPER,""),("forewing_right",BUTTERFLY_UPPER,"translate(502 0) scale(-1 1)"),("hindwing_left",BUTTERFLY_LOWER,""),("hindwing_right",BUTTERFLY_LOWER,"translate(502 0) scale(-1 1)")], line=left+f'<g transform="translate(502 0) scale(-1 1)">{mirrored}</g>'+body, marks=marks+f'<g transform="translate(502 0) scale(-1 1)">{mirrored_marks}</g>'+body)

    dark = path(BEETLE_BODY,fill=INK,stroke="none",name="ventral-body") + ''.join(path(d,fill=INK,width=1.2,name=f"leg-{i+1}") for i,d in enumerate(BEETLE_LEGS))
    line = dark + path(BEETLE_SHELL,name="arched-elytron") + path(BEETLE_PRONOTUM,name="pronotum-short-recurved-horn") + path(BEETLE_HORN,name="long-recurved-head-horn")
    line += ''.join(path(d,stroke="#b7a99f",width=.8,name=f"shell-vein-{i+1}") for i,d in enumerate(["M49 276 C75 218 155 158 277 146","M104 272 C142 210 215 160 284 147","M193 262 C219 214 245 191 285 172","M296 144 C289 169 302 214 326 228 C348 241 382 244 402 231","M412 96 C383 127 391 154 397 176 C403 194 407 211 402 227"]))
    line += path("M401 246 C413 246 421 252 448 253",width=1.2,name="head-profile") + oval(413,244,4.4,4.1,fill="none",stroke=INK,width=1.3)
    line += ''.join(path(d,stroke="#fffaf5",width=1.3,name=f"leg-root-separation-{i+1}") for i,d in enumerate(["M83 300 C79 297 82 292 88 288 C92 284 92 277 99 276 C108 273 115 281 107 292", "M231 303 C224 302 230 290 230 282 C230 274 235 267 242 267 C250 267 253 274 251 280", "M308 280 C304 273 300 267 304 261 C308 252 317 255 321 265"]))
    art["beetle"] = dict(box=(0,0,537,374),crop=(794,175,1331,549),label="Rhinoceros beetle",regions=[("elytron",BEETLE_SHELL,""),("pronotum_and_short_horn",BEETLE_PRONOTUM,""),("head_and_long_horn",BEETLE_HORN,"")],line=line,marks=dark)

    dark = ''.join(path(d,fill=INK,stroke="none",name=f"leg-{i+1}") for i,d in enumerate(LADYBUG_LEGS))
    dark += oval(96,179,21,37,-18)+oval(232,177,21,37,18)
    dark += path("M158 31 C145 30 141 37 138 44 C133 53 143 57 155 55 C159 54 159 37 158 31 Z",fill=INK,stroke="none",name="neck-mark-left")
    dark += path("M168 31 C180 30 184 37 189 44 C193 53 183 57 171 55 C167 54 166 38 168 31 Z",fill=INK,stroke="none",name="neck-mark-right")
    dark += path("M121 35 C111 33 104 30 98 26 M208 35 C220 32 226 28 231 25",width=1.5,name="antennae")+oval(96,25,8,4.5,37)+oval(232,25,8,4.5,-37)
    line=dark + path(LADYBUG_LEFT,name="elytron-left") + path(LADYBUG_RIGHT,name="elytron-right") + path(LADYBUG_HEAD,name="head-cap") + path(LADYBUG_PRONOTUM,name="pronotum")
    line += path("M159 54 L159 297 C161 298 163 298 165 297 L165 54",width=1.55,name="central-seam")
    line += path("M113 58 C74 87 62 127 65 167 C68 224 99 269 155 293 M209 58 C246 84 260 124 259 165 C257 222 225 270 171 293",stroke="#b7a99f",width=.85,name="elytron-contour-lines")
    art["ladybug"] = dict(box=(0,0,327,308),crop=(213,698,540,1006),label="Ladybug",regions=[("elytron_left",LADYBUG_LEFT,""),("elytron_right",LADYBUG_RIGHT,""),("head",LADYBUG_HEAD,""),("pronotum",LADYBUG_PRONOTUM,"")],line=line,marks=dark)

    feet = ""
    for i,(x,y) in enumerate([(65,148),(130,148),(195,148),(260,149),(327,149),(386,148),(444,147),(491,146)]):
        feet += path(f"M{x-11} {y-1} C{x-11} {y+16} {x+11} {y+16} {x+12} {y-1} Z",fill=INK,stroke="none",name=f"proleg-{i+1}")
    line=feet + path(CATERPILLAR_OUTER,name="continuous-body-outline")
    seams=["M56 72 C41 96 40 128 55 144","M113 65 C101 86 96 118 101 141","M177 64 C163 84 158 118 165 141","M236 64 C224 88 221 119 228 142","M291 63 C299 88 299 117 291 142","M354 62 C363 88 363 118 354 142","M415 62 C423 86 423 116 412 142","M471 61 C479 87 477 114 465 141","M515 61 C505 88 502 120 507 143"]
    line+=''.join(path(d,width=1.55,name=f"segment-seam-{i+1}") for i,d in enumerate(seams))
    face=oval(536,102,6.1,7.2)+path("M514 60 C518 47 518 31 516 20 M529 64 C532 52 537 39 544 30",width=1.5,name="antennae")
    face+=oval(516,16,4.4,5,fill="none",stroke=INK,width=1.5)+oval(547,28,4.4,5,35,fill="none",stroke=INK,width=1.5)
    face+=path("M562 122 C565 124 565 129 562 131",width=1.7,name="mouth")
    art["caterpillar"]=dict(box=(0,0,575,175),crop=(778,761,1353,936),label="Caterpillar",regions=[(name,d,"") for name,d in CATERPILLAR_REGIONS],line=line+face,marks=feet+face)
    return art


def svg_doc(content, size=1024, viewbox="0 0 1024 1024", title=""):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="{viewbox}"><title>{title}</title>{content}</svg>'


def species_transform(data):
    _,_,w,h=data["box"]
    scale=896/max(w,h)
    return f"translate({(1024-w*scale)/2:.6f} {(1024-h*scale)/2:.6f}) scale({scale:.8f})"


# Optical icon masters are authored at 64 units. Details are intentionally
# re-composed for recognizability at 48 pixels, not generated from paper SVGs.
def build_icons():
    ink=ICON_INK
    def p(d,fill="none",width=1.65): return path(d,fill=fill,stroke=ink,width=width)
    icons={}
    upper="M31 31 C26 20 15 8 7 9 C1 10 5 18 5 22 C4 29 11 33 19 32 Z"
    lower="M31 33 C24 30 9 30 9 37 C10 44 17 54 22 54 C28 54 30 41 31 33 Z"
    left=p(upper)+p(lower)+p("M7 9 C2 10 4 16 5 20 L7 19 C7 15 9 14 12 13 Z",ink,0)
    left+=oval(13,40,1.4,1.4,fill=ink)+oval(17,46,1.5,1.5,fill=ink)+oval(22,49,1.5,1.5,fill=ink)
    icons["butterfly"]=left+f'<g transform="translate(64 0) scale(-1 1)">{left}</g>'+p("M31 30 C30 35 31 43 32 45 C34 40 34 33 33 30 Z",ink,0)+oval(32,28,2,2,fill=ink)+p("M30 27 C29 24 27 22 26 20 M34 27 C35 24 37 22 38 20",width=1.2)+oval(26,20,1.2,1.2,fill=ink)+oval(38,20,1.2,1.2,fill=ink)
    icons["beetle"]=p("M5 43 C6 31 19 25 33 27 C33 33 34 36 36 38 C27 42 15 41 5 43 Z")+p("M33 27 C39 25 42 23 46 20 C42 23 42 28 46 31 C45 38 40 40 36 38 C33 36 32 31 33 27 Z")+p("M46 31 C55 27 59 15 55 8 C60 13 61 25 56 32 C51 39 48 39 50 43 L44 43 L43 40 Z")+p("M6 44 C16 42 25 43 35 39 L44 42 L40 46 L32 45 L28 47 L24 45 L19 47 L13 46 L7 48 Z",ink,0)+p("M14 45 L12 51 L8 53 M26 45 L26 51 L29 54 M38 44 L41 51 L46 53",width=2.5)+p("M9 41 C14 34 22 30 30 29",width=.9)+oval(47,41,.8,.8,fill=ink)
    icons["ladybug"]=p("M19 15 L13 11 M45 15 L51 11",width=1.5)+oval(13,11,2,1.7,fill=ink)+oval(51,11,2,1.7,fill=ink)+p("M17 24 L11 21 M13 35 L7 35 M17 47 L12 51 M47 24 L53 21 M51 35 L57 35 M47 47 L52 51",width=3.3)+p("M20 17 C23 6 41 6 44 17 Z")+p("M32 16 C17 15 12 26 13 37 C14 51 22 58 32 59 C43 58 51 49 51 36 C51 24 45 16 32 16 Z")+p("M31 17 L31 58 M34 17 L34 58",width=1.2)+oval(23,36,3.6,6.4,-18,fill=ink)+oval(42,36,3.6,6.4,18,fill=ink)+p("M26 17 C26 21 30 21 30 17 M35 17 C35 21 39 21 39 17",width=2.2)
    icons["caterpillar"]=p("M7 32 C8 25 13 23 18 27 C22 22 28 23 32 27 C37 23 42 24 45 28 C50 25 54 27 56 32 C61 33 62 37 61 42 C57 45 53 43 50 43 C45 47 39 47 35 44 C30 47 24 46 21 44 C16 46 11 45 9 42 C3 45 2 38 7 32 Z")+p("M18 27 C14 31 14 38 16 43 M32 27 C28 31 28 38 30 44 M45 28 C42 33 42 39 43 45 M54 29 C51 34 51 40 52 43",width=1.2)+p("M11 44 L11 47 M23 45 L23 48 M36 46 L36 49 M47 45 L47 48",width=2.5)+p("M55 30 L55 25 M58 32 L61 28",width=1.2)+oval(55,24,1.2,1.2,fill=ink)+oval(61,27,1.2,1.2,fill=ink)+oval(57,37,1.25,1.4,fill=ink)
    return {k:svg_doc(v,size=64,viewbox="0 0 64 64",title=f"BugWorld {k} optical navigation icon") for k,v in icons.items()}


def rasterize(jobs):
    runner="const sharp=require(process.argv[1]);const jobs=JSON.parse(process.argv[2]);(async()=>{for(const j of jobs) await sharp(j.svg,{density:192}).resize(j.size,j.size).png().toFile(j.png);})().catch(e=>{console.error(e);process.exit(1)});"
    subprocess.run([str(NODE),"-e",runner,SHARP,json.dumps(jobs)],check=True)


def fit_image(image, box, background=(255,255,255,255)):
    result=Image.new("RGBA",box,background)
    copy=image.copy().convert("RGBA")
    copy.thumbnail(box,Image.Resampling.LANCZOS)
    result.alpha_composite(copy,((box[0]-copy.width)//2,(box[1]-copy.height)//2))
    return result.convert("RGB")


def font(size,bold=False):
    filename="arialbd.ttf" if bold else "arial.ttf"
    return ImageFont.truetype(str(Path("C:/Windows/Fonts")/filename),size)


def component_sizes(mask, region, prune_fringe=False):
    """Exact 4-connected topology, using row spans rather than a huge pixel BFS."""
    parents=[]; areas=[]; previous=[]; spans=[]
    def root(i):
        while parents[i]!=i:
            parents[i]=parents[parents[i]]; i=parents[i]
        return i
    for y,row in enumerate(mask):
        edge=np.flatnonzero(np.diff(np.pad((row==region).astype(np.int8),(1,1))))
        current=[]; cursor=0
        for start,end in zip(edge[::2],edge[1::2]):
            label=len(parents); parents.append(label); areas.append(int(end-start))
            while cursor<len(previous) and previous[cursor][1]<=start: cursor+=1
            k=cursor
            while k<len(previous) and previous[k][0]<end:
                a=root(label); b=root(previous[k][2])
                if a!=b: parents[a]=b; areas[b]+=areas[a]
                k+=1
            current.append((start,end,label))
            spans.append((y,start,end,label))
        previous=current
    roots=[i for i in range(len(parents)) if root(i)==i]
    largest=max(roots,key=lambda i:areas[i])
    if prune_fringe:
        fringe=[i for i in roots if i!=largest]
        assert all(areas[i]<=16 for i in fringe),f"Unexpected disconnected coloring area in region {region}"
        for y,start,end,label in spans:
            if root(label)!=largest: mask[y,start:end]=0
        return [areas[largest]],sum(areas[i] for i in fringe)
    return sorted((areas[i] for i in roots),reverse=True)


def write_review(art):
    reference=Image.open(REFERENCE).convert("RGB")
    sheet=Image.new("RGB",(1600,2250),(248,247,244)); draw=ImageDraw.Draw(sheet)
    draw.text((66,35),"APPROVED DRAWING  /  ACTUAL SVG RASTER",font=font(38,True),fill=(56,46,41))
    draw.text((66,88),"Left: unedited approved crop. Right: rasterized editable SVG, fitted to the same crop bounds.",font=font(21),fill=(104,94,89))
    rows=[]
    for i,(name,data) in enumerate(art.items()):
        y=146+i*512
        draw.text((66,y),data["label"],font=font(28,True),fill=(56,46,41))
        crop=reference.crop(data["crop"]); crop.save(OUT/"reference"/f"{name}-approved-crop.png")
        raster=Image.open(OUT/"sheets"/f"{name}-outline-2048.png").convert("RGBA")
        # Reverse the documented square-sheet padding to show the full source
        # crop bounds; neither side is trimmed to its dark-pixel bounding box.
        _,_,w,h=data["box"]; scale=1792/max(w,h)
        xy=((2048-w*scale)/2,(2048-h*scale)/2)
        actual=raster.crop((round(xy[0]),round(xy[1]),round(xy[0]+w*scale),round(xy[1]+h*scale)))
        for x,img,label in [(66,crop,"APPROVED REFERENCE"),(844,actual,"PRODUCED SVG")]:
            draw.rounded_rectangle((x,y+42,x+690,y+447),18,fill="white",outline=(222,215,207),width=2)
            sheet.paste(fit_image(img,(652,355)),(x+19,y+63))
            draw.text((x+18,y+456),label,font=font(17,True),fill=(115,100,90))
        rows.append(dict(species=name,source_crop=list(data["crop"]),source_aspect=w/h))
    draw.text((66,2203),"New artwork only. No app changes. Comparison crops are not used in the delivered SVG or PNG assets.",font=font(18),fill=(105,97,90))
    sheet.save(OUT/"comparison-approved-vs-svg.png")

    icons=Image.new("RGB",(900,580),(250,247,252)); d=ImageDraw.Draw(icons)
    d.text((40,26),"OPTICAL ICONS / ACTUAL PIXEL SIZES",font=font(29,True),fill=ICON_INK)
    d.text((40,68),"Four separately drawn 64-unit masters. PNGs shown 1:1 below.",font=font(19),fill=(115,103,128))
    for j,size in enumerate((48,64,96)):
        x=310+j*175
        d.text((x,110),f"{size} px",font=font(18,True),fill=ICON_INK)
    for i,name in enumerate(art):
        y=151+i*101
        d.text((42,y+25),art[name]["label"],font=font(18),fill=ICON_INK)
        for j,size in enumerate((48,64,96)):
            x=310+j*175
            d.rounded_rectangle((x-14,y-2,x+110,y+97),12,fill=(244,238,252),outline=(223,212,236))
            im=Image.open(OUT/"icons"/f"{name}-{size}.png").convert("RGBA")
            icons.paste(im,(x+(96-size)//2,y+(96-size)//2),im)
    icons.save(OUT/"icons-contact-sheet-actual-sizes.png")

    masks=Image.new("RGB",(1800,550),(248,247,244)); d=ImageDraw.Draw(masks)
    d.text((36,22),"COLORING REGIONS / FALSE COLOR QA",font=font(29,True),fill=(56,46,41))
    colors=[(0,0,0),(235,155,177),(180,143,214),(115,185,209),(131,190,155),(225,182,113),(159,169,227),(219,145,118),(155,204,209),(218,175,216),(178,188,122)]
    for i,name in enumerate(art):
        arr=np.array(Image.open(OUT/"masks"/f"{name}-regions-2048.png"))[:,:,0]
        rgb=np.array(colors,dtype=np.uint8)[arr]
        rgba=np.dstack([rgb,(arr>0).astype(np.uint8)*255])
        masks.paste(fit_image(Image.fromarray(rgba),(400,400)),(25+445*i,90))
        d.text((40+445*i,504),f"{art[name]['label']} / {len(art[name]['regions'])} areas",font=font(19),fill=(56,46,41))
    masks.save(OUT/"masks-contact-sheet.png")


def main():
    for directory in ("sheets","icons","masks","reference","_raster-work"):
        (OUT/directory).mkdir(parents=True,exist_ok=True)
    art=build_art(); jobs=[]; stats={}
    for name,data in art.items():
        transform=species_transform(data)
        svg=svg_doc(f'<g transform="{transform}">{data["line"]}</g>',title=f"BugWorld {name} approved-silhouette line art")
        parsed=ET.fromstring(svg)
        ids=[node.attrib['id'] for node in parsed.iter() if 'id' in node.attrib]
        assert len(ids)==len(set(ids)),f"Duplicate editable path ids: {name}"
        file=OUT/"sheets"/f"{name}-outline.svg"; file.write_text(svg,encoding="utf-8")
        jobs.append(dict(svg=str(file),png=str(OUT/"sheets"/f"{name}-outline-2048.png"),size=2048))
        # Marks are rasterized separately to protect all fixed dark marks.
        marker=OUT/"_raster-work"/f"{name}-locked.svg"
        marker.write_text(svg_doc(f'<g transform="{transform}">{data["marks"]}</g>'),encoding="utf-8")
        jobs.append(dict(svg=str(marker),png=str(marker.with_suffix(".png")),size=2048))
        maskpaths=[]
        for index,(label,d,tr) in enumerate(data["regions"],1):
            item=f'<g transform="{tr}">{path(d,fill="white",stroke="none",name=label)}</g>'
            region=OUT/"_raster-work"/f"{name}-{index}.svg"
            region.write_text(svg_doc(f'<g transform="{transform}">{item}</g>'),encoding="utf-8")
            jobs.append(dict(svg=str(region),png=str(region.with_suffix(".png")),size=2048))
            maskpaths.append(f'<g transform="{tr}">{path(d,fill=f"rgb({index},0,0)",stroke="none",name=label)}</g>')
        locked_shapes=data["marks"].replace(INK,"#000000")
        exclusion=f'<defs><mask id="exclude-fixed-marks" maskUnits="userSpaceOnUse" x="0" y="0" width="1024" height="1024"><rect width="1024" height="1024" fill="white"/><g transform="{transform}">{locked_shapes}</g></mask></defs>'
        (OUT/"masks"/f"{name}-regions.svg").write_text(svg_doc(exclusion+f'<g mask="url(#exclude-fixed-marks)"><g transform="{transform}">'+''.join(maskpaths)+'</g></g>'),encoding="utf-8")
        stats[name]=dict(reference_crop=list(data["crop"]),source_coordinate_box=list(data["box"]),source_to_sheet=transform,regions=[dict(id=i,label=region[0],d=region[1],transform=region[2]) for i,region in enumerate(data["regions"],1)])
    for name,svg in build_icons().items():
        ET.fromstring(svg)
        file=OUT/"icons"/f"{name}.svg"; file.write_text(svg,encoding="utf-8")
        for size in (48,64,96): jobs.append(dict(svg=str(file),png=str(OUT/"icons"/f"{name}-{size}.png"),size=size))
    rasterize(jobs)
    for name,data in art.items():
        mask=np.zeros((2048,2048),dtype=np.uint8)
        for index in range(1,len(data["regions"])+1):
            coverage=np.array(Image.open(OUT/"_raster-work"/f"{name}-{index}.png").convert("RGBA"))[:,:,3]
            mask[coverage>=128]=index
        locked=np.array(Image.open(OUT/"_raster-work"/f"{name}-locked.png").convert("RGBA"))[:,:,3]>=128
        mask[locked]=0
        topology={}; fringe={}
        for i in range(1,len(data['regions'])+1):
            topology[str(i)],fringe[str(i)]=component_sizes(mask,i,prune_fringe=True)
        rgb=np.zeros((2048,2048,3),dtype=np.uint8); rgb[:,:,0]=mask
        Image.fromarray(rgb).save(OUT/"masks"/f"{name}-regions-2048.png")
        Image.fromarray((mask>0).astype(np.uint8)*255).save(OUT/"masks"/f"{name}-paintable-2048.png")
        Image.fromarray(locked.astype(np.uint8)*255).save(OUT/"masks"/f"{name}-locked-2048.png")
        outline=Image.open(OUT/"sheets"/f"{name}-outline-2048.png").convert("RGBA")
        alpha=np.array(outline)[:,:,3]
        values,counts=np.unique(mask,return_counts=True)
        stats[name].update(outline_size=list(outline.size),outline_alpha_bbox=list(outline.getbbox()),ink_coverage_pixels=int(np.count_nonzero(alpha)),region_pixels={str(int(k)):int(v) for k,v in zip(values,counts)},locked_pixels=int(locked.sum()),region_component_pixels=topology,removed_subpixel_fringe_pixels=fringe)
        assert list(outline.size)==[2048,2048] and alpha.min()==0 and alpha.max()==255
        assert set(values)==set(range(len(data["regions"])+1)),f"Missing mask region in {name}"
        assert all(int(np.sum(mask==i))>250 for i in range(1,len(data["regions"])+1))
        assert all(region[1].strip().endswith('Z') for region in data['regions']),f"Unclosed region path: {name}"
    manifest=dict(format="BugWorld v3-review lineart 1",canvas=2048,viewBox=[0,0,1024,1024],ink=INK,iconInk=ICON_INK,reference=str(REFERENCE.relative_to(ROOT)).replace("\\","/"),species=stats)
    (OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    write_review(art)
    # These are our own temporary raster inputs, all strictly below OUT.
    for file in (OUT/"_raster-work").iterdir(): file.unlink()
    (OUT/"_raster-work").rmdir()
    print(json.dumps({k:{"regions":len(v['regions']),"bbox":v['outline_alpha_bbox'],"paintable_pixels":sum(n for key,n in v['region_pixels'].items() if key!='0')} for k,v in stats.items()},indent=2))


if __name__ == "__main__":
    main()
