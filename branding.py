from PIL import Image, ImageDraw, ImageFont
import math
import os

# ---------------------------------------------------------------------------
# Config — edit these to match your channel
# ---------------------------------------------------------------------------
LOGO_PATH = "assets/logo.png"

FACEBOOK_HANDLE = "facebook.com/thedcarchive"
TELEGRAM_HANDLE = "t.me/thedcarchive_notice"
SOURCE_SITE = "dhakacollege.edu.bd"

BAR_HEIGHT = 90
BG_COLOR = (10, 14, 26)            # near-black navy
TEXT_COLOR = (230, 230, 230)
SUBTEXT_COLOR = (150, 160, 175)

WATERMARK_TEXT = "THE DC ARCHIVE"
WATERMARK_COLOR = (45, 100, 200)   # slightly more saturated brand blue
WATERMARK_OPACITY = 56             # reduced slightly for the bolder design
WATERMARK_ANGLE = 40
WATERMARK_SPACING_X = 430         # wider spacing for brick pattern
WATERMARK_SPACING_Y = 290

FONT_BOLD_PATH = "assets/fonts/Inter-Bold.ttf"
FONT_REG_PATH = "assets/fonts/Inter-Regular.ttf"

def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        try:
            return ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", size)
        except OSError:
            return ImageFont.load_default()

def _tiled_watermark(size):
    """Faint repeating diagonal watermark layer, same size as the page.
    Redesigned to feature an alternating brick pattern with a subtext."""
    w, h = size
    font_main = _font(FONT_BOLD_PATH, 48)
    font_sub = _font(FONT_BOLD_PATH, 24)

    diag = int(math.hypot(w, h))
    tile = Image.new("RGBA", (diag, diag), (0, 0, 0, 0))
    tdraw = ImageDraw.Draw(tile)
    
    for row_idx, y in enumerate(range(0, diag, WATERMARK_SPACING_Y)):
        # Offset every other row for a brick-like pattern
        offset_x = (WATERMARK_SPACING_X // 2) if row_idx % 2 == 1 else 0
        for x in range(-offset_x, diag + offset_x, WATERMARK_SPACING_X):
            # Draw main text centered at (x, y)
            tdraw.text((x, y), WATERMARK_TEXT, font=font_main,
                       fill=WATERMARK_COLOR + (WATERMARK_OPACITY,), anchor="ma")

                       
    tile = tile.rotate(WATERMARK_ANGLE, expand=False)

    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    layer.paste(tile, (-(diag - w) // 2, -(diag - h) // 2), tile)
    return layer

def _load_logo(max_height):
    if not os.path.exists(LOGO_PATH):
        return None
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA")
        bbox = logo.getbbox()
        if bbox:
            logo = logo.crop(bbox)
        ratio = max_height / logo.height
        return logo.resize((max(1, int(logo.width * ratio)), max_height), Image.Resampling.LANCZOS)
    except Exception:
        return None

def add_branding(page_img: Image.Image) -> Image.Image:
    """
    page_img: a single rendered notice page, in its original, unmodified
              colors (do not pre-process/invert it before calling this).

    Returns: original page (untouched) + faint full-page watermark,
             with a footer bar appended below carrying logo + CTAs.
    """
    page_img = page_img.convert("RGBA")
    w, h = page_img.size

    # 1. Composite the faint watermark directly over the untouched original.
    watermark = _tiled_watermark((w, h))
    watermarked = Image.alpha_composite(page_img, watermark)

    # 2. Footer bar appended below — never overlaps the notice content.
    canvas = Image.new("RGBA", (w, h + BAR_HEIGHT), BG_COLOR + (255,))
    canvas.paste(watermarked, (0, 0))
    draw = ImageDraw.Draw(canvas)

    logo = _load_logo(max_height=BAR_HEIGHT - 30)
    text_x = 24
    if logo:
        canvas.paste(logo, (24, h + (BAR_HEIGHT - logo.height) // 2), logo)
        text_x = 24 + logo.width + 16

    font_bold = _font(FONT_BOLD_PATH, 22)
    font_reg = _font(FONT_REG_PATH, 15)

    draw.text((text_x, h + 18), "The DC Archive · Verified",
              font=font_bold, fill=TEXT_COLOR)
    draw.text(
        (text_x, h + 48),
        f"Follow: {FACEBOOK_HANDLE}   |   Subscribe telegram chennel for instant update: {TELEGRAM_HANDLE}",
        font=font_reg, fill=SUBTEXT_COLOR,
    )

    # Right-aligned source tag
    try:
        bbox = draw.textbbox((0, 0), SOURCE_SITE, font=font_reg)
        text_w = bbox[2] - bbox[0]
    except AttributeError:
        text_w = font_reg.getlength(SOURCE_SITE) if hasattr(font_reg, 'getlength') else 150

    draw.text((w - text_w - 24, h + 35), SOURCE_SITE,
              font=font_reg, fill=SUBTEXT_COLOR)

    return canvas.convert("RGB")
