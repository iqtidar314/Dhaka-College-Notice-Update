$env:PYTHONIOENCODING="utf-8"; 
python test_telegram_scenarios.py
01	Happy path — 1 image	✅
02	Happy path — 3-image album	✅
03	No images → PDF fallback	✅
04	Image fails → PDF fallback	✅
05	Image + PDF fail → URL + footer	✅
06	Image + PDF fail, no URL → text + footer	✅
07	EDITED notice	✅
08	REMOVED_FROM_PAGE_1 — 🚫 styled	✅
09	DELETED label edit — 🗑 styled	✅
10	API error (bad token) — graceful	✅
11	Network timeout — graceful	✅
12	900-char Bengali title — safely truncated	✅
13	PDF_REPLACED change type	✅
14	Standalone PDF send	✅