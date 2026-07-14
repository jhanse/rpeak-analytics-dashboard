#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the bundled R-PEAK data payload from public/rpeak_tasks_2026.csv.

The dashboard UI now lives in public/index.html and public/app.js. Keep those files
editable and only regenerate public/data.js from the current CSV export.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
CSV_PATH = PUBLIC / "rpeak_tasks_2026.csv"
DATA_PATH = PUBLIC / "data.js"

with CSV_PATH.open(newline="", encoding="utf-8-sig") as f:
    rows = [{k: (v if v is not None else "") for k, v in r.items()} for r in csv.DictReader(f)]

payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
DATA_PATH.write_text(f"window.RPEAK_ROWS = {payload};\n", encoding="utf-8")

print(f"Built {DATA_PATH.relative_to(ROOT)} with {len(rows)} rows")
