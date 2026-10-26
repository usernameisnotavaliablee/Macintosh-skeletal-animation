#!/usr/bin/env python3
# Skeletal glyph contour = closed ribbon around a pen trail:
# starts at stroke begin, goes along edge1 to the tip (~half arc length),
# returns along edge2.  Emit both resampled edges; the animation reveals a
# growing prefix polygon  e1[0..m] + reverse(e2[0..m])  -- the pen trail.
import json, math
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen

FONT = "MacintoshSkeletalVariable.otf"
TEXT = "test"
EDGE_N = 160
CUBIC_STEPS = 24

def flatten_glyph(gs, name):
    rp = RecordingPen(); gs[name].draw(rp)
    contours, cur, start, prev = [], None, None, None
    for op, pts in rp.value:
        if op == "moveTo":
            cur = [pts[0]]; start = pts[0]; prev = pts[0]
        elif op == "curveTo":
            p0 = prev
            for i in range(1, CUBIC_STEPS + 1):
                t = i / CUBIC_STEPS
                (x1,y1),(x2,y2),(x3,y3) = pts
                x = (1-t)**3*p0[0] + 3*(1-t)**2*t*x1 + 3*(1-t)*t*t*x2 + t**3*x3
                y = (1-t)**3*p0[1] + 3*(1-t)**2*t*y1 + 3*(1-t)*t*t*y2 + t**3*y3
                cur.append((x,y))
            prev = pts[-1]
        elif op == "lineTo":
            cur.append(pts[-1]); prev = pts[-1]
        elif op in ("closePath","endPath"):
            contours.append((start, cur)); cur = None
    return contours

def arc_positions(pts):
    acc = [0.0]
    for i in range(1, len(pts)):
        acc.append(acc[-1] + math.dist(pts[i-1], pts[i]))
    return acc

def resample(pts, n):
    acc = arc_positions(pts)
    total = acc[-1]
    out, j = [], 0
    for i in range(n):
        s = total * i / (n - 1)
        while j < len(acc) - 2 and acc[j+1] < s:
            j += 1
        seg = acc[j+1] - acc[j] or 1e-9
        f = (s - acc[j]) / seg
        out.append((pts[j][0] + (pts[j+1][0]-pts[j][0]) * f,
                    pts[j][1] + (pts[j+1][1]-pts[j][1]) * f))
    return out

def main():
    data = open(FONT,"rb").read()
    font = hb.Font(hb.Face(data))
    buf = hb.Buffer(); buf.add_str(TEXT); buf.guess_segment_properties()
    hb.shape(font, buf, {})
    ft = TTFont(FONT); gs = ft.getGlyphSet()
    order = ft.getGlyphOrder()
    strokes, x_off = [], 0.0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        name = order[info.codepoint]
        for start, pts in flatten_glyph(gs, name):
            if len(pts) < 8: continue
            acc = arc_positions(pts)
            k = 0
            while k < len(acc)-1 and acc[k] < acc[-1]/2:
                k += 1
            e1 = resample(pts[:k+1], EDGE_N)
            e2 = resample(list(reversed(pts[k:])) + [pts[0]], EDGE_N)
            sl = arc_positions(e1)[-1]
            strokes.append({
                "g": name,
                "e1": [[round(x+x_off,1), round(y,1)] for x,y in e1],
                "e2": [[round(x+x_off,1), round(y,1)] for x,y in e2],
                "len": round(sl,1),
            })
        x_off += pos.x_advance
    meta = {"text":TEXT,"upm":ft["head"].unitsPerEm,"adv":x_off,
            "glyphs":[order[i.codepoint] for i in buf.glyph_infos]}
    PEN_ORDER = [0,3,2,1,4,5,6,7,8,9,10,13,12,11]  # connectivity-derived writing order for "test"
    strokes = [strokes[i] for i in PEN_ORDER]
    json.dump({"meta":meta,"strokes":strokes}, open("strokes.json","w"))
    import os
    print("strokes:",len(strokes),"json KB:",os.path.getsize("strokes.json")//1024)
    for i,s in enumerate(strokes):
        print(i,s["g"],"len",s["len"],"start",s["e1"][0],"tip",s["e1"][-1])

main()
