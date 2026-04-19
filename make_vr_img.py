"""Generate a synthetic tech/VR-glow image resembling the GrabHack 2.0 cover photo."""
from PIL import Image, ImageDraw, ImageFilter
import math, random

W, H = 900, 750
img = Image.new("RGB", (W, H), (5, 8, 20))
draw = ImageDraw.Draw(img)

# Dark radial base – deep navy centre-right
for r in range(350, 0, -1):
    alpha = int(30 * (1 - r / 350))
    draw.ellipse(
        [W // 2 - r, H // 2 - r, W // 2 + r, H // 2 + r],
        fill=None,
        outline=(0, 60 + alpha, 80 + alpha),
    )

# Concentric glow rings (cyan / teal)
ring_colors = [
    (0, 212, 208),
    (0, 168, 156),
    (0, 100, 120),
]
cx, cy = W // 2 + 80, H // 2
for i, (rr, col) in enumerate(zip([260, 190, 120], ring_colors)):
    for width in range(3, 0, -1):
        draw.ellipse(
            [cx - rr - width, cy - rr - width, cx + rr + width, cy + rr + width],
            outline=col,
            width=1,
        )

# Glowing horizontal light streaks (simulate VR visor reflection)
for y_off, intensity in [(-60, 180), (-30, 220), (0, 255), (30, 200), (60, 160)]:
    y = H // 2 + y_off
    for x in range(W // 4, W):
        dist = abs(x - (W // 2 + 80))
        fade = max(0, 1 - dist / 350)
        r_val = int(0 * fade * intensity / 255)
        g_val = int(200 * fade * intensity / 255)
        b_val = int(220 * fade * intensity / 255)
        draw.point((x, y), fill=(r_val, g_val, b_val))

# Abstract helmet silhouette (oval shape, dark with cyan edge glow)
hx, hy, hr = cx - 20, cy - 30, 130
# Outer glow
for offset in range(15, 0, -1):
    glow_alpha = int(80 * (1 - offset / 15))
    draw.ellipse(
        [hx - hr - offset, hy - int(hr * 1.2) - offset,
         hx + hr + offset, hy + int(hr * 1.2) + offset],
        outline=(0, glow_alpha * 2, glow_alpha * 3),
        width=1,
    )
# Solid helmet fill
draw.ellipse(
    [hx - hr, hy - int(hr * 1.2), hx + hr, hy + int(hr * 1.2)],
    fill=(8, 14, 35),
)
# Visor highlight (cyan strip)
draw.rectangle([hx - 80, hy - 25, hx + 60, hy + 10], fill=(0, 180, 200))
draw.rectangle([hx - 82, hy - 27, hx + 62, hy + 12], fill=None)

# Neck/body suggestion
draw.polygon(
    [(hx - 55, hy + int(hr * 1.2) - 10),
     (hx + 45, hy + int(hr * 1.2) - 10),
     (hx + 120, H),
     (hx - 130, H)],
    fill=(10, 16, 40),
)

# Edge: right-side cyan accent bars (3 bars)
for i, (y1, y2) in enumerate([(200, 290), (320, 370), (400, 430)]):
    draw.rectangle([W - 55, y1, W - 10, y2], fill=(0, 210, 205))

# Soft blur for glow effect
img = img.filter(ImageFilter.GaussianBlur(radius=1))

# Re-sharpen edges lightly
sharp = img.filter(ImageFilter.SHARPEN)
img = Image.blend(img, sharp, 0.4)

img.save("/home/user/saver/vr_cover.jpg", quality=92)
print("Saved vr_cover.jpg")
