"""Build the mod page logo: publish/logo.png (4:3) plus a small preview at ModDB thumbnail size."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'stills/generated/9000026-t2i.png'   # Four Siblings
OUT = ROOT / 'publish/logo.png'
PREVIEW = ROOT / 'publish/logo_preview_130x98.png'
FONT = '/usr/share/fonts/truetype/ubuntu/Ubuntu[wdth,wght].ttf'
W, H = 1024, 768
GREEN, RED = (0, 102, 0), (218, 41, 28)   # Portuguese flag


def font(size, style='Condensed Extra Bold'):
    f = ImageFont.truetype(FONT, size)
    f.set_variation_by_name(style)
    return f


img = ImageOps.fit(ImageOps.grayscale(Image.open(SRC)), (W, H), centering=(0.5, 0.3)).convert('RGB')

# darken the lower half so the text reads
shade = Image.new('L', (W, H), 0)
d = ImageDraw.Draw(shade)
top = int(H * 0.42)
for y in range(top, H):
    d.line([(0, y), (W, y)], fill=int(235 * min(1, (y - top) / (H * 0.30))))
img = Image.composite(Image.new('RGB', (W, H), (0, 0, 0)), img, shade)

d = ImageDraw.Draw(img)
x = 56
title = font(140)
d.text((x, 548), 'PORTUGUESE', font=title, fill='white', anchor='ls')
d.text((x, 670), 'FILM PACK', font=title, fill='white', anchor='ls')

# flag stripe, 2/5 green and 3/5 red, then the subtitle on the same line
sy, sh, sw = 704, 14, 300
d.rectangle([x, sy, x + sw * 2 // 5, sy + sh], fill=GREEN)
d.rectangle([x + sw * 2 // 5, sy, x + sw, sy + sh], fill=RED)
sub = font(44, 'Condensed Bold')
d.text((x + sw + 24, sy + sh // 2), '80 FILMS · 1981-2005', font=sub, fill=(220, 220, 220), anchor='lm')

OUT.parent.mkdir(exist_ok=True)
img.save(OUT, optimize=True)
img.resize((130, 98), Image.LANCZOS).save(PREVIEW)
print(OUT, img.size)
