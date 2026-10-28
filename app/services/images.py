import io
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_DIMENSION = 1920
MAX_PIXELS = 40_000_000

Image.MAX_IMAGE_PIXELS = MAX_PIXELS


class InvalidImageError(ValueError):
    pass


@dataclass
class ProcessedImage:
    data: bytes
    width: int
    height: int
    content_type: str = "image/webp"
    extension: str = "webp"


def process_car_image(raw: bytes) -> ProcessedImage:
    try:
        with Image.open(io.BytesIO(raw)) as probe:
            if probe.format not in ALLOWED_FORMATS:
                raise InvalidImageError("Only JPEG, PNG or WebP images are allowed")
            probe.verify()
        with Image.open(io.BytesIO(raw)) as img:
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGBA" if img.mode in ("RGBA", "LA", "P") else "RGB")
            img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            img.save(out, format="WEBP", quality=82, method=4)
            return ProcessedImage(data=out.getvalue(), width=img.width, height=img.height)
    except InvalidImageError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError) as exc:
        raise InvalidImageError("The file is not a valid image") from exc
