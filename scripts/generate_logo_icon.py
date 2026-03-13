from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
PNG_PATH = ASSETS / "wor-logo.png"
ICO_PATH = ASSETS / "wor-logo.ico"

SIZE = 1024


def _lerp(a: int, b: int, t: float) -> int:
    return round(a + (b - a) * t)


def build_gradient() -> Image.Image:
    start = (106, 112, 176)
    end = (78, 201, 205)
    image = Image.new("RGBA", (SIZE, SIZE))
    pixels = image.load()

    for x in range(SIZE):
        t = x / (SIZE - 1)
        color = (
            _lerp(start[0], end[0], t),
            _lerp(start[1], end[1], t),
            _lerp(start[2], end[2], t),
            255,
        )
        for y in range(SIZE):
            pixels[x, y] = color

    return image


def build_logo() -> Image.Image:
    gradient = build_gradient()
    mask = Image.new("L", (SIZE, SIZE), 0)
    draw = ImageDraw.Draw(mask)

    outer_shape = [
        (92, 182),
        (292, 170),
        (302, 428),
        (500, 186),
        (804, 530),
        (824, 158),
        (950, 156),
        (912, 866),
        (652, 880),
        (542, 606),
        (388, 884),
        (90, 856),
    ]
    draw.polygon(outer_shape, fill=255)

    logo = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    logo.paste(gradient, (0, 0), mask)

    cutouts = ImageDraw.Draw(logo)
    cutouts.polygon([(304, 176), (454, 182), (208, 432)], fill=(255, 255, 255, 0))
    cutouts.polygon([(618, 176), (776, 168), (816, 492)], fill=(255, 255, 255, 0))
    cutouts.polygon([(446, 622), (538, 622), (490, 754)], fill=(255, 255, 255, 0))

    return logo


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    logo = build_logo()
    logo.save(PNG_PATH)
    logo.save(ICO_PATH, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])


if __name__ == "__main__":
    main()
