"""Build test.html: handwriting animation from MacintoshSkeletalVariable.otf.

usage: python3 -I build.py [TEXT]      (needs fontTools + hb-shape)

1. hb-shape picks the connected cursive glyphs (calt/rlig) + bridge glyphs (_br.*).
2. Each contour of the Variable font is one pen stroke: centerline offset by
   +-width/2, width linear in wght. Extrapolating the master outlines to
   width 0 collapses the contour onto its centerline (forward + back);
   the forward half is the stroke path, its start point is where the pen lands.
3. Strokes are chained by endpoint proximity (= writing order); leftovers
   (t crossbars, i dots) are written after the word, like real cursive.
"""
import sys, json, math, subprocess
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen

FONT = "MacintoshSkeletalVariable.otf"
TEXT = sys.argv[1] if len(sys.argv) > 1 else "test"
f = TTFont(FONT)

def contours(g, w):
    p = RecordingPen(); f.getGlyphSet(location={"wght": w})[g].draw(p)
    cs = []
    for op, a in p.value:
        if op == "moveTo": cs.append([a[0]])
        elif op == "lineTo": cs[-1] += [cs[-1][-1], a[0], a[0]]
        elif op == "curveTo": cs[-1] += list(a)
    return cs  # flat: P0, (c1, c2, P)*

def width(w):  # stroke width at wght w, measured on the t crossbar (horizontal capsule)
    ys = [p[1] for p in contours("t", w)[1]]
    return max(ys) - min(ys)

W100, W500 = width(100), width(500)
T0 = -W100 / (W500 - W100)  # lerp factor 100->500 where width hits 0

def seglen(p0, c1, c2, p3, n=16):
    pts = [tuple((1-s)**3*a + 3*(1-s)**2*s*b + 3*(1-s)*s*s*c + s**3*d
                 for a, b, c, d in zip(p0, c1, c2, p3)) for s in (i / n for i in range(n + 1))]
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(n))

def centerline(pts):
    """Collapsed closed contour -> forward half (cut nearest half arc length)."""
    segs = [pts[i:i + 4] for i in range(0, len(pts) - 1, 3)]
    lens = [seglen(*s) for s in segs]
    acc, cut, best = 0, 0, 1e9
    for i, L in enumerate(lens):
        acc += L
        if abs(acc - sum(lens) / 2) < best: best, cut = abs(acc - sum(lens) / 2), i
    keep = cut + 1
    while keep > 1 and lens[keep - 1] < 1: keep -= 1  # drop zero-length cap segments
    return pts[:keep * 3 + 1]

shaped = json.loads(subprocess.check_output(["hb-shape", "--output-format=json", FONT, TEXT]))
strokes, x = [], 0
for gi in shaped:
    for a, b in zip(contours(gi["g"], 100), contours(gi["g"], 500)):
        sk = [(p[0] + (q[0] - p[0]) * T0, p[1] + (q[1] - p[1]) * T0) for p, q in zip(a, b)]
        strokes.append([(px + x + gi["dx"], py + gi["dy"]) for px, py in centerline(sk)])
    x += gi["ax"]

# writing order: greedy chain end -> nearest start; far jumps deferred to the end
order, rest = [strokes[0]], strokes[1:]
while rest:
    end = order[-1][-1]
    i = min(range(len(rest)), key=lambda k: math.dist(end, rest[k][0]))
    if math.dist(end, rest[i][0]) > 400: break
    order.append(rest.pop(i))
order += sorted(rest, key=lambda s: s[0][0])  # crossbars / dots, left to right
lifts = len(order) - len(rest)  # index where pen-lift strokes begin

def d(s):
    r = lambda p: f"{p[0]:.0f} {-p[1]:.0f}"  # flip y for SVG
    return f"M{r(s[0])}" + "".join("C" + " ".join(r(p) for p in s[i:i + 3]) for i in range(1, len(s), 3))

ys = [p[1] for s in order for p in s]
data = {"paths": [d(s) for s in order], "lift": lifts, "width": round(W500),
        "box": [-W500, -max(ys) - W500, x + W500 * 2, max(ys) - min(ys) + W500 * 2]}
html = open("template.html", encoding="utf-8").read().replace("/*DATA*/null", json.dumps(data))
open(f"{TEXT}.html", "w", encoding="utf-8").write(html)
print(f"{TEXT}.html: {len(order)} strokes, {len(rest)} after pen lift, width {W500:.0f}/{f['head'].unitsPerEm}")
