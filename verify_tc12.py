"""Quick verification that TC-12 (caption truncation) now passes."""
import os, re as _re

_env_path = '.env'
if os.path.exists(_env_path):
    with open(_env_path, encoding='utf-8') as f:
        for line in f:
            m = _re.match(r'\$env:(\w+)\s*=\s*["\']?([^"\']+)["\']?', line.strip())
            if m:
                os.environ.setdefault(m.group(1), m.group(2).strip())

from telegram_utils import TelegramUtils
import struct, zlib

def tiny_png():
    def chunk(name, data):
        c = name + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xFFFFFFFF)
    sig  = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
    raw  = b'\x00\xff\x00\x00'
    idat = chunk(b'IDAT', zlib.compress(raw))
    iend = chunk(b'IEND', b'')
    return sig + ihdr + idat + iend

tg     = TelegramUtils()
notice = {'title': 'ক' * 900, 'download_url': ''}
caption = tg.build_notice_caption(notice, 'NEW')

print(f"Caption length: {len(caption)} chars (must be <= 1024)")
assert len(caption) <= 1024, f"FAIL: caption is {len(caption)} chars!"

result = tg.send_photo(tiny_png(), caption=caption)
ok = result is not None
print("Photo sent:", result.get('message_id') if result else "FAILED")
print("TC-12:", "PASS" if ok else "FAIL")
