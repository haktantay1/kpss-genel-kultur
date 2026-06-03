# -*- coding: utf-8 -*-
"""Generate PWA app icons (no Pillow needed; drawn with PyMuPDF)."""
import fitz, math

NAVY=(0.102,0.212,0.365)   # #1a365d
NAVY2=(0.090,0.176,0.302)
WHITE=(1,1,1)
GOLD=(0.839,0.620,0.180)   # #d69e2e

def star_points(cx,cy,R,r,rot=-90,n=5):
    pts=[]
    for i in range(2*n):
        ang=math.radians(rot+i*(180/n))
        rad=R if i%2==0 else r
        pts.append(fitz.Point(cx+rad*math.cos(ang), cy+rad*math.sin(ang)))
    return pts

def draw_icon(maskable=False):
    S=512
    doc=fitz.open(); page=doc.new_page(width=S,height=S)
    sh=page.new_shape()
    # background (subtle vertical two-tone for depth)
    sh.draw_rect(fitz.Rect(0,0,S,S)); sh.finish(fill=NAVY,color=None)
    sh.draw_rect(fitz.Rect(0,S*0.55,S,S)); sh.finish(fill=NAVY2,color=None)
    # motif geometry (kept inside the maskable safe zone ~ center 80%)
    scale=0.84 if maskable else 1.0
    cx,cy=S*0.5, S*0.5
    R=120*scale
    # crescent: white disk carved by a navy disk offset to the right
    sh.draw_circle(fitz.Point(cx-44*scale,cy), R); sh.finish(fill=WHITE,color=None)
    sh.draw_circle(fitz.Point(cx-44*scale+46*scale,cy), R*0.82); sh.finish(fill=NAVY,color=None)
    # five-point gold star nestled in the crescent opening
    sp=star_points(cx+72*scale, cy, 52*scale, 22*scale, rot=-90)
    sh.draw_polyline(sp); sh.finish(fill=GOLD,color=None,closePath=True)
    sh.commit()
    return doc,page

def export(page, size, path):
    m=fitz.Matrix(size/512, size/512)
    pix=page.get_pixmap(matrix=m, alpha=False)
    pix.save(path)
    print("wrote",path,f"{size}x{size}")

doc,page=draw_icon(maskable=False)
export(page,512,"icon-512.png")
export(page,192,"icon-192.png")
export(page,180,"apple-touch-icon-180.png")
mdoc,mpage=draw_icon(maskable=True)
export(mpage,512,"icon-512-maskable.png")
print("done")
