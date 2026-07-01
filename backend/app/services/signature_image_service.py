from io import BytesIO

from PIL import Image, ImageDraw, ImageFont


class SignatureImageService:
    @staticmethod
    def create_company_signature() -> bytes:
        image = Image.new("RGBA", (600, 180), (255, 255, 255, 0))
        draw = ImageDraw.Draw(image)

        try:
            font_big = ImageFont.truetype("arial.ttf", 42)
            font_small = ImageFont.truetype("arial.ttf", 22)
        except Exception:
            font_big = ImageFont.load_default()
            font_small = ImageFont.load_default()

        draw.text((30, 35), "Internship Coordinator", fill=(20, 20, 20, 255), font=font_big)
        draw.text((35, 100), "Authorized Digital Signature", fill=(60, 60, 60, 255), font=font_small)
        draw.line((30, 140, 560, 140), fill=(20, 20, 20, 255), width=3)

        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()