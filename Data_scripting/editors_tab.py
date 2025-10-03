

"""
editors_tab.py

Purpose
-------
Scrape **editor notes** (Description text) from the **Edits** tab.
This is a closures-only flow:
  • Always apply the **Show In Client** filter (key: `presence_period`).
  • Do NOT click the "edited" badge.
  • Match the Edits row by the CSV column **Edit Closure** (same calendar day
    preferred; otherwise choose the closest in time).

Reference
---------
Modeled after `edited_json_notes.py` conventions. Reuses shared helpers &
constants from `BC_hours_and_closures_Edit_Contests.py`.

Input / Output
--------------
- Reads:  `2_BC_Hours_and_Closures_Edit_Contests.csv`
          columns used → "Place Id" and "Edit Closure"
- Writes: `editor_notes_output.csv` with columns:
          place_id, place_name, edit_closure_csv, edit_dt_iso, editor_note

Usage
-----
    python Data_scripting/editors_tab.py
"""

from __future__ import annotations
import csv
import re
import html
import sys
from datetime import datetime
from typing import List, Tuple, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Reuse existing helpers/constants to keep behavior consistent
from BC_hours_and_closures_Edit_Contests import (
    start_driver,
    click_versions_tab,
    choose_field,
    collect_versions,  # not strictly required, but available if needed
    PATH,
    TIMEOUT,
    THRESHOLD,  # not used directly here, but kept for parity
)

# ---- Closures-only configuration
FILTER_KEY = "presence_period"   # Show In Client
INPUT_CSV = "2_BC_Hours_and_Closures_Edit_Contests.csv"
OUTPUT_CSV = "editor_notes_output.csv"
ID_COL = "Place Id"
CLOSURE_COL = "Edit Closure"


# ---------- Page readiness / utilities ----------

def _wait_details_ready(driver):
    """Wait until Versions & Edits tabs are visible (page chrome ready)."""
    WebDriverWait(driver, TIMEOUT).until(
        EC.presence_of_element_located((By.XPATH, "//a[contains(@class,'nav-link') and normalize-space()='Versions']"))
    )
    WebDriverWait(driver, TIMEOUT).until(
        EC.presence_of_element_located((By.XPATH, "//a[contains(@class,'nav-link') and normalize-space()='Edits']"))
    )


def _get_place_name(driver) -> str:
    """Read the POI name from the Name row or header fallbacks."""
    try:
        val = driver.find_elements(By.XPATH, "//div[@title='Name']/following-sibling::div")
        if val:
            t = val[0].text.strip()
            if t:
                return t
    except Exception:
        pass
    for sel in (
        "[data-test-id='place-header__title']",
        "[data-test-id='place__title']",
        "[data-test-id='place-title']",
    ):
        try:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            if els and els[0].text.strip():
                return els[0].text.strip()
        except Exception:
            pass
    return ""


# ---------- Edits tab helpers ----------

def click_edits_tab(driver):
    """Open the Edits tab (same pattern as clicking Versions)."""
    try:
        el = driver.find_element(By.XPATH, "//a[contains(@class,'nav-link') and normalize-space()='Edits']")
    except Exception:
        el = driver.find_element(By.XPATH, "//a[contains(@href,'/edits')]")
    try:
        el.click()
    except Exception:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        driver.execute_script("arguments[0].click();", el)
    WebDriverWait(driver, TIMEOUT).until(
        EC.presence_of_element_located((By.XPATH, "//div[@title='Date'] | //div[@title='Description']"))
    )


def _parse_edit_datetime(txt: str) -> Optional[datetime]:
    """Parse the Edits row Date string into a datetime (lenient)."""
    if not txt:
        return None
    s = re.sub(r"\s+", " ", txt.strip())
    # Drop trailing timezone token
    parts = s.split(" ")
    if parts and parts[-1].isupper() and len(parts[-1]) in (2, 3, 4):
        s = " ".join(parts[:-1])
    fmts = [
        "%Y-%m-%d %I:%M %p",
        "%Y-%m-%d %H:%M",
        "%b %d, %Y %I:%M %p",
        "%b %d, %Y %H:%M",
        "%Y-%m-%d",
    ]
    for f in fmts:
        try:
            return datetime.strptime(s, f)
        except Exception:
            continue
    return None


def collect_edits(driver) -> List[Tuple[datetime, str]]:
    """Return list of (edit_datetime, description_text) from Edits tab."""
    rows = driver.find_elements(By.XPATH, "//div[contains(@class,'audit-row') and .//div[@title='Date']]")
    out: List[Tuple[datetime, str]] = []
    for r in rows:
        try:
            d_el = r.find_element(By.XPATH, ".//div[@title='Date']/following-sibling::div")
            desc_el = r.find_element(By.XPATH, ".//div[@title='Description']/following-sibling::div")
        except Exception:
            continue
        dt = _parse_edit_datetime(d_el.text)
        desc = desc_el.text.strip()
        if dt:
            out.append((dt, desc))
    out.sort(key=lambda t: t[0], reverse=True)  # newest first
    return out


def apply_sic_filter(driver) -> None:
    """Open Versions and apply Show In Client (presence_period) filter."""
    click_versions_tab(driver)
    choose_field(driver, FILTER_KEY)


def _same_calendar_day(a: datetime, b: datetime) -> bool:
    return (a.year, a.month, a.day) == (b.year, b.month, b.day)


def find_matching_edit(edits: List[Tuple[datetime, str]], target_dt: Optional[datetime]) -> Tuple[Optional[datetime], str]:
    """Choose the Edits row for the same calendar day as target_dt; otherwise closest."""
    if not edits:
        return (None, "")
    if target_dt is None:
        return edits[0][0], edits[0][1]
    for dt, desc in edits:
        if _same_calendar_day(dt, target_dt):
            return dt, desc
    # fallback: absolute closest
    best = min(edits, key=lambda t: abs((t[0] - target_dt).total_seconds()))
    return best[0], best[1]


# ---------- Core flow ----------

def scrape_editor_note_via_edits(driver, place_id: str, target_dt: Optional[datetime]):
    # Load details
    driver.get(PATH + str(place_id))
    _wait_details_ready(driver)
    place_name = _get_place_name(driver)

    # Apply Show In Client filter (no badge clicking)
    apply_sic_filter(driver)

    # Switch to Edits and collect entries
    click_edits_tab(driver)
    edits = collect_edits(driver)
    match_dt, note = find_matching_edit(edits, target_dt)

    return {
        "place_id": str(place_id),
        "place_name": place_name,
        "edit_dt_iso": match_dt.isoformat() if match_dt else "",
        "editor_note": note,
    }


# ---------- CLI ----------
if __name__ == "__main__":
    driver = start_driver()
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(
            out_f,
            fieldnames=[
                "place_id",
                "place_name",
                "edit_closure_csv",
                "edit_dt_iso",
                "editor_note",
            ],
        )
        writer.writeheader()

        with open(INPUT_CSV, newline="", encoding="utf-8") as in_f:
            reader = csv.DictReader(in_f)
            reader.fieldnames = [fn.lstrip("\ufeff").strip() for fn in reader.fieldnames]
            for row in reader:
                # Clean Place Id
                pid_raw = (row.get(ID_COL, "") or "").strip()
                pid_unescaped = html.unescape(pid_raw)
                pid_no_tags = re.sub(r"<[^>]*>", "", pid_unescaped)
                m = re.search(r"\d+", pid_no_tags)
                pid = m.group(0) if m else ""
                if not pid:
                    print("❗ Missing Place Id; skipping.")
                    continue

                # Parse target Edit Closure date (lenient)
                raw_closure = (row.get(CLOSURE_COL, "") or "").strip()
                target_dt = None
                if raw_closure:
                    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%d %H:%M", "%m/%d/%Y %I:%M %p", "%b %d, %Y"):
                        try:
                            target_dt = datetime.strptime(raw_closure, fmt)
                            break
                        except Exception:
                            continue

                try:
                    rec = scrape_editor_note_via_edits(driver, pid, target_dt)
                except Exception as e:
                    print(f"❌ Error for {pid}: {e}")
                    rec = {
                        "place_id": str(pid),
                        "place_name": "",
                        "edit_dt_iso": "",
                        "editor_note": "",
                    }
                # add original CSV date to output row
                rec["edit_closure_csv"] = raw_closure
                print(f"→ {rec}")
                writer.writerow(rec)

    driver.quit()
    print("✅ Done (Edits tab notes).")