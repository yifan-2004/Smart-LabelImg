"""Create original synthetic road scenes for the browser annotation demo."""
from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).parent / "web-demo"
root.mkdir(exist_ok=True)
for frame in range(3):
    image = Image.new("RGB", (1200, 750), "#d9e8f2")
    draw = ImageDraw.Draw(image)
    for x, height in [(25, 150), (160, 195), (330, 120), (450, 170), (900, 190), (1080, 150)]:
        draw.rectangle((x, 260-height, x+95, 290), fill="#b1c3cc")
        for wx in range(x+12, x+85, 24):
            for wy in range(280-height, 240, 30):
                draw.rectangle((wx, wy, wx+10, wy+13), fill="#e9f0ef")
    draw.rectangle((0, 260, 1200, 320), fill="#a9c6a1")
    draw.rectangle((0, 320, 1200, 750), fill="#414a57")
    draw.polygon([(550, 320), (650, 320), (890, 750), (310, 750)], fill="#515b69")
    for y in [350, 420, 520, 660]:
        draw.rectangle((596, y, 604, y+25), fill="#f7f3d8")
    for x, y, w, h, color in [(180+frame*12, 430, 260, 140, "#e8ac43"), (720+frame*8, 540, 300, 155, "#3b91bd"), (770+frame*4, 350, 150, 100, "#c56565")]:
        draw.rounded_rectangle((x, y, x+w, y+h), 20, fill=color)
        draw.polygon([(x+w*.2, y+10), (x+w*.73, y+10), (x+w*.88, y+65), (x+w*.08, y+65)], fill="#c6dce4")
        for wx in [x+int(w*.22), x+int(w*.78)]:
            draw.ellipse((wx-22, y+h-25, wx+22, y+h+18), fill="#202a37")
            draw.ellipse((wx-10, y+h-14, wx+10, y+h+7), fill="#a8b4bc")
    image.save(root / f"frame_{frame+1:03}.png")
(root / "classes.txt").write_text("car\n", encoding="utf-8")
