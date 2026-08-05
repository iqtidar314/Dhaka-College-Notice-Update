# The DC Archive — Premium UX Optimization Strategy
**Version 3.0 Redesign Blueprint**
*Generated: 2026-05-03*

---

## Executive Summary

Your current system functions correctly but presents as a utility rather than a premium service. This document transforms it into **The DC Archive** — a branded intelligence platform that students trust and forward. The core shift: stop sending notices, start broadcasting intelligence.

---

## 1. Visual Hierarchy & Aesthetics: The "System Log" Aesthetic

### Current Problem
Plain text with emoji prefixes reads like a script output. There's no visual hierarchy distinguishing the *title* from the *metadata* from the *links*.

### Proposed Caption Template

```python
# telegram_utils.py — new caption builder

def build_notice_caption(notice: dict, change_type: str) -> str:
    change_icons = {
        "NEW":               "🆕",
        "EDITED":            "✏️",
        "PDF_REPLACED":      "🔄",
        "REMOVED_FROM_PAGE_1": "📤",
    }
    change_label = {
        "NEW":               "NEW NOTICE",
        "EDITED":            "UPDATED",
        "PDF_REPLACED":      "PDF REPLACED",
        "REMOVED_FROM_PAGE_1": "MOVED OFF PAGE 1",
    }

    icon  = change_icons.get(change_type, "📌")
    label = change_label.get(change_type, "NOTICE")

    caption = (
        f"{icon} <b>{label}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>{notice['title']}</b>\n"
        f"\n"
        f"<code>📅 {notice['date']}  |  #️⃣ Serial {notice['serial']}</code>\n"
        f"\n"
        f"<i>The DC Archive — Notice Monitor</i>"
    )
    return caption
```

### Why This Works
- **Bold title** = immediate hierarchy. First thing eyes land on.
- **Horizontal rule** (━━━) = visual separator that looks intentional, not decorative.
- **Monospace metadata** = "system log" feel. Date and serial in `<code>` tags render in a distinct font in Telegram, creating a data-terminal aesthetic.
- **Italic branding footer** = subtle, professional, never shouting.
- The change type badge (`NEW`, `UPDATED`) trains students to read the state at a glance.

---

## 2. Dark Mode PDF Transformation

### Current Problem
White-background PDFs look jarring in dark mode Telegram (the dominant mode for students on mobile at night). The content is unreadable in low light.

### The "Dark Intelligence" Transform Pipeline

Implement this in `content_processor.py`:

```python
# content_processor.py — Dark Mode Transform

import fitz  # PyMuPDF
from PIL import Image, ImageOps, ImageFilter, ImageDraw
import numpy as np

# --- STEP 1: SMART CROP ---
def smart_crop_whitespace(img: Image.Image, threshold=245, padding=20) -> Image.Image:
    """Remove white borders while preserving content."""
    img_array = np.array(img.convert("RGB"))
    # Find rows/cols that are NOT pure white
    mask = np.any(img_array < threshold, axis=2)
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    if not rows.any():
        return img
    rmin, rmax = np.where(rows)[0][[0, -1]]
    cmin, cmax = np.where(cols)[0][[0, -1]]
    # Add padding back
    h, w = img_array.shape[:2]
    rmin = max(0, rmin - padding)
    rmax = min(h, rmax + padding)
    cmin = max(0, cmin - padding)
    cmax = min(w, cmax + padding)
    return img.crop((cmin, rmin, cmax, rmax))

# --- STEP 2: DARK MODE INVERT ---
def apply_dark_mode(img: Image.Image) -> Image.Image:
    """
    Intelligent inversion:
    - Inverts the base image (white → dark navy, black text → light)
    - Applies a dark navy tint instead of pure black background
    - Preserves color data in charts (uses luminance-only inversion)
    """
    # Convert to numpy for processing
    img_rgb = img.convert("RGB")
    arr = np.array(img_rgb, dtype=np.float32)
    
    # Invert: new_pixel = 255 - old_pixel
    inverted = 255.0 - arr
    
    # Tint: shift toward navy (#1a1f2e) instead of pure black
    # Navy RGB: (26, 31, 46)
    navy = np.array([26, 31, 46], dtype=np.float32)
    # Blend: 85% inverted + 15% navy tint for warmth
    tinted = inverted * 0.85 + navy * 0.15
    tinted = np.clip(tinted, 0, 255).astype(np.uint8)
    
    return Image.fromarray(tinted)

# --- STEP 3: CANVAS EXPANSION BRANDING ---
BRAND_BAR_HEIGHT = 72  # px at 150dpi render

def add_branding_bar(img: Image.Image, is_dark: bool = True) -> Image.Image:
    """
    Adds an UNCROPABLE branding bar by EXPANDING the canvas downward.
    The bar is part of the image — not an overlay.
    """
    from PIL import ImageFont
    
    w, h = img.size
    bar_h = BRAND_BAR_HEIGHT
    
    # Create new canvas
    bg_color = (18, 22, 36) if is_dark else (245, 245, 247)
    new_img = Image.new("RGB", (w, h + bar_h), bg_color)
    new_img.paste(img, (0, 0))
    
    draw = ImageDraw.Draw(new_img)
    
    # Accent line at the top of the bar
    accent_color = (99, 179, 237)  # Telegram-blue accent
    draw.rectangle([(0, h), (w, h + 3)], fill=accent_color)
    
    # Brand name
    try:
        font_large = ImageFont.truetype("assets/fonts/Inter-Bold.ttf", 22)
        font_small = ImageFont.truetype("assets/fonts/Inter-Regular.ttf", 15)
    except:
        font_large = ImageFont.load_default()
        font_small = font_large
    
    text_color = (220, 230, 245) if is_dark else (30, 40, 60)
    muted_color = (120, 140, 165) if is_dark else (100, 110, 130)
    
    # Left: "The DC Archive" logo area
    draw.text((20, h + 10), "The DC Archive", font=font_large, fill=text_color)
    draw.text((20, h + 40), "t.me/thedcarchive_notice", font=font_small, fill=muted_color)
    
    # Right: separator + "Notice Monitor"
    draw.text((w - 200, h + 10), "Notice Monitor", font=font_large, fill=accent_color)
    draw.text((w - 200, h + 40), "dhakacollege.edu.bd", font=font_small, fill=muted_color)
    
    # Vertical divider in center
    mid_x = w // 2
    draw.rectangle([(mid_x - 1, h + 12), (mid_x + 1, h + bar_h - 12)], fill=muted_color)
    
    return new_img
```

### Color Palette for Dark Mode Output

| Element | Color | Hex |
|---|---|---|
| Background | Deep Navy | `#121624` |
| Text (primary) | Ice White | `#DCE6F5` |
| Text (muted) | Slate | `#7890A5` |
| Accent line | Telegram Blue | `#63B3ED` |
| Brand name | Ice White | `#DCE6F5` |
| Monitor label | Accent Blue | `#63B3ED` |

---

## 3. Inline Keyboard — The Button Architecture

### Current Problem
Text links (`🔗 Download PDF`, `🌐 View on Website`) take up 4 lines of caption. They look like a README, not a product.

### Proposed Button Layout

```python
# telegram_utils.py — Inline Keyboard Builder

def build_inline_keyboard(notice: dict) -> dict:
    """
    Row 1: [⬇ PDF]  [🌐 Website]
    Row 2: [👥 Facebook]  [📢 Channel]
    
    Two rows, two buttons each. Maximum utility, minimum vertical space.
    """
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "⬇️  Download PDF",
                    "url": notice["download_url"]
                },
                {
                    "text": "🌐  View on Website",
                    "url": "https://www.dhakacollege.edu.bd/en/notice"
                }
            ],
            [
                {
                    "text": "👥  Facebook",
                    "url": "https://www.facebook.com/thedcarchive"
                },
                {
                    "text": "📢  Join Channel",
                    "url": "https://t.me/thedcarchive_notice"
                }
            ]
        ]
    }
    return keyboard

# In send_media_group or sendMessage:
# Add reply_markup=json.dumps(build_inline_keyboard(notice))
```

### Why 2×2 is Optimal
- **Row 1** = action buttons (what students need RIGHT NOW).
- **Row 2** = discovery buttons (grow your audience passively).
- Two columns = compact on mobile.
- Inline keyboards survive forwarding — when a student forwards the message to their class group, **the buttons forward with it** and still point to your links.

---

## 4. Media Layout Engineering: Image Stitching

### Current Problem
Telegram's auto-album creates a 3-column grid of tiny, unreadable thumbnails for multi-page PDFs. Students can't read anything without tapping each image.

### The "Master Sheet" Strategy

For result sheets (multi-page wide spreadsheets), stitch pages into a vertical composite:

```python
# content_processor.py — Master Sheet Compositor

from PIL import Image

def stitch_pages_vertical(
    page_images: list[Image.Image],
    max_width: int = 1920,
    gap: int = 8,
    gap_color: tuple = (18, 22, 36),
    max_pages_to_stitch: int = 6
) -> list[Image.Image]:
    """
    Strategy:
    - If 1-3 pages: stitch vertically into one tall image
    - If 4-8 pages: stitch into a 2-column grid
    - If 9+ pages: send as document (don't try to stitch)
    
    Returns a list of output images (usually just 1, sometimes 2).
    """
    n = len(page_images)
    
    if n == 0:
        return []
    
    if n <= 3:
        # Single vertical strip
        return [_stitch_vertical(page_images, max_width, gap, gap_color)]
    
    elif n <= 8:
        # 2-column grid: left column = odd pages, right = even
        left  = page_images[0::2]
        right = page_images[1::2]
        col_w = (max_width - gap) // 2
        left_strip  = _stitch_vertical(left,  col_w, gap, gap_color)
        right_strip = _stitch_vertical(right, col_w, gap, gap_color)
        return [_stitch_horizontal([left_strip, right_strip], gap, gap_color)]
    
    else:
        # Too many pages: just send the first 2 as preview + document
        return page_images[:2]

def _stitch_vertical(images, max_width, gap, gap_color):
    scaled = []
    for img in images:
        r = max_width / img.width
        scaled.append(img.resize((int(img.width * r), int(img.height * r)), Image.LANCZOS))
    
    total_h = sum(i.height for i in scaled) + gap * (len(scaled) - 1)
    canvas = Image.new("RGB", (max_width, total_h), gap_color)
    y = 0
    for img in scaled:
        canvas.paste(img, (0, y))
        y += img.height + gap
    return canvas

def _stitch_horizontal(images, gap, gap_color):
    total_w = sum(i.width for i in images) + gap * (len(images) - 1)
    max_h   = max(i.height for i in images)
    canvas  = Image.new("RGB", (total_w, max_h), gap_color)
    x = 0
    for img in images:
        canvas.paste(img, (x, 0))
        x += img.width + gap
    return canvas
```

### Decision Logic (add to `content_processor.py`)

```python
def process_pdf_for_telegram(pdf_path: str, notice: dict) -> dict:
    """
    Returns:
    {
      "send_mode": "album" | "single" | "document_only",
      "images": [PIL.Image, ...],         # processed images
      "send_document": bool,               # always True (raw PDF always sent)
      "caption": str,
    }
    """
    pages = render_pdf_to_images(pdf_path, dpi=150)
    
    # Apply dark mode + crop to each page
    processed = []
    for page in pages:
        page = smart_crop_whitespace(page)
        page = apply_dark_mode(page)
        processed.append(page)
    
    # Stitch
    stitched = stitch_pages_vertical(processed)
    
    # Add branding bar to EACH stitched image (so it's always visible)
    final_images = [add_branding_bar(img, is_dark=True) for img in stitched]
    
    if len(final_images) == 1:
        send_mode = "single"
    else:
        send_mode = "album"
    
    return {
        "send_mode": send_mode,
        "images": final_images,
        "send_document": True,
    }
```

---

## 5. Viral "Forwarding" Optimization

### The Forwarding Problem
When a student forwards your message to their class group:
- Telegram adds "Forwarded from [Channel Name]" at the top — free branding.
- BUT: the forwarded message *loses inline keyboard buttons* in Telegram's current behavior if the source message is in a channel with certain settings.

### The Solution: "Forward-Proof" Caption Branding

Embed the essential identity INTO the caption text (not just buttons), so it survives any forwarding context:

```python
# The forward-proof footer (always at the bottom of caption)

FORWARD_FOOTER = (
    "\n\n"
    "━━━━━━━━━━━━━━━━━━━━\n"
    "🏛 <b>The DC Archive</b> — Dhaka College Notice Monitor\n"
    "📢 <a href='https://t.me/thedcarchive_notice'>Subscribe for instant alerts</a>"
)
```

This achieves:
1. Even if buttons don't forward, the channel link is in the text.
2. The "Subscribe for instant alerts" CTA converts readers in class groups into subscribers.
3. The `━━━` separator makes it look designed — not an afterthought.

### Channel Name Strategy
Set your channel username to `@thedcarchive_notice` (already done) and ensure the channel has **"Forwarded from" links enabled** in channel settings so every forward carries your brand.

---

## 6. Module-by-Module Implementation Plan

### `content_processor.py` — Changes Required

| Function | Change | Priority |
|---|---|---|
| `render_pdf_to_images()` | Increase DPI from default to 150 for mobile clarity | HIGH |
| `smart_crop_whitespace()` | **ADD** — new function | HIGH |
| `apply_dark_mode()` | **ADD** — new function | HIGH |
| `add_branding_bar()` | **REPLACE** current logo overlay with canvas expansion | HIGH |
| `stitch_pages_vertical()` | **ADD** — new function | MEDIUM |
| `process_pdf_for_telegram()` | **REFACTOR** — orchestrate new pipeline | HIGH |

### `telegram_utils.py` — Changes Required

| Function | Change | Priority |
|---|---|---|
| `build_notice_caption()` | **ADD** — new function with HTML template | HIGH |
| `build_inline_keyboard()` | **ADD** — replaces text links | HIGH |
| `send_notice_message()` | Pass `reply_markup` to all send calls | HIGH |
| `send_media_group()` | Attach inline keyboard to the LAST image or send as separate message | MEDIUM |

### `monitor.py` — Changes Required

| Section | Change | Priority |
|---|---|---|
| Notice dispatch | Pass `change_type` to caption builder | MEDIUM |
| Duplicate detection | **INVESTIGATE**: screenshots show same notice sent 3× — add `sent_ids` set in memory per run | CRITICAL |

### `dashboard_manager.py` — Changes Required

| Section | Change | Priority |
|---|---|---|
| Status message | Apply same HTML formatting template | LOW |
| Stats display | Use `<code>` for numbers, bold for labels | LOW |

---

## 7. Critical Bug: Duplicate Sends

**From screenshots**: The notice "XI (2025-2026) Half Yearly Science Result" (Serial: 8) appears sent at **12:47 AM**, **12:48 AM**, and **12:48 AM again**. This is a serious UX problem — students see triple notifications.

### Likely Cause
The cache is being checked BEFORE sending, but a race condition or retry logic in the media group send is re-triggering the pipeline for the same notice.

### Fix (add to `monitor.py`)

```python
# At the top of the run() function
_dispatched_this_run: set[str] = set()

def dispatch_notice(notice: dict, change_type: str):
    if notice["id"] in _dispatched_this_run:
        logger.warning(f"Skipping duplicate dispatch for {notice['id']}")
        return
    _dispatched_this_run.add(notice["id"])
    # ... existing send logic
```

---

## 8. Complete New Message Flow

```
PDF Notice Detected
        │
        ▼
render_pdf_to_images(dpi=150)
        │
        ▼
[per page] smart_crop_whitespace()
        │
        ▼
[per page] apply_dark_mode()
        │
        ▼
stitch_pages_vertical() → 1 or 2 composite images
        │
        ▼
[per image] add_branding_bar() ← CANVAS EXPANDED, not overlaid
        │
        ▼
build_notice_caption() ← HTML formatted, change-type aware
        │
        ▼
build_inline_keyboard() ← 2×2 button grid
        │
        ├── sendPhoto/sendMediaGroup (images + caption + keyboard)
        │
        └── sendDocument (raw PDF, silent, caption = "Original PDF: {title}")
```

---

## 9. Aesthetic Reference: Before vs After

### Before (Current)
```
[3-column album of white PDF pages]

🗂 The DC Archive — Notice

XI (2025-2026) Half Yearly Science Result
📅 19-04-2026
🔖 Serial: 8

🔗 Download PDF
🌐 View on Website
👥 Facebook
📢 Telegram
                              12:47 AM
```

### After (Proposed)
```
[1-2 dark-mode stitched composite images with branding bar]

🆕 NEW NOTICE
━━━━━━━━━━━━━━━━━━━━
XI (2025-2026) Half Yearly Science Result

📅 19-04-2026  |  #️⃣ Serial 8

The DC Archive — Notice Monitor

━━━━━━━━━━━━━━━━━━━━
🏛 The DC Archive — Dhaka College Notice Monitor
📢 Subscribe for instant alerts

[⬇️ Download PDF]  [🌐 View on Website]
[👥 Facebook]      [📢 Join Channel]
                              12:47 AM
```

---

## 10. Pending Improvements (for v3.1)

- **Notice type detection**: Auto-tag notices as `#result`, `#exam`, `#admission`, `#routine` based on title keywords. Add the hashtag to the caption. This makes your channel searchable inside Telegram.
- **Thread/reply grouping**: If the same notice is EDITED, send the update as a *reply to the original message* (store `message_id` in cache) instead of a new top-level message. Cleaner channel history.
- **Silent hours**: Between 11 PM and 6 AM, set `disable_notification: true` on sends. Students still get the notice when they wake up, but won't be disturbed at 3 AM.

---

*End of DC Archive Optimization Strategy — v3.0*
*Repository: https://github.com/iqtidar314/Dhaka-College-Notice-Update*