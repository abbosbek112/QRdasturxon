"""Namuna restoran uchun taom rasmlarini chizadi.

Nega chizamiz, tayyor foto olmaymiz? Loyiha ataylab tashqi bog'liqliksiz:
internetdan hech narsa yuklanmaydi. Shu sabab namuna rasmlari shu yerda,
Pillow bilan chiziladi.

Bular foto emas — ustidan qaralgan sodda illyustratsiya. Haqiqiy foto
qo'yilsa menyu albatta chiroyliroq chiqadi, admin paneldan istalgan payt
almashtirsa bo'ladi.

Muhim texnik nuqta: Pillow shakl chetlarini silliqlamaydi, shuning uchun
hamma narsa SCALE barobar katta chiziladi va oxirida LANCZOS bilan
kichraytiriladi — chetlar shundagina toza chiqadi.
"""

from __future__ import annotations

import math
import random

from PIL import Image, ImageDraw, ImageFilter

SCALE = 4
DISH_SIZE = (900, 675)      # 4:3 — menyudagi karta nisbati
COVER_SIZE = (1200, 600)
LOGO_SIZE = (400, 400)

Color = tuple[int, int, int]


# --- asosiy yordamchilar ---------------------------------------------------

def _gradient(size: tuple[int, int], top: Color, bottom: Color) -> Image.Image:
    """Vertikal gradient. Bir piksel enli chiziq chizib, keyin cho'zamiz —
    har bir pikselni alohida bo'yashdan ancha tez."""
    width, height = size
    strip = Image.new("RGB", (1, height))
    draw = ImageDraw.Draw(strip)
    for y in range(height):
        t = y / max(height - 1, 1)
        draw.point((0, y), tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return strip.resize(size, Image.BILINEAR)


def _mix(a: Color, b: Color, t: float) -> Color:
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _shadow(size: tuple[int, int], shape, blur: int, alpha: int = 90) -> Image.Image:
    layer = Image.new("L", size, 0)
    shape(ImageDraw.Draw(layer))
    return layer.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: v * alpha // 255)


def _speckle(draw, cx, cy, rx, ry, color, count, size_range, rng):
    """Ovqat ustidagi mayda donalar — tekis rangni jonlantiradi."""
    for _ in range(count):
        angle = rng.uniform(0, math.tau)
        dist = math.sqrt(rng.random())
        x = cx + math.cos(angle) * rx * dist
        y = cy + math.sin(angle) * ry * dist
        r = rng.uniform(*size_range)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=color)


def _blob(draw, cx, cy, rx, ry, color, rng, wobble=0.12, points=26):
    """Biroz notekis aylana — ovqat mukammal doira bo'lmaydi."""
    coords = []
    for i in range(points):
        angle = math.tau * i / points
        k = 1 + rng.uniform(-wobble, wobble)
        coords.append((cx + math.cos(angle) * rx * k, cy + math.sin(angle) * ry * k))
    draw.polygon(coords, fill=color)


def _plate(draw, cx, cy, r, rim: Color = (255, 255, 255), inner: Color = (248, 246, 243)):
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=rim)
    draw.ellipse((cx - r * 0.86, cy - r * 0.86, cx + r * 0.86, cy + r * 0.86), fill=inner)


def _bowl(draw, cx, cy, r, outer: Color, inner: Color):
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=outer)
    draw.ellipse((cx - r * 0.88, cy - r * 0.88, cx + r * 0.88, cy + r * 0.88), fill=inner)


def _scene(bg_top: Color, bg_bottom: Color, size=DISH_SIZE):
    """Fon + ustiga chiziladigan katta tuval qaytaradi."""
    big = (size[0] * SCALE, size[1] * SCALE)
    base = _gradient(big, bg_top, bg_bottom)
    return base, ImageDraw.Draw(base, "RGBA"), big


def _finish(image: Image.Image, size) -> Image.Image:
    return image.resize(size, Image.LANCZOS)


def _drop_shadow(base, big, cx, cy, r):
    """Idish ostidagi yumshoq soya — rasm tekis bo'lib qolmaydi."""
    shade = _shadow(
        big,
        lambda d: d.ellipse((cx - r * 1.02, cy - r * 0.9 + r * 0.16, cx + r * 1.02, cy + r * 1.04 + r * 0.16), fill=255),
        blur=int(26 * SCALE),
        alpha=105,
    )
    base.paste((90, 62, 40), (0, 0), shade)


# --- taomlar ---------------------------------------------------------------

def osh(seed=1) -> Image.Image:
    rng = random.Random(seed)
    base, draw, big = _scene((252, 245, 235), (238, 224, 205))
    cx, cy = big[0] / 2, big[1] / 2
    r = big[1] * 0.40
    _drop_shadow(base, big, cx, cy, r)
    draw = ImageDraw.Draw(base, "RGBA")
    _plate(draw, cx, cy, r)

    # guruch uyumi
    _blob(draw, cx, cy, r * 0.74, r * 0.70, (232, 196, 130), rng, wobble=0.06)
    _speckle(draw, cx, cy, r * 0.70, r * 0.66, (244, 216, 158), 900, (r * 0.012, r * 0.026), rng)
    _speckle(draw, cx, cy, r * 0.70, r * 0.66, (214, 172, 106), 500, (r * 0.010, r * 0.020), rng)

    # sabzi tilimlari
    for _ in range(26):
        angle = rng.uniform(0, math.tau)
        dist = math.sqrt(rng.random()) * r * 0.62
        x, y = cx + math.cos(angle) * dist, cy + math.sin(angle) * dist
        length, thick = r * rng.uniform(0.14, 0.24), r * 0.035
        a = rng.uniform(0, math.pi)
        dx, dy = math.cos(a) * length / 2, math.sin(a) * length / 2
        draw.line((x - dx, y - dy, x + dx, y + dy), fill=(226, 138, 46), width=int(thick))

    # go'sht bo'laklari
    for _ in range(7):
        angle = rng.uniform(0, math.tau)
        dist = math.sqrt(rng.random()) * r * 0.52
        x, y = cx + math.cos(angle) * dist, cy + math.sin(angle) * dist
        _blob(draw, x, y, r * 0.115, r * 0.092, (128, 72, 38), rng, wobble=0.2, points=12)
        _blob(draw, x - r * 0.02, y - r * 0.02, r * 0.07, r * 0.052, (156, 92, 50), rng, wobble=0.25, points=10)

    # mayiz
    _speckle(draw, cx, cy, r * 0.60, r * 0.56, (74, 44, 34), 22, (r * 0.022, r * 0.034), rng)
    return _finish(base, DISH_SIZE)


def lagmon(seed=2) -> Image.Image:
    rng = random.Random(seed)
    base, draw, big = _scene((250, 242, 232), (234, 218, 200))
    cx, cy = big[0] / 2, big[1] / 2
    r = big[1] * 0.40
    _drop_shadow(base, big, cx, cy, r)
    draw = ImageDraw.Draw(base, "RGBA")
    _bowl(draw, cx, cy, r, (255, 255, 255), (206, 92, 46))

    # qaynatma yuzasi
    _blob(draw, cx, cy, r * 0.80, r * 0.80, (186, 78, 38), rng, wobble=0.03)

    # ugra halqalari
    for _ in range(30):
        rr = r * rng.uniform(0.18, 0.66)
        ox, oy = cx + rng.uniform(-r * 0.2, r * 0.2), cy + rng.uniform(-r * 0.2, r * 0.2)
        start = rng.uniform(0, 360)
        draw.arc(
            (ox - rr, oy - rr, ox + rr, oy + rr),
            start, start + rng.uniform(70, 200),
            fill=(238, 208, 150), width=int(r * 0.035),
        )

    # go'sht va qalampir
    for _ in range(9):
        angle = rng.uniform(0, math.tau)
        dist = math.sqrt(rng.random()) * r * 0.58
        x, y = cx + math.cos(angle) * dist, cy + math.sin(angle) * dist
        _blob(draw, x, y, r * 0.085, r * 0.062, (118, 62, 34), rng, wobble=0.22, points=10)
    for _ in range(14):
        angle = rng.uniform(0, math.tau)
        dist = math.sqrt(rng.random()) * r * 0.62
        x, y = cx + math.cos(angle) * dist, cy + math.sin(angle) * dist
        draw.line((x, y, x + rng.uniform(-r * .09, r * .09), y + rng.uniform(-r * .09, r * .09)),
                  fill=(52, 122, 58), width=int(r * 0.026))
    return _finish(base, DISH_SIZE)


def somsa(seed=3) -> Image.Image:
    rng = random.Random(seed)
    base, draw, big = _scene((248, 240, 229), (226, 208, 186))
    cx, cy = big[0] / 2, big[1] / 2

    # yog'och taxta
    board = (cx - big[1] * 0.44, cy - big[1] * 0.30, cx + big[1] * 0.44, cy + big[1] * 0.30)
    shade = _shadow(big, lambda d: d.rounded_rectangle(board, radius=int(28 * SCALE), fill=255), int(24 * SCALE), 100)
    base.paste((92, 64, 42), (0, 0), shade)
    draw = ImageDraw.Draw(base, "RGBA")
    draw.rounded_rectangle(board, radius=int(28 * SCALE), fill=(168, 122, 78))
    for i in range(7):
        y = board[1] + (board[3] - board[1]) * (i + 0.5) / 7
        draw.line((board[0], y, board[2], y), fill=(152, 108, 68), width=int(2.5 * SCALE))

    # uchta somsa
    for ox, oy, rot in ((-0.54, 0.08, -14), (0.0, -0.12, 5), (0.54, 0.10, 17)):
        px, py = cx + ox * big[1] * 0.50, cy + oy * big[1] * 0.5
        s = big[1] * 0.185
        a = math.radians(rot)
        pts = []
        for angle in (-90, 30, 150):
            t = math.radians(angle) + a
            pts.append((px + math.cos(t) * s, py + math.sin(t) * s * 0.92))
        # taxtaga tushgan soya
        draw.polygon([(x + s * 0.06, y + s * 0.10) for x, y in pts], fill=(120, 84, 52, 120))
        draw.polygon(pts, fill=(190, 136, 74))                       # pishgan chet
        inner = [(px + (x - px) * 0.80, py + (y - py) * 0.80) for x, y in pts]
        draw.polygon(inner, fill=(216, 166, 96))                     # ustki yuza
        top = [(px + (x - px) * 0.52, py - s * 0.10 + (y - py) * 0.52) for x, y in pts]
        draw.polygon(top, fill=(232, 186, 114))                      # yorug' cho'qqi
        _speckle(draw, px, py, s * 0.40, s * 0.34, (250, 244, 228), 24, (s * 0.026, s * 0.044), rng)
    return _finish(base, DISH_SIZE)


def manti(seed=4) -> Image.Image:
    rng = random.Random(seed)
    base, draw, big = _scene((250, 244, 236), (232, 220, 206))
    cx, cy = big[0] / 2, big[1] / 2
    r = big[1] * 0.40
    _drop_shadow(base, big, cx, cy, r)
    draw = ImageDraw.Draw(base, "RGBA")
    _plate(draw, cx, cy, r)

    for i in range(5):
        angle = math.tau * i / 5 - math.pi / 2
        px, py = cx + math.cos(angle) * r * 0.42, cy + math.sin(angle) * r * 0.40
        s = r * 0.30
        # ostki soya — manti tekis dog' bo'lib qolmasin
        _blob(draw, px, py + s * 0.10, s * 1.02, s * 0.88, (214, 198, 176), rng, wobble=0.05)
        _blob(draw, px, py, s, s * 0.86, (243, 233, 215), rng, wobble=0.07)
        # yuqoridan tushgan yorug'lik
        _blob(draw, px - s * 0.10, py - s * 0.18, s * 0.58, s * 0.42, (253, 249, 241), rng, wobble=0.16)
        # cho'qqidagi burma — chiziqlar kalta, aks holda yulduzchaga o'xshab qoladi
        for k in range(5):
            t = math.tau * k / 5 + 0.4
            draw.line((px, py - s * 0.06,
                       px + math.cos(t) * s * 0.30, py - s * 0.06 + math.sin(t) * s * 0.26),
                      fill=(222, 208, 186), width=int(r * 0.016))
        draw.ellipse((px - s * 0.11, py - s * 0.15, px + s * 0.11, py + s * 0.05),
                     fill=(230, 217, 195))
    _speckle(draw, cx, cy, r * 0.68, r * 0.64, (58, 118, 62), 26, (r * 0.014, r * 0.024), rng)
    return _finish(base, DISH_SIZE)


def mastava(seed=5) -> Image.Image:
    rng = random.Random(seed)
    base, draw, big = _scene((250, 243, 233), (231, 216, 198))
    cx, cy = big[0] / 2, big[1] / 2
    r = big[1] * 0.39
    _drop_shadow(base, big, cx, cy, r)
    draw = ImageDraw.Draw(base, "RGBA")
    _bowl(draw, cx, cy, r, (255, 255, 255), (214, 118, 52))
    _blob(draw, cx, cy, r * 0.80, r * 0.80, (198, 100, 42), rng, wobble=0.03)

    _speckle(draw, cx, cy, r * 0.66, r * 0.62, (240, 226, 196), 320, (r * 0.016, r * 0.028), rng)
    for _ in range(10):
        angle = rng.uniform(0, math.tau)
        dist = math.sqrt(rng.random()) * r * 0.56
        x, y = cx + math.cos(angle) * dist, cy + math.sin(angle) * dist
        _blob(draw, x, y, r * 0.075, r * 0.06, (226, 148, 60), rng, wobble=0.2, points=10)
    _speckle(draw, cx, cy, r * 0.62, r * 0.58, (60, 126, 62), 40, (r * 0.016, r * 0.028), rng)
    # yog' halqalari
    for _ in range(16):
        angle = rng.uniform(0, math.tau)
        dist = math.sqrt(rng.random()) * r * 0.68
        x, y = cx + math.cos(angle) * dist, cy + math.sin(angle) * dist
        rr = r * rng.uniform(0.02, 0.05)
        draw.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(248, 206, 120, 170))
    return _finish(base, DISH_SIZE)


def achichuk(seed=6) -> Image.Image:
    rng = random.Random(seed)
    base, draw, big = _scene((250, 246, 240), (232, 224, 212))
    cx, cy = big[0] / 2, big[1] / 2
    r = big[1] * 0.40
    _drop_shadow(base, big, cx, cy, r)
    draw = ImageDraw.Draw(base, "RGBA")
    _plate(draw, cx, cy, r)

    # pomidor tilimlari
    for _ in range(11):
        angle = rng.uniform(0, math.tau)
        dist = math.sqrt(rng.random()) * r * 0.58
        x, y = cx + math.cos(angle) * dist, cy + math.sin(angle) * dist
        s = r * rng.uniform(0.15, 0.21)
        draw.ellipse((x - s, y - s * 0.95, x + s, y + s * 0.95), fill=(202, 48, 40))
        draw.ellipse((x - s * 0.66, y - s * 0.62, x + s * 0.66, y + s * 0.62), fill=(226, 82, 62))
        _speckle(draw, x, y, s * 0.4, s * 0.38, (246, 208, 150), 7, (s * 0.06, s * 0.1), rng)
    # piyoz halqalari
    for _ in range(9):
        angle = rng.uniform(0, math.tau)
        dist = math.sqrt(rng.random()) * r * 0.56
        x, y = cx + math.cos(angle) * dist, cy + math.sin(angle) * dist
        s = r * rng.uniform(0.09, 0.15)
        draw.ellipse((x - s, y - s * 0.5, x + s, y + s * 0.5),
                     outline=(250, 248, 246), width=int(r * 0.030))
    _speckle(draw, cx, cy, r * 0.62, r * 0.58, (46, 118, 54), 46, (r * 0.016, r * 0.030), rng)
    return _finish(base, DISH_SIZE)


def kapuchino(seed=7) -> Image.Image:
    rng = random.Random(seed)
    base, draw, big = _scene((246, 240, 233), (226, 214, 200))
    cx, cy = big[0] / 2, big[1] / 2
    r = big[1] * 0.40
    _drop_shadow(base, big, cx, cy, r)
    draw = ImageDraw.Draw(base, "RGBA")

    _plate(draw, cx, cy, r, (250, 248, 246), (242, 238, 234))       # likopcha
    cup = r * 0.68
    draw.ellipse((cx - cup, cy - cup, cx + cup, cy + cup), fill=(255, 255, 255))
    draw.ellipse((cx - cup * 0.90, cy - cup * 0.90, cx + cup * 0.90, cy + cup * 0.90), fill=(140, 92, 56))
    _blob(draw, cx, cy, cup * 0.86, cup * 0.86, (196, 148, 100), rng, wobble=0.02)

    # sut naqshi — barg
    draw.ellipse((cx - cup * 0.30, cy - cup * 0.34, cx + cup * 0.30, cy + cup * 0.20), fill=(246, 238, 226))
    for i in range(6):
        t = i / 5
        w = cup * (0.30 - 0.045 * i)
        y = cy + cup * (0.10 + t * 0.52)
        draw.ellipse((cx - w, y - cup * 0.11, cx + w, y + cup * 0.11), fill=(246, 238, 226))
    draw.line((cx, cy - cup * 0.30, cx, cy + cup * 0.66), fill=(214, 190, 160), width=int(r * 0.016))
    return _finish(base, DISH_SIZE)


def choy(seed=8) -> Image.Image:
    rng = random.Random(seed)
    base, draw, big = _scene((249, 244, 236), (230, 218, 202))
    cx, cy = big[0] / 2, big[1] / 2
    r = big[1] * 0.38
    _drop_shadow(base, big, cx, cy, r)
    draw = ImageDraw.Draw(base, "RGBA")

    _plate(draw, cx, cy, r, (252, 250, 248), (244, 241, 237))
    piala = r * 0.62
    draw.ellipse((cx - piala, cy - piala, cx + piala, cy + piala), fill=(255, 255, 255))
    draw.ellipse((cx - piala * 0.90, cy - piala * 0.90, cx + piala * 0.90, cy + piala * 0.90), fill=(58, 130, 148))
    draw.ellipse((cx - piala * 0.80, cy - piala * 0.80, cx + piala * 0.80, cy + piala * 0.80), fill=(255, 255, 255))
    _blob(draw, cx, cy, piala * 0.74, piala * 0.74, (206, 150, 62), rng, wobble=0.02)
    draw.ellipse((cx - piala * 0.44, cy - piala * 0.44, cx + piala * 0.44, cy + piala * 0.44),
                 fill=(226, 178, 88, 130))
    return _finish(base, DISH_SIZE)


def chakchak(seed=9) -> Image.Image:
    rng = random.Random(seed)
    base, draw, big = _scene((250, 245, 236), (232, 220, 204))
    cx, cy = big[0] / 2, big[1] / 2
    r = big[1] * 0.40
    _drop_shadow(base, big, cx, cy, r)
    draw = ImageDraw.Draw(base, "RGBA")
    _plate(draw, cx, cy, r)

    # asalga botirilgan tayoqchalar uyumi
    for _ in range(150):
        angle = rng.uniform(0, math.tau)
        dist = math.sqrt(rng.random()) * r * 0.62
        x, y = cx + math.cos(angle) * dist, cy + math.sin(angle) * dist * 0.9
        length = r * rng.uniform(0.10, 0.18)
        a = rng.uniform(0, math.pi)
        dx, dy = math.cos(a) * length / 2, math.sin(a) * length / 2
        shade = rng.choice([(228, 168, 62), (240, 188, 84), (212, 148, 48)])
        draw.line((x - dx, y - dy, x + dx, y + dy), fill=shade, width=int(r * 0.042))
    _speckle(draw, cx, cy, r * 0.55, r * 0.50, (250, 236, 210), 30, (r * 0.014, r * 0.024), rng)
    return _finish(base, DISH_SIZE)


def norin(seed=10) -> Image.Image:
    rng = random.Random(seed)
    base, draw, big = _scene((250, 246, 239), (233, 223, 209))
    cx, cy = big[0] / 2, big[1] / 2
    r = big[1] * 0.40
    _drop_shadow(base, big, cx, cy, r)
    draw = ImageDraw.Draw(base, "RGBA")
    _plate(draw, cx, cy, r)

    _blob(draw, cx, cy, r * 0.74, r * 0.68, (226, 210, 180), rng, wobble=0.06)
    # ugra qatlami: quyi qavat to'qroq, ustki qavat ochroq — chuqurlik beradi
    for shade, count, width_k in (((228, 212, 182), 260, 0.034), ((248, 239, 218), 300, 0.028)):
        for _ in range(count):
            angle = rng.uniform(0, math.tau)
            dist = math.sqrt(rng.random()) * r * 0.62
            x, y = cx + math.cos(angle) * dist, cy + math.sin(angle) * dist * 0.92
            length = r * rng.uniform(0.12, 0.22)
            a = rng.uniform(-0.5, 0.5)
            dx, dy = math.cos(a) * length / 2, math.sin(a) * length / 2
            draw.line((x - dx, y - dy, x + dx, y + dy), fill=shade, width=int(r * width_k))
    for _ in range(58):
        angle = rng.uniform(0, math.tau)
        dist = math.sqrt(rng.random()) * r * 0.56
        x, y = cx + math.cos(angle) * dist, cy + math.sin(angle) * dist * 0.9
        length = r * rng.uniform(0.10, 0.18)
        a = rng.uniform(-0.6, 0.6)
        dx, dy = math.cos(a) * length / 2, math.sin(a) * length / 2
        draw.line((x - dx, y - dy, x + dx, y + dy),
                  fill=rng.choice([(112, 66, 40), (136, 82, 48)]), width=int(r * 0.030))
    return _finish(base, DISH_SIZE)


# --- muqova va logo --------------------------------------------------------

def cover(accent: Color = (180, 83, 9)) -> Image.Image:
    """Restoran muqovasi — ustidan qaralgan dasturxon.

    Menyuning eng tepasida turadi va ustiga oq harflar bilan restoran nomi
    yoziladi, shuning uchun oxirida pastki yarmi qoraytiriladi.
    """
    rng = random.Random(42)
    big = (COVER_SIZE[0] * SCALE, COVER_SIZE[1] * SCALE)
    width, height = big
    base = _gradient(big, (146, 102, 62), (88, 57, 32))          # yog'och stol
    draw = ImageDraw.Draw(base, "RGBA")

    # taxta oralig'i va tolasi
    for i in range(8):
        y = height * (i + 0.5) / 8
        draw.line((0, y, width, y), fill=(0, 0, 0, 30), width=int(3 * SCALE))
    for _ in range(90):
        y = rng.uniform(0, height)
        x = rng.uniform(0, width)
        draw.line((x, y, x + rng.uniform(40, 190) * SCALE, y), fill=(255, 236, 210, 12),
                  width=int(rng.uniform(1, 2.5) * SCALE))

    def plate_of_rice(cx, cy, r):
        _drop_shadow(base, big, cx, cy, r)
        d = ImageDraw.Draw(base, "RGBA")
        _plate(d, cx, cy, r)
        _blob(d, cx, cy, r * 0.74, r * 0.70, (232, 196, 130), rng, wobble=0.06)
        _speckle(d, cx, cy, r * 0.68, r * 0.64, (245, 218, 160), 420, (r * 0.014, r * 0.028), rng)
        for _ in range(16):
            a = rng.uniform(0, math.tau)
            dist = math.sqrt(rng.random()) * r * 0.58
            x, y = cx + math.cos(a) * dist, cy + math.sin(a) * dist
            ln, t = r * rng.uniform(0.14, 0.24), rng.uniform(0, math.pi)
            d.line((x - math.cos(t) * ln / 2, y - math.sin(t) * ln / 2,
                    x + math.cos(t) * ln / 2, y + math.sin(t) * ln / 2),
                   fill=(226, 138, 46), width=int(r * 0.036))
        for _ in range(6):
            a = rng.uniform(0, math.tau)
            dist = math.sqrt(rng.random()) * r * 0.50
            _blob(d, cx + math.cos(a) * dist, cy + math.sin(a) * dist,
                  r * 0.12, r * 0.095, (128, 72, 38), rng, wobble=0.2, points=12)

    def bowl_of_soup(cx, cy, r):
        _drop_shadow(base, big, cx, cy, r)
        d = ImageDraw.Draw(base, "RGBA")
        _bowl(d, cx, cy, r, (255, 255, 255), (200, 100, 44))
        _blob(d, cx, cy, r * 0.80, r * 0.80, (188, 88, 38), rng, wobble=0.03)
        _speckle(d, cx, cy, r * 0.64, r * 0.60, (238, 222, 190), 160, (r * 0.018, r * 0.032), rng)
        _speckle(d, cx, cy, r * 0.60, r * 0.56, (58, 122, 60), 26, (r * 0.018, r * 0.030), rng)

    def coffee(cx, cy, r):
        _drop_shadow(base, big, cx, cy, r)
        d = ImageDraw.Draw(base, "RGBA")
        _plate(d, cx, cy, r, (250, 248, 246), (242, 238, 234))
        cup = r * 0.68
        d.ellipse((cx - cup, cy - cup, cx + cup, cy + cup), fill=(255, 255, 255))
        d.ellipse((cx - cup * 0.9, cy - cup * 0.9, cx + cup * 0.9, cy + cup * 0.9), fill=(150, 100, 60))
        _blob(d, cx, cy, cup * 0.84, cup * 0.84, (200, 152, 104), rng, wobble=0.02)
        d.ellipse((cx - cup * 0.34, cy - cup * 0.34, cx + cup * 0.34, cy + cup * 0.34),
                  fill=(244, 234, 220))

    # Muqova telefonda o'rtasidan qirqiladi (background-size: cover), shuning
    # uchun idishlar mayda va keng tarqatilgan: qanday qirqilsa ham kadrda
    # bir nechtasi qoladi va hech biri ulkan bo'lib ko'rinmaydi.
    plate_of_rice(width * 0.50, height * 0.46, height * 0.20)
    bowl_of_soup(width * 0.305, height * 0.28, height * 0.130)
    bowl_of_soup(width * 0.695, height * 0.29, height * 0.120)
    coffee(width * 0.625, height * 0.75, height * 0.115)
    coffee(width * 0.375, height * 0.76, height * 0.100)
    bowl_of_soup(width * 0.855, height * 0.60, height * 0.115)
    plate_of_rice(width * 0.145, height * 0.62, height * 0.120)

    # vilka va pichoq — chap chetda, katta likopcha yonida
    draw = ImageDraw.Draw(base, "RGBA")
    silver = (228, 230, 234, 225)
    fx = width * 0.325
    draw.rounded_rectangle((fx, height * 0.50, fx + height * 0.022, height * 0.70),
                           radius=int(height * 0.011), fill=silver)
    for i in range(3):                                   # vilka tishlari
        tx = fx + height * 0.003 + i * height * 0.008
        draw.rounded_rectangle((tx, height * 0.43, tx + height * 0.005, height * 0.52),
                               radius=int(height * 0.003), fill=silver)
    kx = fx + height * 0.048
    draw.rounded_rectangle((kx, height * 0.51, kx + height * 0.019, height * 0.70),
                           radius=int(height * 0.010), fill=silver)
    draw.rounded_rectangle((kx - height * 0.003, height * 0.42, kx + height * 0.022, height * 0.53),
                           radius=int(height * 0.010), fill=silver)

    # Pastdan qorayish — restoran nomi oq harflarda shu yerga tushadi. Menyu
    # shablonida yana bir qoraytiruvchi qatlam bor, shuning uchun bu yerdagisi
    # kuchli bo'lmasligi kerak, aks holda taomlar ko'rinmay qoladi.
    fade = Image.new("L", big, 0)
    fd = ImageDraw.Draw(fade)
    for y in range(height):
        t = max(0.0, (y / height - 0.40) / 0.60)
        fd.line((0, y, width, y), fill=int(135 * t * t))
    base.paste((12, 9, 6), (0, 0), fade)
    return _finish(base, COVER_SIZE)


def logo(accent: Color = (180, 83, 9)) -> Image.Image:
    """Doira ichida bodom shakli — kafening belgisi."""
    big = (LOGO_SIZE[0] * SCALE, LOGO_SIZE[1] * SCALE)
    base = _gradient(big, _mix(accent, (255, 255, 255), 0.14), _mix(accent, (0, 0, 0), 0.24))
    draw = ImageDraw.Draw(base, "RGBA")
    cx, cy = big[0] / 2, big[1] / 2
    s = big[0] * 0.30

    # Bodom — uchi o'tkir, o'rtasi keng. Eni sin() bo'yicha o'zgaradi, shuning
    # uchun ikki uchi tabiiy ravishda nolga keladi.
    def almond(scale: float, tilt: float):
        pts, n = [], 44
        for side in (1, -1):
            rng_iter = range(n + 1) if side == 1 else range(n, -1, -1)
            for i in rng_iter:
                t = i / n
                dy = (-1 + 2 * t) * s * scale
                dx = side * s * scale * 0.56 * math.sin(math.pi * t)
                pts.append((cx + dx * math.cos(tilt) - dy * math.sin(tilt),
                            cy + dx * math.sin(tilt) + dy * math.cos(tilt)))
        return pts

    draw.polygon(almond(1.0, math.radians(-12)), fill=(255, 249, 240))
    draw.polygon(almond(0.42, math.radians(-12)), fill=_mix(accent, (0, 0, 0), 0.12))

    # Doira ichiga kesmaymiz: menyuda logo allaqachon yumaloq kvadrat ichida
    # ko'rinadi, yana bir doira qo'shsak ikkita ramka bo'lib qolardi.
    return _finish(base, LOGO_SIZE)


DISHES = {
    "osh": osh,
    "lagmon": lagmon,
    "somsa": somsa,
    "manti": manti,
    "mastava": mastava,
    "achichuk": achichuk,
    "kapuchino": kapuchino,
    "choy": choy,
    "chakchak": chakchak,
    "norin": norin,
}

# Bosh sahifadagi telefon maketi shu rasmlarni ko'rsatadi. Ular media emas,
# static: bazaga bog'liq emas, ya'ni namuna restoran o'chirilsa ham maket
# butun qoladi.
LANDING_THUMBS = ("osh", "lagmon", "somsa", "norin", "mastava", "kapuchino")
THUMB_SIZE = (260, 195)

# Telegram/Facebook havola kartochkasi uchun standart o'lcham
OG_SIZE = (1200, 630)
# Docker konteynerida shrift yo'q va bo'lishi ham shart emas: OG rasm shu
# yerda BIR MARTA chiziladi va static fayl bo'lib qoladi.
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
)


def _font(size: int):
    from PIL import ImageFont

    from pathlib import Path

    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    raise SystemExit(
        "Qalin shrift topilmadi. FONT_CANDIDATES ga tizimingizdagi .ttf yo'lini qo'shing."
    )


def og_card(accent: Color = (180, 83, 9)) -> Image.Image:
    """Havola ulashilganda chiqadigan kartochka.

    Telegramga tashlanganda odam nima ekanini rasmdan bilib olsin: nom,
    bitta jumla va mahsulotning o'zidan bo'lak — likopchalar bilan stol.
    """
    rng = random.Random(7)
    big = (OG_SIZE[0] * SCALE, OG_SIZE[1] * SCALE)
    width, height = big
    base = _gradient(big, (255, 252, 248), (247, 238, 228))
    draw = ImageDraw.Draw(base, "RGBA")

    # O'ng tomonda stol burchagi — mahsulot hidi kelsin, lekin matnni bosmasin
    def plate_of_rice(cx, cy, r):
        _drop_shadow(base, big, cx, cy, r)
        d = ImageDraw.Draw(base, "RGBA")
        _plate(d, cx, cy, r)
        _blob(d, cx, cy, r * 0.74, r * 0.70, (232, 196, 130), rng, wobble=0.06)
        _speckle(d, cx, cy, r * 0.68, r * 0.64, (245, 218, 160), 380, (r * 0.014, r * 0.028), rng)
        for _ in range(14):
            a = rng.uniform(0, math.tau)
            dist = math.sqrt(rng.random()) * r * 0.58
            x, y = cx + math.cos(a) * dist, cy + math.sin(a) * dist
            ln, t = r * rng.uniform(0.14, 0.24), rng.uniform(0, math.pi)
            d.line((x - math.cos(t) * ln / 2, y - math.sin(t) * ln / 2,
                    x + math.cos(t) * ln / 2, y + math.sin(t) * ln / 2),
                   fill=(226, 138, 46), width=int(r * 0.036))
        for _ in range(5):
            a = rng.uniform(0, math.tau)
            dist = math.sqrt(rng.random()) * r * 0.50
            _blob(d, cx + math.cos(a) * dist, cy + math.sin(a) * dist,
                  r * 0.12, r * 0.095, (128, 72, 38), rng, wobble=0.2, points=12)

    def bowl(cx, cy, r):
        _drop_shadow(base, big, cx, cy, r)
        d = ImageDraw.Draw(base, "RGBA")
        _bowl(d, cx, cy, r, (255, 255, 255), (200, 100, 44))
        _blob(d, cx, cy, r * 0.80, r * 0.80, (188, 88, 38), rng, wobble=0.03)
        _speckle(d, cx, cy, r * 0.62, r * 0.58, (238, 222, 190), 130, (r * 0.018, r * 0.032), rng)

    plate_of_rice(width * 0.855, height * 0.60, height * 0.30)
    bowl(width * 0.665, height * 0.24, height * 0.145)
    bowl(width * 0.985, height * 0.16, height * 0.125)

    draw = ImageDraw.Draw(base, "RGBA")
    left = int(width * 0.075)

    # Nom
    draw.text((left, int(height * 0.30)), "QR", font=_font(int(78 * SCALE)), fill=(15, 17, 21))
    brand_w = draw.textlength("QR", font=_font(int(78 * SCALE)))
    draw.text((left + brand_w, int(height * 0.30)), "dasturxon",
              font=_font(int(78 * SCALE)), fill=accent)

    # Bitta jumla — nima ekanini shu aytadi
    draw.text((left, int(height * 0.47)), "Kafengiz menyusi —",
              font=_font(int(44 * SCALE)), fill=(60, 65, 74))
    draw.text((left, int(height * 0.575)), "mijoz telefonida",
              font=_font(int(44 * SCALE)), fill=accent)

    # Pastda kichik izoh
    draw.text((left, int(height * 0.755)), "QR kod · uch til · statistika",
              font=_font(int(26 * SCALE)), fill=(140, 146, 156))

    return _finish(base, OG_SIZE)


def write_landing_thumbs(static_dir) -> list[str]:
    """Maket uchun kichik rasmlarni app/static/img/ ga yozadi."""
    from pathlib import Path

    out = Path(static_dir) / "img"
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for key in LANDING_THUMBS:
        image = DISHES[key]().resize(THUMB_SIZE, Image.LANCZOS)
        path = out / f"dish-{key}.webp"
        image.save(path, "WEBP", quality=80, method=6)
        written.append(str(path))
    return written


if __name__ == "__main__":
    from pathlib import Path

    from app.config import BASE_DIR

    static = BASE_DIR / "app" / "static"
    for name in write_landing_thumbs(static):
        print(name)

    # JPEG, PNG emas: kartochkada gradient bor va PNG uni yomon siqadi.
    # Telegram/Facebook ikkalasini ham qabul qiladi, JPEG esa uch barobar yengil.
    og = Path(static) / "img" / "og.jpg"
    og_card().save(og, "JPEG", quality=86, optimize=True, progressive=True)
    print(og)
