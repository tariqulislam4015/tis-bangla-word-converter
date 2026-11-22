"""Generates TIS brand assets (icon, logo, splash, installer images).

Usage:  python packaging/make_assets.py <project-root>
Needs Pillow and the Inter font (OFL); adjust the FB/FS/FR paths below if Inter
is installed elsewhere (on Windows e.g. C:/Windows/Fonts/Inter-ExtraBold.otf).
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(sys.argv[1])
NAVY = (20, 36, 58); SLATE = (37, 59, 85); BLUE = (59, 130, 246); TEAL = (20, 184, 166)
WHITE = (255, 255, 255); OFF = (245, 247, 250)
FB = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FS = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
FR = "/usr/share/fonts/opentype/inter/InterDisplay-Medium.otf"

def mark(S=1024, tiny=False):
    """App mark: navy squircle, geometric 'ব' glyph, conversion arrow."""
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = int(S * 0.23)
    # vertical gradient navy -> slate
    grad = Image.new("RGBA", (S, S))
    gd = ImageDraw.Draw(grad)
    for y in range(S):
        t = y / S
        c = tuple(int(NAVY[i] * (1 - t) + SLATE[i] * t) for i in range(3)) + (255,)
        gd.line([(0, y), (S, y)], fill=c)
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], r, fill=255)
    im.paste(grad, (0, 0), mask)
    d = ImageDraw.Draw(im)
    u = S / 100
    lw = int((13 if tiny else 10) * u)
    # matra (headline)
    top = 24 * u
    d.rounded_rectangle([18 * u, top, 74 * u, top + lw], radius=lw // 2, fill=WHITE)
    # stem on the right
    sx = 62 * u
    bottom = 72 * u
    d.line([(sx, top + lw / 2), (sx, bottom)], fill=WHITE, width=lw)
    # left-pointing triangular bowl attached to the stem (the shape of ব)
    apex = (24 * u, 50 * u)
    tri = [(sx, top + lw * 0.9), apex, (sx, bottom), (sx, top + lw * 0.9)]
    d.line(tri, fill=WHITE, width=lw, joint="curve")
    for x, y in (apex, (sx, bottom)):
        d.ellipse([x - lw / 2, y - lw / 2, x + lw / 2, y + lw / 2], fill=WHITE)
    # conversion arrow (electric blue) with teal tip
    ay = 84 * u
    aw = int((8 if tiny else 6) * u)
    d.rounded_rectangle([18 * u, ay - aw / 2, 70 * u, ay + aw / 2], radius=aw // 2, fill=BLUE)
    d.polygon([(68 * u, ay - 9 * u), (84 * u, ay), (68 * u, ay + 9 * u)], fill=BLUE)
    d.ellipse([80 * u, 18 * u, 90 * u, 28 * u], fill=TEAL)
    return im

def save_icons():
    icons = OUT / "assets" / "icons"; icons.mkdir(parents=True, exist_ok=True)
    big = mark(1024)
    tiny = mark(1024, tiny=True)
    big.resize((256, 256), Image.LANCZOS).save(icons / "tis_logo_256.png")
    big.resize((512, 512), Image.LANCZOS).save(icons / "tis_logo_512.png")
    frames = []
    for s in (16, 20, 24, 32, 40, 48, 64, 128, 256):
        src = tiny if s <= 32 else big
        frames.append(src.resize((s, s), Image.LANCZOS))
    frames[-1].save(icons / "tis.ico", format="ICO", sizes=[f.size for f in frames],
                    append_images=frames[:-1])
    return big

def splash(big):
    W, H = 640, 360
    im = Image.new("RGBA", (W, H), NAVY + (255,))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        c = tuple(int(NAVY[i] * (1 - t) + (16, 24, 39)[i] * t) for i in range(3))
        d.line([(0, y), (W, y)], fill=c)
    d.rectangle([0, H - 6, W * 0.62, H], fill=BLUE)
    d.rectangle([W * 0.62, H - 6, W, H], fill=TEAL)
    logo = big.resize((132, 132), Image.LANCZOS)
    im.alpha_composite(logo, (52, 92))
    d.text((210, 92), "TIS", font=ImageFont.truetype(FB, 64), fill=WHITE)
    d.text((212, 168), "Bangla Word Converter", font=ImageFont.truetype(FS, 26), fill=WHITE)
    d.text((212, 206), "Smart Bengali Text & Document Conversion", font=ImageFont.truetype(FR, 15),
           fill=(169, 184, 204))
    d.text((212, 232), "Unicode to Bijoy  |  SolaimanLipi to SutonnyMJ", font=ImageFont.truetype(FR, 15),
           fill=(169, 184, 204))
    d.text((W - 92, 24), "v1.5.0", font=ImageFont.truetype(FR, 13), fill=(143, 163, 189))
    d.text((52, H - 40), "Loading…", font=ImageFont.truetype(FR, 13), fill=(143, 163, 189))
    imgs = OUT / "assets" / "images"; imgs.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(imgs / "splash.png")

def installer_images(big):
    # Inno Setup: large wizard image 164x314 (and 2x), small 55x55 (and 2x)
    inst = OUT / "packaging" / "installer_config"; inst.mkdir(parents=True, exist_ok=True)
    for scale in (1, 2):
        W, H = 164 * scale, 314 * scale
        im = Image.new("RGB", (W, H), NAVY)
        d = ImageDraw.Draw(im)
        for y in range(H):
            t = y / H
            c = tuple(int(NAVY[i] * (1 - t) + SLATE[i] * t) for i in range(3))
            d.line([(0, y), (W, y)], fill=c)
        lg = big.resize((96 * scale, 96 * scale), Image.LANCZOS)
        im.paste(lg, ((W - lg.width) // 2, 60 * scale), lg)
        f1 = ImageFont.truetype(FB, 34 * scale); f2 = ImageFont.truetype(FS, 12 * scale)
        for text, f, y, col in (("TIS", f1, 176, WHITE), ("Bangla Word", f2, 222, (200, 212, 228)),
                                ("Converter", f2, 240, (200, 212, 228))):
            w = d.textlength(text, font=f)
            d.text(((W - w) / 2, y * scale), text, font=f, fill=col)
        d.rectangle([0, H - 5 * scale, W, H], fill=BLUE)
        im.save(inst / f"wizard_large{'' if scale == 1 else '@2x'}.bmp")
        s = 55 * scale
        sm = Image.new("RGB", (s, s), WHITE)
        lg2 = big.resize((s - 6 * scale, s - 6 * scale), Image.LANCZOS)
        sm.paste(lg2, (3 * scale, 3 * scale), lg2)
        sm.save(inst / f"wizard_small{'' if scale == 1 else '@2x'}.bmp")

big = save_icons(); splash(big); installer_images(big)
print("assets written")
