"""HYPERION store art for EX STORAGE LAB from the real logo + real Wine screenshots. ©2026 EX Inc./HYPERION DIGITAL ©2026"""
import os
from PIL import Image, ImageDraw, ImageFont
F = "/usr/share/fonts/truetype/sand-box/google/Poppins/"
OUT = "store_art"; BG = (53, 58, 70)
logo = Image.open("assets/logo_full.png").convert("RGB")


def grad_line(d, x0, y, w, h):
    for x in range(w):
        t = x / max(w - 1, 1)
        a, b = ((0x52, 0xe0, 0xb6), (0x4f, 0x9d, 0xe8)) if t < .55 else ((0x4f, 0x9d, 0xe8), (0x8b, 0x7c, 0xf2))
        u = t / .55 if t < .55 else (t - .55) / .45
        d.line([(x0 + x, y), (x0 + x, y + h)], fill=tuple(int(p + (q - p) * u) for p, q in zip(a, b)))


def vgrad(size, top, bot):
    im = Image.new("RGB", size); d = ImageDraw.Draw(im)
    for y in range(size[1]):
        t = y / (size[1] - 1); d.line([(0, y), (size[0], y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bot)))
    return im


def card(size, shot=None, title_px=60, sub=True):
    W, H = size; im = vgrad(size, (58, 63, 76), (40, 44, 54)); d = ImageDraw.Draw(im)
    if shot:
        s = Image.open(shot).convert("RGB"); sc = (H * 0.86) / s.height; s = s.resize((int(s.width * sc), int(s.height * sc)), Image.LANCZOS)
        x = max(int(W * 0.70), W - s.width); y = int(H * 0.09)
        m = Image.new("L", s.size, 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, s.width - 1, s.height - 1), radius=14, fill=255)
        im.paste(s, (x, y), m); d.rounded_rectangle((x, y, x + s.width - 1, y + s.height - 1), radius=14, outline=(80, 88, 104), width=2)
        # fade the screenshot into the background on its left edge (flat, no glow)
        fade = Image.new("RGB", (W, H), (46, 50, 61)); fm = Image.new("L", (W, H), 0); fd = ImageDraw.Draw(fm)
        for i in range(260):
            fd.line([(x + i, 0), (x + i, H)], fill=int(255 * (1 - i / 260) ** 1.6))
        fd.rectangle((0, 0, x, H), fill=255)
        im = Image.composite(fade, im, fm); d = ImageDraw.Draw(im)
    ls = int(H * (0.62 if shot else 0.52)); lg = logo.resize((ls, ls), Image.LANCZOS)
    lm = Image.new("L", (ls, ls), 0); ImageDraw.Draw(lm).rounded_rectangle((0, 0, ls - 1, ls - 1), radius=int(ls * .2), fill=255)
    lx = int(H * 0.12); ly = (H - ls) // 2; im.paste(lg, (lx, ly), lm); d = ImageDraw.Draw(im)
    tx = lx + ls + int(H * 0.08)
    room = (int(W * 0.70) - 30 if shot else W - 34) - tx
    while True:
        ft = ImageFont.truetype(F + "Poppins-Bold.ttf", title_px)
        tb = d.textbbox((0, 0), "EX STORAGE LAB", font=ft)
        if tb[2] - tb[0] <= room or title_px < 12:
            break
        title_px -= 2
    ty = H // 2 - (tb[3] - tb[1]) - (int(title_px * .1) if sub else -int(title_px * .4))
    d.text((tx, ty), "EX STORAGE LAB", font=ft, fill=(236, 241, 247))
    grad_line(d, tx, ty + tb[3] + int(title_px * .22), tb[2] - tb[0], max(3, title_px // 14))
    if sub:
        sp = int(title_px * .40)
        while sp > 9 and d.textbbox((0, 0), "Free up space. You choose what goes.", font=ImageFont.truetype(F + "Poppins-Medium.ttf", sp))[2] > room:
            sp -= 1
        fs = ImageFont.truetype(F + "Poppins-Medium.ttf", sp)
        d.text((tx, ty + tb[3] + int(title_px * .45)), "Free up space. You choose what goes.", font=fs, fill=(165, 178, 196))
    return im


os.makedirs(OUT, exist_ok=True)
Image.open("assets/logo256.png").save(os.path.join(OUT, "icon.png"))
card((616, 353), None, 44).save(os.path.join(OUT, "capsule.jpg"), quality=90)
card((1600, 600), "shots_raw/shot_scan.png", 78).save(os.path.join(OUT, "hero.jpg"), quality=90)
for n, f in enumerate(("shot_scan", "shot_files", "shot_confirm", "shot_result", "shot_start")):
    Image.open("shots_raw/%s.png" % f).convert("RGB").save(os.path.join(OUT, "shot%d.jpg" % n), quality=90)
print(sorted(os.listdir(OUT)))
