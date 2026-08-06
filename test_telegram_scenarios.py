"""
test_telegram_scenarios.py
──────────────────────────
Integration test suite that sends REAL Telegram messages to verify every
failure/success path in send_notice_with_media and related helpers.

Each test case describes the scenario in a header message sent to the channel,
then triggers the actual code path, so you can see in Telegram exactly what
each case looks like.

Run:  python test_telegram_scenarios.py
"""

import os
import sys
import time
import textwrap
from unittest.mock import patch, MagicMock
from io import BytesIO

# ── Load .env (PowerShell format: $env:KEY="VALUE") ──────────────────────────
import re as _re
_env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(_env_path):
    with open(_env_path, encoding='utf-8') as _f:
        for _line in _f:
            _m = _re.match(r'\$env:(\w+)\s*=\s*["\']?([^"\']+)["\']?', _line.strip())
            if _m:
                os.environ.setdefault(_m.group(1), _m.group(2).strip())

from telegram_utils import TelegramUtils, _link_footer

# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_tg() -> TelegramUtils:
    """Fresh TelegramUtils instance."""
    return TelegramUtils()


def _tiny_png() -> bytes:
    """Minimal valid 1×1 PNG (doesn't need PIL)."""
    import struct, zlib
    def chunk(name: bytes, data: bytes) -> bytes:
        c = name + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xFFFFFFFF)
    sig   = b'\x89PNG\r\n\x1a\n'
    ihdr  = chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
    raw   = b'\x00\xff\x00\x00'              # filter byte + 1 pixel (green)
    idat  = chunk(b'IDAT', zlib.compress(raw))
    iend  = chunk(b'IEND', b'')
    return sig + ihdr + idat + iend


def _fake_pdf() -> bytes:
    """Minimal valid PDF bytes (Telegram accepts it as a document)."""
    return (
        b'%PDF-1.4\n'
        b'1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n'
        b'2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n'
        b'3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n'
        b'xref\n0 4\n0000000000 65535 f \n'
        b'trailer<</Size 4/Root 1 0 R>>\n'
        b'startxref 0\n%%EOF'
    )


NOTICE_BASE = {
    'id':           'test-scenario-id',
    'title':        '',          # filled per test
    'date':         '07-08-2026',
    'download_url': 'https://dhakacollege.blr1.digitaloceanspaces.com/notice/6fb84f02929fcec7-উচ্চমাধ্যমিক-সার্টিফিকেট-পরীক্ষা-২০২৬-এর-গ্রুপভিত্তিক-ব্যবহারিক-পরীক্ষার-সময়সূচি.pdf',
}


PASS = '✅'
FAIL = '❌'
SEP  = '━' * 30


def header(tg: TelegramUtils, case_no: int, label: str, description: str):
    """Send a section header to Telegram so each test is labelled in chat."""
    text = (
        f"<b>[TEST {case_no}] {label}</b>\n"
        f"<blockquote>{description}</blockquote>"
    )
    tg.send_message(text, disable_notification=True)
    time.sleep(0.5)   # avoid flood limit


def result_msg(ok: bool, detail: str = '') -> str:
    icon = PASS if ok else FAIL
    return f"{icon} {'PASS' if ok else 'FAIL'}" + (f" — {detail}" if detail else '')


# ── Test Cases ────────────────────────────────────────────────────────────────

results = []


def run(case_no, label, description, fn):
    print(f"\n{SEP}\nTest {case_no}: {label}")
    tg = _make_tg()
    header(tg, case_no, label, description)
    try:
        ok, detail = fn(tg)
        results.append((case_no, label, ok, detail))
        print(result_msg(ok, detail))
    except Exception as exc:
        results.append((case_no, label, False, str(exc)))
        print(f"{FAIL} EXCEPTION: {exc}")
    time.sleep(1.5)   # breathing room between tests


# ─────────────────────────────────────────────────────────────────────────────
# CASE 1 — Happy path: single image, no PDF needed
# ─────────────────────────────────────────────────────────────────────────────
def case_01(tg):
    notice = {**NOTICE_BASE, 'title': '[TC-01] Happy path — 1 image, no PDF needed'}
    result_list, all_sent = tg.send_notice_with_media(
        notice, 'NEW',
        images=[_tiny_png()],
        pdf_bytes=None,
    )
    ok = bool(result_list) and all_sent
    return ok, f"message_ids={[r.get('message_id') for r in result_list]}"


run(1, "Happy path — 1 image", "Single image sent successfully, no PDF attached.", case_01)


# ─────────────────────────────────────────────────────────────────────────────
# CASE 2 — Happy path: multi-image album (3 pages)
# ─────────────────────────────────────────────────────────────────────────────
def case_02(tg):
    notice = {**NOTICE_BASE, 'title': '[TC-02] Happy path — 3-page album'}
    result_list, all_sent = tg.send_notice_with_media(
        notice, 'NEW',
        images=[_tiny_png(), _tiny_png(), _tiny_png()],
        pdf_bytes=_fake_pdf(),
    )
    ok = bool(result_list) and all_sent
    return ok, f"messages_sent={len(result_list)}"


run(2, "Happy path — 3-image album", "Three images in a media group, PDF should NOT be sent.", case_02)


# ─────────────────────────────────────────────────────────────────────────────
# CASE 3 — No images at all, PDF available → PDF sent, no URL message
# ─────────────────────────────────────────────────────────────────────────────
def case_03(tg):
    notice = {**NOTICE_BASE, 'title': '[TC-03] No images, PDF available — PDF should be sent'}
    result_list, all_sent = tg.send_notice_with_media(
        notice, 'NEW',
        images=[],
        pdf_bytes=_fake_pdf(),
    )
    # all_sent is False (no images), but a doc should be in results
    pdf_sent = len(result_list) >= 2   # text message + PDF document
    return pdf_sent, f"all_sent={all_sent}, results={len(result_list)}"


run(3, "No images — PDF fallback", "0 images, PDF available. Expect text caption + PDF document.", case_03)


# ─────────────────────────────────────────────────────────────────────────────
# CASE 4 — Image upload fails → PDF fallback triggered
# ─────────────────────────────────────────────────────────────────────────────
def case_04(tg):
    notice = {**NOTICE_BASE, 'title': '[TC-04] Image upload fails — PDF fallback triggered'}
    original_send_photo = tg.send_photo

    def _failing_photo(photo_bytes, caption, **kw):
        print("  [MOCK] send_photo forced to fail")
        return None   # simulate API failure

    tg.send_photo = _failing_photo
    result_list, all_sent = tg.send_notice_with_media(
        notice, 'NEW',
        images=[_tiny_png()],
        pdf_bytes=_fake_pdf(),
    )
    tg.send_photo = original_send_photo
    pdf_sent = any(r for r in result_list)
    return pdf_sent, f"all_sent={all_sent}, fallback_results={len(result_list)}"


run(4, "Image upload fails → PDF fallback", "send_photo forced to return None. Expect PDF document sent.", case_04)


# ─────────────────────────────────────────────────────────────────────────────
# CASE 5 — Image upload fails AND PDF also fails → download URL message sent
# ─────────────────────────────────────────────────────────────────────────────
def case_05(tg):
    notice = {**NOTICE_BASE, 'title': '[TC-05] Image AND PDF both fail — raw URL fallback'}
    original_send_photo    = tg.send_photo
    original_send_document = tg.send_document

    def _fail_photo(photo_bytes, caption, **kw):
        print("  [MOCK] send_photo forced to fail")
        return None

    def _fail_doc(file_bytes, filename, **kw):
        print("  [MOCK] send_document forced to fail")
        return None

    tg.send_photo    = _fail_photo
    tg.send_document = _fail_doc
    result_list, all_sent = tg.send_notice_with_media(
        notice, 'NEW',
        images=[_tiny_png()],
        pdf_bytes=_fake_pdf(),
    )
    tg.send_photo    = original_send_photo
    tg.send_document = original_send_document
    # Expect a URL fallback message (the text message with download link)
    got_url_fallback = len(result_list) >= 1
    return got_url_fallback, f"all_sent={all_sent}, results={len(result_list)}"


run(5, "Image AND PDF fail → URL fallback", "Both send_photo and send_document return None. Expect raw URL message.", case_05)


# ─────────────────────────────────────────────────────────────────────────────
# CASE 6 — Image AND PDF fail, NO download_url → nothing sent (graceful)
# ─────────────────────────────────────────────────────────────────────────────
def case_06(tg):
    notice = {**NOTICE_BASE,
              'title': '[TC-06] Image+PDF fail, no URL — text+footer fallback sent',
              'download_url': ''}

    original_send_photo    = tg.send_photo
    original_send_document = tg.send_document
    tg.send_photo    = lambda *a, **k: None
    tg.send_document = lambda *a, **k: None

    result_list, all_sent = tg.send_notice_with_media(
        notice, 'NEW',
        images=[_tiny_png()],
        pdf_bytes=_fake_pdf(),
    )
    tg.send_photo    = original_send_photo
    tg.send_document = original_send_document
    # Expect exactly 1 fallback text message (caption + footer, no URL)
    ok = len(result_list) == 1 and not all_sent
    return ok, f"results={len(result_list)} (expected 1 — text+footer fallback)"


run(6, "Image+PDF fail, no URL — text fallback", "No download_url. After all failures, a text caption+footer should still be sent.", case_06)


# ─────────────────────────────────────────────────────────────────────────────
# CASE 7 — EDITED notice (caption changes)
# ─────────────────────────────────────────────────────────────────────────────
def case_07(tg):
    notice = {**NOTICE_BASE, 'title': '[TC-07] EDITED notice — updated caption'}
    result_list, all_sent = tg.send_notice_with_media(
        notice, 'EDITED',
        images=[_tiny_png()],
        pdf_bytes=None,
    )
    ok = bool(result_list)
    return ok, f"message_ids={[r.get('message_id') for r in result_list]}"


run(7, "EDITED notice", "Change type EDITED — caption should show 'Updated' label.", case_07)


# ─────────────────────────────────────────────────────────────────────────────
# CASE 8 — REMOVED_FROM_PAGE_1 notification
# ─────────────────────────────────────────────────────────────────────────────
def case_08(tg):
    notice = {**NOTICE_BASE, 'title': '[TC-08] Notice removed from front page'}
    result = tg.send_removed_notification(notice)
    ok = result is not None
    return ok, f"message_id={result.get('message_id') if result else None}"


run(8, "REMOVED_FROM_PAGE_1 notification", "send_removed_notification() should post a removal alert.", case_08)


# ─────────────────────────────────────────────────────────────────────────────
# CASE 9 — format_deleted_label applied to a message (edit simulation)
# ─────────────────────────────────────────────────────────────────────────────
def case_09(tg):
    notice = {**NOTICE_BASE, 'title': '[TC-09] Message gets DELETED label edit'}
    # First send a normal message
    original_caption = tg.build_notice_caption(notice, 'NEW')
    send_result = tg.send_message(original_caption)
    if not send_result:
        return False, "initial send failed"
    msg_id = send_result.get('message_id')
    time.sleep(0.5)
    # Now edit it to prepend [DELETED]
    deleted_text = tg.format_deleted_label(original_caption)
    edit_result = tg.edit_message(msg_id, deleted_text)
    ok = edit_result is not None
    return ok, f"edited message_id={msg_id}"


run(9, "DELETED label edit", "Send a message then edit it to prepend [DELETED].", case_09)


# ─────────────────────────────────────────────────────────────────────────────
# CASE 10 — Telegram API error response (bad token simulation)
# ─────────────────────────────────────────────────────────────────────────────
def case_10(tg):
    notice = {**NOTICE_BASE, 'title': '[TC-10] API error — bad token response (should log & not crash)'}
    # Patch requests.post to return a fake "401 Unauthorized" response
    mock_response = MagicMock()
    mock_response.json.return_value = {'ok': False, 'description': 'Unauthorized (simulated)'}

    tg.send_message(
        "<b>[TC-10]</b> Next call will simulate a Telegram API error (logged below)...",
        disable_notification=True
    )
    time.sleep(0.5)

    with patch('telegram_utils.requests.post', return_value=mock_response):
        result = tg.send_photo(_tiny_png(), caption='Should not appear')

    ok = result is None   # must return None cleanly, not raise
    return ok, "returned None gracefully on API error"


run(10, "API error — bad token (simulated)", "requests.post returns {'ok': False}. Code must log and return None without crashing.", case_10)


# ─────────────────────────────────────────────────────────────────────────────
# CASE 11 — Network timeout simulation
# ─────────────────────────────────────────────────────────────────────────────
def case_11(tg):
    import requests as req_lib
    notice = {**NOTICE_BASE, 'title': '[TC-11] Network timeout (simulated)'}
    tg.send_message(
        "<b>[TC-11]</b> Next call simulates a network timeout...",
        disable_notification=True
    )
    time.sleep(0.5)

    with patch('telegram_utils.requests.post', side_effect=req_lib.exceptions.Timeout("simulated timeout")):
        result = tg.send_message("Should not appear — timeout test")

    ok = result is None
    return ok, "returned None on Timeout without crashing"


run(11, "Network timeout simulation", "requests.post raises Timeout. Code must catch it and return None.", case_11)


# ─────────────────────────────────────────────────────────────────────────────
# CASE 12 — Caption at exactly 1024-char limit (truncation check)
# ─────────────────────────────────────────────────────────────────────────────
def case_12(tg):
    long_title = 'ক' * 900   # very long Bangla title
    notice = {**NOTICE_BASE, 'title': long_title}
    caption = tg.build_notice_caption(notice, 'NEW')
    truncated = caption[:1024]
    result = tg.send_photo(_tiny_png(), caption=truncated)
    ok = result is not None
    return ok, f"caption_len={len(caption)}, truncated_to={len(truncated)}, sent={ok}"


run(12, "Caption truncation at 1024 chars", "Title is 900 Bengali chars. Caption is built then truncated to 1024 before send.", case_12)


# ─────────────────────────────────────────────────────────────────────────────
# CASE 13 — PDF_REPLACED change type
# ─────────────────────────────────────────────────────────────────────────────
def case_13(tg):
    notice = {**NOTICE_BASE, 'title': '[TC-13] PDF replaced — should show PDF Replaced label'}
    result_list, all_sent = tg.send_notice_with_media(
        notice, 'PDF_REPLACED',
        images=[_tiny_png()],
        pdf_bytes=None,
    )
    ok = bool(result_list)
    return ok, f"all_sent={all_sent}"


run(13, "PDF_REPLACED change type", "Caption label should say 'PDF Replaced'.", case_13)


# ─────────────────────────────────────────────────────────────────────────────
# CASE 14 — send_document directly (standalone PDF send)
# ─────────────────────────────────────────────────────────────────────────────
def case_14(tg):
    result = tg.send_document(
        _fake_pdf(),
        filename='test-notice-tc14.pdf',
        caption='<b>[TC-14]</b> Standalone PDF send test',
    )
    ok = result is not None
    return ok, f"message_id={result.get('message_id') if result else None}"


run(14, "Standalone PDF send", "send_document() called directly with a minimal PDF.", case_14)


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

tg = _make_tg()

passed = sum(1 for _, _, ok, _ in results if ok)
failed = sum(1 for _, _, ok, _ in results if not ok)

summary_lines = [f"<b>Test Run Summary — {passed}/{len(results)} passed</b>\n"]
for no, label, ok, detail in results:
    icon = PASS if ok else FAIL
    summary_lines.append(f"{icon} TC-{no:02d}: {label}")
    if not ok:
        summary_lines.append(f"       ↳ {detail}")

tg.send_message("\n".join(summary_lines))

print(f"\n{'='*50}")
print(f"RESULTS: {passed} passed, {failed} failed out of {len(results)}")
for no, label, ok, detail in results:
    print(f"  {'PASS' if ok else 'FAIL'} [{no:02d}] {label}: {detail}")
print('='*50)
