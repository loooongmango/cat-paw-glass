"""Renders assets/night.jpg: a black cat on a rainy window sill, city bokeh behind.

Usage: python3 tools/night.py [output.jpg]   (needs numpy and Pillow)
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1272, 600
S = 2
rng = np.random.default_rng(11)
import os, sys
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'night.jpg')


def P(pts):
    return [(x * S, y * S) for x, y in pts]


def mask(fn, blur=0):
    m = Image.new('L', (W * S, H * S), 0)
    fn(ImageDraw.Draw(m))
    m = m.resize((W, H), Image.LANCZOS)
    if blur:
        m = m.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(m, dtype=np.float32) / 255.0


def bez(p0, c1, c2, p3, n=40):
    out = []
    for i in range(n + 1):
        t = i / n
        u = 1 - t
        out.append((u**3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t**3 * p3[0],
                    u**3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t**3 * p3[1]))
    return out


yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
img = np.zeros((H, W, 3), np.float32)


def paint(m, color, alpha=1.0, mode='normal'):
    global img
    c = np.array(color, np.float32) / 255.0
    a = np.clip(m * alpha, 0, 1)[..., None]
    if mode == 'normal':
        img = img * (1 - a) + c * a
    elif mode == 'add':
        img = img + c * a
    elif mode == 'screen':
        img = img * (1 - a) + (1 - (1 - img) * (1 - c)) * a


SILL = 478
# sky: dark, slightly lighter haze near horizon
sky_top = np.array([7, 9, 12], np.float32) / 255
sky_hz = np.array([40, 48, 58], np.float32) / 255
t = np.clip((yy - 40) / (SILL - 120), 0, 1) ** 1.6
img[:] = sky_top * (1 - t[..., None]) + sky_hz * t[..., None]
band = np.exp(-((yy - 395) ** 2) / (2 * 85 ** 2))
img += band[..., None] * np.array([0.13, 0.15, 0.18], np.float32)

# out-of-focus buildings
bld = []
x = -20
while x < W + 40:
    w = rng.uniform(50, 140)
    h = rng.uniform(90, 300)
    bld.append((x, SILL - h, x + w, SILL + 10))
    x += w * rng.uniform(0.7, 1.05)
bm = mask(lambda d: [d.rectangle(P([(b[0], b[1]), (b[2], b[3])]), fill=255) for b in bld], 9)
paint(bm, (16, 20, 25), 0.7)

# bokeh lights from windows
def bokeh_disc(cx, cy, r):
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    edge = np.clip((r - d) / 1.8, 0, 1)
    rim = np.exp(-((d - r * 0.86) ** 2) / (2 * (r * 0.09 + 0.6) ** 2)) * 0.45
    return edge * (0.55 + rim)

bok = np.zeros((H, W, 3), np.float32)
for b in bld:
    n = int((b[2] - b[0]) * (SILL - b[1]) / 2600)
    for k in range(n):
        if rng.random() < 0.25:
            continue
        cx = rng.uniform(b[0] + 6, b[2] - 6)
        cy = rng.uniform(b[1] + 8, SILL - 20)
        r = rng.uniform(4.5, 12)
        warm = rng.random() < 0.38
        col = np.array([235, 196, 140] if warm else [196, 214, 232], np.float32) / 255
        inten = rng.uniform(0.3, 0.85)
        y0, y1 = int(max(cy - r - 3, 0)), int(min(cy + r + 3, H))
        x0, x1 = int(max(cx - r - 3, 0)), int(min(cx + r + 3, W))
        if y1 <= y0 or x1 <= x0:
            continue
        d = np.sqrt((xx[y0:y1, x0:x1] - cx) ** 2 + (yy[y0:y1, x0:x1] - cy) ** 2)
        edge = np.clip((r - d) / 1.6, 0, 1)
        rim = np.exp(-((d - r * 0.86) ** 2) / (2 * (r * 0.1 + 0.6) ** 2)) * 0.5
        bok[y0:y1, x0:x1] += (edge * (0.5 + rim))[..., None] * col * inten
# a few big foreground bokeh (street lights, very defocused)
for cx, cy, r, col, inten in [(150, 140, 46, (220, 228, 236), 0.22), (1140, 110, 58, (230, 200, 150), 0.18),
                              (560, 70, 34, (210, 220, 235), 0.16), (1010, 330, 28, (255, 70, 60), 0.35),
                              (330, 300, 40, (200, 214, 228), 0.14)]:
    m = bokeh_disc(cx, cy, r)
    bok += m[..., None] * np.array(col, np.float32) / 255 * inten
img += bok
# glow haze from city
glow = np.asarray(Image.fromarray((np.clip(bok.mean(axis=2) * 3, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(40)), np.float32) / 255
paint(glow, (150, 170, 190), 0.35, 'add')

# raindrops and streaks on the glass (in focus)
drops = np.zeros((H, W), np.float32)
dark = np.zeros((H, W), np.float32)
for k in range(55):
    cx, cy = rng.uniform(0, W), rng.uniform(0, SILL - 10)
    r = rng.uniform(2.2, 5.5)
    y0, y1 = int(max(cy - r - 2, 0)), int(min(cy + r + 2, H))
    x0, x1 = int(max(cx - r - 2, 0)), int(min(cx + r + 2, W))
    d = np.sqrt((xx[y0:y1, x0:x1] - cx) ** 2 + ((yy[y0:y1, x0:x1] - cy) * 0.9) ** 2)
    dark[y0:y1, x0:x1] = np.maximum(dark[y0:y1, x0:x1], np.clip((r - d) / 1.0, 0, 1) * 0.5)
    hd = np.sqrt((xx[y0:y1, x0:x1] - (cx - r * 0.35)) ** 2 + (yy[y0:y1, x0:x1] - (cy - r * 0.35)) ** 2)
    drops[y0:y1, x0:x1] += np.clip((r * 0.38 - hd) / 0.8, 0, 1)
streaks = mask(lambda d: [d.line(P([(sx, sy), (sx + rng.uniform(-6, 6), sy + rng.uniform(60, 180))]), fill=255, width=int(2.2 * S))
                          for sx, sy in [(rng.uniform(0, W), rng.uniform(0, 260)) for _ in range(5)]], 0.6)
paint(dark, (6, 8, 10), 1.0)
paint(drops, (210, 222, 235), 0.75, 'add')
paint(streaks, (140, 155, 170), 0.18, 'add')

# window mullion (left) and frame (right)
paint(mask(lambda d: d.rectangle(P([(300, 0), (326, SILL)]), fill=255)), (5, 6, 8))
paint(mask(lambda d: d.rectangle(P([(326, 0), (329, SILL)]), fill=255), 0.8), (60, 70, 80), 0.5)
paint(mask(lambda d: d.rectangle(P([(1222, 0), (W, SILL)]), fill=255)), (5, 6, 8))
paint(mask(lambda d: d.rectangle(P([(1219, 0), (1222, SILL)]), fill=255), 0.8), (60, 70, 80), 0.4)

# sill
paint(mask(lambda d: d.rectangle(P([(0, SILL), (W, H)]), fill=255)), (9, 10, 12))
top = np.clip(1 - (yy - SILL) / 16, 0, 1) * (yy >= SILL)
paint(top, (44, 50, 58), 0.9)
paint(mask(lambda d: d.rectangle(P([(0, SILL), (W, SILL + 1.5)]), fill=255), 0.6), (120, 132, 145), 0.55, 'add')
# blurred reflection of city on sill top
refl = np.flipud(np.clip(bok, 0, 1))
refl_band = ((yy >= SILL) & (yy < SILL + 22)).astype(np.float32)
shift = 2 * SILL - H
rb = np.zeros_like(bok)
src = np.clip(bok[max(0, 2 * SILL - H - 22):SILL][::-1], 0, 1)
hh = min(src.shape[0], H - SILL)
rb[SILL:SILL + hh] = src[:hh]
rb = np.asarray(Image.fromarray((np.clip(rb * 255, 0, 255)).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5)), np.float32) / 255
img += rb * (refl_band * np.clip(1 - (yy - SILL) / 22, 0, 1))[..., None] * 0.5

# cat silhouette, back view, sitting on the sill looking out
CX = 820
left = bez((792, 316), (772, 350), (722, 392), (728, 442)) + bez((728, 442), (731, 466), (738, SILL), (752, SILL))
right = bez((888, SILL), (902, SILL), (909, 466), (912, 442)) + bez((912, 442), (918, 392), (868, 350), (848, 316))
body = left + right
head = []
for i in range(120):
    a = 2 * math.pi * i / 120
    head.append((CX + 47 * math.cos(a), 298 + 41 * math.sin(a)))
ear_l = [(778, 290), (786, 236), (790, 232), (796, 237), (814, 270)]
ear_r = [(826, 270), (844, 237), (850, 232), (854, 236), (862, 290)]
tail = bez((880, SILL - 6), (950, SILL - 2), (1004, SILL - 10), (1022, 440)) + bez((1022, 440), (1030, 420), (1018, 404), (1006, 410))

def catfn(d):
    d.polygon(P(body), fill=255)
    d.polygon(P(head), fill=255)
    d.polygon(P(ear_l), fill=255)
    d.polygon(P(ear_r), fill=255)
    d.line(P(tail[:30]), fill=255, width=int(17 * S), joint='curve')
    d.line(P(tail[28:60]), fill=255, width=int(13 * S), joint='curve')
    d.line(P(tail[58:]), fill=255, width=int(10 * S), joint='curve')
    d.ellipse(P([(1001, 404), (1012, 414)]), fill=255)

cat = mask(catfn, 0.7)
# fuzzy fur edge
noise = np.asarray(Image.fromarray((rng.random((H, W)) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6)), np.float32) / 255
soft = mask(catfn, 2.2)
cat = np.clip(np.maximum(cat, (soft > 0.25 + 0.5 * noise) * soft), 0, 1)
# rim light from the city behind
er = np.asarray(Image.fromarray((cat * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(5)), np.float32) / 255
rim = np.clip(cat - er, 0, 1)
rim = np.asarray(Image.fromarray((rim * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2)), np.float32) / 255
upper = np.clip((SILL - 30 - yy) / 120, 0, 1)
paint(cat, (3, 4, 5), 1.0)
bgl = np.asarray(Image.fromarray((np.clip(img.mean(axis=2) * 2.2, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(14)), np.float32) / 255
rim2 = np.clip(cat - np.roll(np.roll(cat, 3, axis=0), 1, axis=1), 0, 1)
rim2 = np.asarray(Image.fromarray((rim2 * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.9)), np.float32) / 255
paint(rim2 * upper * (0.4 + bgl), (170, 185, 200), 0.6, 'add')
# contact shadow on sill
paint(mask(lambda d: d.ellipse(P([(720, SILL - 4), (1040, SILL + 12)]), fill=255), 5), (0, 0, 0), 0.7)

# finish: bloom, desaturate, cold grade, vignette, grain
lum = img.mean(axis=2)
hi = np.clip((lum - 0.35) / 0.4, 0, 1)
bloom = np.asarray(Image.fromarray((hi * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(18)), np.float32) / 255
img += bloom[..., None] * np.array([0.22, 0.25, 0.28], np.float32)
g = img.mean(axis=2, keepdims=True)
img = g + (img - g) * 0.22
img = img * np.array([0.95, 1.0, 1.06], np.float32)
img = np.clip(img, 0, 1) ** 1.02
vig = ((xx - W * 0.55) / (W * 0.62)) ** 2 + ((yy - H * 0.45) / (H * 0.8)) ** 2
img *= (1 - 0.38 * np.clip(vig, 0, 1))[..., None]
img += rng.normal(0, 0.03, (H, W)).astype(np.float32)[..., None]
img = np.clip(img, 0, 1)
Image.fromarray((img * 255).astype(np.uint8)).save(OUT, quality=90)
print('ok')
