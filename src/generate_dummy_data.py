#!/usr/bin/env python3
"""Generate a public-safe synthetic R-PEAK task dataset.

The dummy dataset preserves broad dashboard characteristics (project count,
status/type/workflow/task-volume/timing patterns) without retaining real project
codes, free-text comments, or site-specific identifiers.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
DEFAULT_SOURCE_PATH = ROOT / "private_data" / "rpeak_tasks_source.csv"
TEMPLATE_PATH = PUBLIC / "workflow_template.csv"
OUT_CSV = PUBLIC / "rpeak_tasks_2026.csv"
OUT_JS = PUBLIC / "data.js"

RNG = random.Random(304654)
HEADERS = [
    "Project Code", "Project Status", "Study Type", "Workflow", "Task Name",
    "Task Comment", "Target Days to Complete", "Date Site Selected",
    "Date HRA approval", "Date Created", "Start Date", "Due Date",
    "Completion Date", "On time or Late", "Days to completion",
    "Days active (if not complete)", "Task Status",
]

STATUS_MIX = {
    "Open": 47,
    "Pending": 30,
    "In set up": 4,
    "Follow up": 5,
    "Suspended": 3,
    "Complete": 1,
}

GENERIC_COMMENTS = {
    "Complete": "Synthetic completed task for demonstration data.",
    "Active": "Synthetic active task; completion date intentionally unavailable.",
    "Pending": "Synthetic pending task awaiting next workflow action.",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def excel_serial(d: date | None) -> str:
    if d is None:
        return ""
    return str((d - date(1899, 12, 30)).days)


def parse_excel(v: str) -> date | None:
    try:
        n = int(float(v))
    except Exception:
        return None
    if n <= 20000:
        return None
    return date(1899, 12, 30) + timedelta(days=n)


def weighted_choice(counter: Counter[str]) -> str:
    items = [(k.strip(), v) for k, v in counter.items() if k and k.strip() and v > 0]
    total = sum(v for _, v in items)
    pick = RNG.uniform(0, total)
    acc = 0.0
    for k, v in items:
        acc += v
        if pick <= acc:
            return k
    return items[-1][0]


def clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))


def nearest_template_tasks(template: list[dict[str, str]], workflow: str, count: int) -> list[dict[str, str]]:
    wf_tasks = [t for t in template if t.get("workflow") == workflow]
    if not wf_tasks:
        wf_tasks = template[:]
    wf_tasks = sorted(wf_tasks, key=lambda t: int(float(t.get("order") or 999)))
    if count <= len(wf_tasks):
        return wf_tasks[:count]
    out = wf_tasks[:]
    while len(out) < count:
        base = RNG.choice(wf_tasks)
        extra = dict(base)
        extra["task"] = f"Follow-up: {base.get('task','Workflow task')}"
        extra["order"] = str(len(out) + 1)
        out.append(extra)
    return out


def sample_project_sizes(real_rows: list[dict[str, str]]) -> list[int]:
    by_project: dict[str, int] = defaultdict(int)
    for r in real_rows:
        by_project[r["Project Code"]] += 1
    sizes = list(by_project.values())
    # Similar task-volume distribution, capped to keep the public demo light.
    return [clamp(int(round(RNG.choice(sizes) * RNG.uniform(0.75, 1.1))), 8, 55) for _ in range(90)]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate public-safe synthetic R-PEAK demo data")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE_PATH), help="Private source export used only for aggregate distributions")
    args = parser.parse_args()
    real = read_csv(Path(args.source))
    template = read_csv(TEMPLATE_PATH)
    study_counter = Counter(r["Study Type"].strip() for r in real)
    workflow_counter = Counter(r["Workflow"].strip() for r in real)
    sizes = sample_project_sizes(real)

    statuses = []
    for status, n in STATUS_MIX.items():
        statuses.extend([status] * n)
    RNG.shuffle(statuses)

    rows: list[dict[str, str]] = []
    today = date(2026, 7, 14)
    start_window = date(2024, 4, 1)

    for idx in range(90):
        code = f"D{idx+1:04d}"
        project_status = statuses[idx]
        study_type = weighted_choice(study_counter)
        workflow = weighted_choice(workflow_counter)
        n_tasks = sizes[idx]
        tasks = nearest_template_tasks(template, workflow, n_tasks)

        project_start = start_window + timedelta(days=RNG.randint(0, 760))
        site_selected = project_start + timedelta(days=RNG.randint(-14, 21))
        hra = project_start + timedelta(days=RNG.randint(-35, 28))
        setup_start = max(site_selected, hra)

        # Mimic target interval distribution: many around 30-70d, some much longer.
        if project_status in {"Pending", "In set up"}:
            cc_days = RNG.choice([RNG.randint(35, 80), RNG.randint(80, 180), None])
        else:
            cc_days = clamp(int(RNG.gauss(54, 32)), 0, 210)
        green_delay = None if cc_days is None else RNG.randint(0, 35)
        first_patient_delay = None if green_delay is None else max(0, int(RNG.gauss(29, 22)))

        capacity_done = setup_start + timedelta(days=cc_days) if cc_days is not None else None
        green_done = capacity_done + timedelta(days=green_delay) if capacity_done and RNG.random() < 0.55 else None
        first_done = green_done + timedelta(days=first_patient_delay) if green_done and RNG.random() < 0.45 else None

        for j, t in enumerate(tasks):
            order = int(float(t.get("order") or j + 1))
            task_name = t.get("task") or f"Workflow task {order}"
            task_l = task_name.lower()
            target = t.get("targetDays") or ""
            created = setup_start + timedelta(days=max(0, order - 1) + RNG.randint(0, 12))
            start = created + timedelta(days=RNG.randint(0, 3))

            completion: date | None
            if "capacity and capability" in task_l and "send c+c" not in task_l:
                completion = capacity_done
            elif "green light" in task_l:
                completion = green_done
            elif "1st patient" in task_l or "first patient" in task_l:
                completion = first_done
            else:
                if project_status in {"Pending", "In set up"}:
                    p_complete = 0.62 if order < n_tasks * 0.55 else 0.34
                elif project_status == "Open":
                    p_complete = 0.86
                elif project_status == "Complete":
                    p_complete = 0.98
                else:
                    p_complete = 0.72
                completion = start + timedelta(days=clamp(int(RNG.expovariate(1 / 11)), 0, 130)) if RNG.random() < p_complete else None

            if completion and completion > today:
                completion = None

            if completion:
                task_status = "Complete"
                days_complete = max(0, (completion - start).days)
                days_active = ""
                timing = "On Time" if (not target or days_complete <= int(float(target or 9999))) else "Late"
                due = start + timedelta(days=int(float(target or 14))) if target else None
            else:
                task_status = "Pending" if project_status == "Pending" and RNG.random() < 0.7 else "Active"
                days_complete = ""
                days_active_n = max(0, (today - start).days)
                days_active = str(days_active_n)
                timing = ""
                due = start + timedelta(days=int(float(target or 14))) if target else None

            rows.append({
                "Project Code": code,
                "Project Status": project_status,
                "Study Type": study_type,
                "Workflow": workflow,
                "Task Name": task_name,
                "Task Comment": GENERIC_COMMENTS[task_status],
                "Target Days to Complete": str(target),
                "Date Site Selected": excel_serial(site_selected),
                "Date HRA approval": excel_serial(hra),
                "Date Created": excel_serial(created),
                "Start Date": excel_serial(start),
                "Due Date": excel_serial(due),
                "Completion Date": excel_serial(completion),
                "On time or Late": timing,
                "Days to completion": str(days_complete),
                "Days active (if not complete)": days_active,
                "Task Status": task_status,
            })

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADERS)
        w.writeheader()
        w.writerows(rows)
    payload = json.dumps(rows, ensure_ascii=False, separators=(",", ":"))
    OUT_JS.write_text(f"window.RPEAK_ROWS = {payload};\n", encoding="utf-8")
    print(f"Generated {len(rows)} synthetic rows across 90 projects")


if __name__ == "__main__":
    main()
