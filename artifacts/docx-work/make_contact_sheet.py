from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

src = Path(r"D:\park-smart-harness\artifacts\docx-work\unpacked\word\media")
files = sorted(src.glob("image*.png"), key=lambda p: int(p.stem[5:]))
font = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 26)
label_font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 30)
cell_w, cell_h = 760, 520
cols = 3
rows = (len(files) + cols - 1) // cols
sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
draw = ImageDraw.Draw(sheet)

for index, path in enumerate(files):
    image = Image.open(path).convert("RGB")
    image.thumbnail((cell_w - 40, cell_h - 90))
    x0 = (index % cols) * cell_w
    y0 = (index // cols) * cell_h
    x = x0 + (cell_w - image.width) // 2
    y = y0 + 58 + (cell_h - 78 - image.height) // 2
    sheet.paste(image, (x, y))
    draw.text((x0 + 18, y0 + 14), f"{path.name}  {Image.open(path).size}", fill="#111827", font=label_font)
    draw.rectangle((x0, y0, x0 + cell_w - 1, y0 + cell_h - 1), outline="#CBD5E1", width=2)

sheet.save(src.parent.parent.parent / "contact-sheet.png")
