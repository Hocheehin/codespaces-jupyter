"""Make a printable QR poster for the app.

    python make_qr.py https://your-app-address            -> qr-poster.png
"""
import sys

import qrcode
from PIL import Image, ImageDraw, ImageFont

if len(sys.argv) < 2:
    sys.exit("Usage: python make_qr.py <app URL> [output.png]")
url, out = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "qr-poster.png")

q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=16, border=4)
q.add_data(url)
q.make()
code = q.make_image().convert("RGB")
W = code.width
poster = Image.new("RGB", (W, code.height + 260), "white")
poster.paste(code, (0, 150))
d = ImageDraw.Draw(poster)


def font(size):
    for f in ("DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


for y, t, s in [(30, "Feedback & Service Requests", 38), (90, "Scan with your phone camera", 28),
                (code.height + 170, "Compliment · Suggestion · Complaint · Fault/Repair", 22),
                (code.height + 210, "OPS_SOP_3.4_06", 20)]:
    f = font(s)
    d.text(((W - d.textlength(t, font=f)) / 2, y), t, fill="black", font=f)
poster.save(out)
print(f"Saved {out} for {url}")
