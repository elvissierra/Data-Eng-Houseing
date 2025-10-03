"""
edited_json_notes.py  (aka BC_rca_notes_only.py)

GOAL:
    A focused utility that ONLY collects the "notes" text from the JSON page
    behind an **edited Show In Client** badge in the Versions view.

WHEN TO USE:
    - Your main pipeline already gets present/edited badges + ToDos, but
      you now need the **RCA notes** (the "notes" field in the JSON edit details)
      for the **Show In Client (SIC)** contested field.
    - This script intentionally ignores non-SIC rows to keep it simple & fast.

INPUT / OUTPUT:
    - Reads Place IDs from:  Data_scripting/BC_Hours_and_Closures_Edit_Contests.csv
      (expects a "Place ID" column and optionally "Contested Field"/"Contested Field Column")
    - Writes: rca_notes_output.csv with columns:
        * place_id
        * place_name
        * rca_note

ASSUMPTIONS:
    - BC_hours_and_closures_Edit_Contests.py exists in the same folder and exposes:
        start_driver, click_versions_tab, choose_field, collect_versions, click_version,
        PATH, TIMEOUT, THRESHOLD

IMPORTANT:
    - This script defaults to **Show In Client (SIC)** but can run for **Hours** by passing --mode hours.
      Internally it maps to the filter keys `presence_period` (SIC) and `hours_period` (Hours).
"""

import csv
import re
import html
import time
import sys
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# ---- Mode configuration
# Default mode is "sic"; pass --mode hours to scrape Hours instead
MODE = "sic"  # "hours" | "sic"
MODE_CONFIG = {
    "hours": {"filter_key": "hours_period", "panel_label": "Hours"},
    "sic": {"filter_key": "presence_period", "panel_label": "Show In Client"},
}

# Reuse your existing helpers & constants from the main hours/closures script.
# This keeps browser setup and DOM conventions in a single place.
from BC_hours_and_closures_Edit_Contests import (
    start_driver,
    click_versions_tab,
    choose_field,
    collect_versions,
    click_version,
    PATH,
    TIMEOUT,
    THRESHOLD,
)

# ---- I/O paths for this focused utility
INPUT_CSV = "2_BC_Hours_and_Closures_Edit_Contests.csv"
OUTPUT_CSV = "2_BC_output.csv"


def _wait_versions_ready(driver):
    """
    Tiny guard to ensure the details page finished loading basic chrome
    before we click 'Versions'.
    """
    WebDriverWait(driver, TIMEOUT).until(
        EC.presence_of_element_located(
            (By.XPATH, "//a[contains(@class,'nav-link') and normalize-space()='Versions']")
        )
    )


def _wait_name_ready(driver):
    """Wait for the Name row (preferred) or fallback to Hours as page-ready signal."""
    try:
        WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, "//div[@title='Name']"))
        )
    except TimeoutException:
        try:
            WebDriverWait(driver, TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, "//div[@title='Hours']"))
            )
        except TimeoutException:
            pass


def _get_place_name(driver) -> str:
    """Best-effort extraction of the POI's display name.

    Priority order:
      1) Details row value next to the label div[@title='Name']
      2) Common header/title fallbacks
    """
    try:
        # Canonical value cell(s) after the Name label
        value_containers = driver.find_elements(By.XPATH, "//div[@title='Name']/following-sibling::div")
        if value_containers:
            spans = value_containers[0].find_elements(By.XPATH, ".//span[normalize-space()]")
            if spans:
                txt = spans[0].text.strip()
                if txt:
                    return txt
            raw = value_containers[0].text.strip()
            if raw:
                return raw
        # Header/title heuristics
        for sel in (
            "[data-test-id='place-header__title']",
            "[data-test-id='place__title']",
            "[data-test-id='place-title']",
        ):
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            if els and els[0].text.strip():
                return els[0].text.strip()
        for xp in (
            "//header//h1",
            "//header//h2",
            "//div[contains(@class,'place-header')]//h1",
            "//div[contains(@class,'place-header')]//h2",
        ):
            els = driver.find_elements(By.XPATH, xp)
            for e in els:
                t = e.text.strip()
                if t:
                    return t
        for h in driver.find_elements(By.TAG_NAME, "h1"):
            t = h.text.strip()
            if t:
                return t
    except Exception:
        pass
    return ""


def _open_json_from_panel(driver, title_text: str) -> bool:
    """
    STRICT panel opener:
      - Find the field panel by @title (e.g., 'Show In Client')
      - Ensure its badge text explicitly starts with 'edited'
      - Click the link wrapping the badge (opens JSON details)
    Returns True if navigation happened (new tab or same tab), else False.

    NOTE: We **only** call this with title_text='Show In Client' in this script.
    """
    # Locate the label cell (left) and the value/badge panel (right)
    try:
        label = WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, f"//div[@title='{title_text}']"))
        )
        panel = label.find_element(By.XPATH, "following-sibling::div")
    except Exception:
        return False

    # Confirm the badge explicitly reads "edited"
    try:
        edited_badge = panel.find_element(By.CSS_SELECTOR, ".audit-badge")
        if not edited_badge or not edited_badge.text or not edited_badge.text.strip().lower().startswith("edit"):
            # Badge exists but isn't an 'edited' state → don't click
            return False
    except NoSuchElementException:
        return False

    # Prefer a link that directly points to an '/edits/' URL; otherwise, click
    # the closest wrapping <a> for the badge.
    link = None
    try:
        links = panel.find_elements(By.CSS_SELECTOR, "a[href*='/edits/']")
        if links:
            link = links[0]
        else:
            link = panel.find_element(
                By.XPATH,
                ".//span[contains(@class,'audit-badge') and "
                "contains(translate(.,'EDITED','edited'),'edited')]/ancestor::a[1]",
            )
    except Exception:
        return False

    # Click (supports either same-tab navigation or a new-tab pop)
    try:
        link.click()
    except Exception:
        try:
            driver.execute_script("arguments[0].scrollIntoView({block:'center'});", link)
            driver.execute_script("arguments[0].click();", link)
        except Exception:
            return False

    return True


def _scrape_notes_from_json(driver) -> str:
    """
    After the edited link is clicked:
      - Either a new tab appears or we navigate in-place to a pretty-printed JSON page.
      - We PREFER parsing the raw JSON text and reading obj['notes'].
      - Fallbacks:
          1) DOM path for the 'notes' attribute
          2) Longest visible string on the page

    Returns the cleaned notes string (or "" if unavailable).
    """
    original = driver.current_window_handle
    pre_url = driver.current_url

    # Detect new-tab vs same-tab navigation
    json_handle = None
    try:
        WebDriverWait(driver, 3).until(EC.new_window_is_opened([original]))
        for h in driver.window_handles:
            if h != original:
                json_handle = h
                break
        if json_handle:
            driver.switch_to.window(json_handle)
    except Exception:
        # same-tab fallback
        try:
            WebDriverWait(driver, TIMEOUT).until(EC.url_changes(pre_url))
        except Exception:
            pass

    # Wait for highlighted JSON container to appear (best-effort)
    try:
        WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//pre[contains(@class,'highlight-js')] | //code[contains(@class,'json')] | //pre",
                )
            )
        )
    except TimeoutException:
        # We'll still try best-effort scraping below
        pass

    def _close_and_return():
        """Close the JSON tab or go back to the version page."""
        try:
            if json_handle:
                driver.close()
                driver.switch_to.window(original)
            else:
                driver.back()
        except Exception:
            pass

    # --- Preferred path: parse the raw JSON text and read 'notes' key ---
    try:
        # Collect text from typical pretty-print containers
        containers = driver.find_elements(By.CSS_SELECTOR, "pre.highlight-js, code.json, pre")
        raw_text = ""
        for c in containers:
            try:
                t = c.text
                if t and t.count("{") >= 1 and t.count("}") >= 1:
                    raw_text = t
                    break
            except Exception:
                continue

        if raw_text:
            # Extract the largest { ... } block (covers extra prelude/epilogue text)
            start = raw_text.find("{")
            end = raw_text.rfind("}")
            if start != -1 and end != -1 and end > start:
                json_block = raw_text[start:end + 1]
                import json as _json
                try:
                    obj = _json.loads(json_block)
                except Exception:
                    # Handle common pretty-print hiccups (e.g., trailing commas)
                    cleaned = re.sub(r",(\s*[}\]])", r"\1", json_block)
                    obj = _json.loads(cleaned)
                notes_val = obj.get("notes", "")
                if isinstance(notes_val, str) and notes_val.strip():
                    notes_val = re.sub(r"\s+", " ", notes_val).strip()
                    _close_and_return()
                    return notes_val
    except Exception:
        # Fall through to DOM-based extraction
        pass

    # --- Fallback 1: DOM path for the 'notes' attribute ---
    try:
        notes_node = driver.find_element(
            By.XPATH,
            "//span[contains(@class,'attribute') and normalize-space()='notes']"
            "/following-sibling::span[contains(@class,'value')]//span[contains(@class,'string')]",
        )
        txt = notes_node.text.strip().strip('"')
        if txt:
            txt = re.sub(r"\s+", " ", txt).strip()
            _close_and_return()
            return txt
    except Exception:
        pass

    # --- Fallback 2: longest visible JSON string literal on page ---
    try:
        strings = driver.find_elements(By.CSS_SELECTOR, ".highlight-js .string, code.json .string, pre .string")
        texts = [s.text.strip().strip('"') for s in strings if s.text.strip()]
        best = max(texts, key=len) if texts else ""
        best = re.sub(r"\s+", " ", best).strip() if best else ""
    except Exception:
        best = ""

    _close_and_return()
    return best


def scrape_rca_note_for_place(driver, place_id: str, contested_field: str = "Show In Client"):
    """
    Single-POI flow (STRICTLY for Show In Client):
        1) Load details page
        2) Click 'Versions'
        3) Filter = presence_period
        4) Pick latest version strictly prior to THRESHOLD (fallback earliest)
        5) Click the 'edited' link in the Show In Client row
        6) Read and return the 'notes' value from the JSON

    Returns:
        dict | None:
            {"place_id": <id>, "rca_note": <text>}  when processed
            None                                    when skipped (not SIC)
    """
    # Guard: we only run for Hours
    #if (contested_field or "").strip().lower() != "hours":
    #    return None

    # Details
    driver.get(PATH + place_id)
    _wait_versions_ready(driver)

    # Ensure Name is present and capture it before leaving the details view
    _wait_name_ready(driver)
    place_name = _get_place_name(driver)

    # Versions → apply filter based on mode
    click_versions_tab(driver)
    cfg = MODE_CONFIG.get(MODE, MODE_CONFIG["hours"])
    key = cfg["filter_key"]
    choose_field(driver, key)  # If this fails, we continue; versions may still be relevant

    # Collect versions, pick one before threshold (else earliest)
    versions = collect_versions(driver)
    if not versions:
        return {"place_id": place_id, "place_name": place_name, "rca_note": ""}

    chosen = None
    for dt, vid in versions:
        if dt < THRESHOLD:
            chosen = (dt, vid)
    if chosen is None:
        chosen = versions[0]

    _, vid = chosen
    click_version(driver, vid)

    # Strict: only click the edited badge in the selected field row
    panel_label = cfg["panel_label"]
    if not _open_json_from_panel(driver, panel_label):
        return {"place_id": place_id, "place_name": place_name, "rca_note": ""}

    note = _scrape_notes_from_json(driver)
    return {"place_id": place_id, "place_name": place_name, "rca_note": note}


if __name__ == "__main__":
    # Optional: select field mode from CLI ("hours" or "sic")
    for i, arg in enumerate(list(sys.argv)):
        if arg == "--mode" and len(sys.argv) > i + 1:
            val = (sys.argv[i + 1] or "").strip().lower()
            if val in MODE_CONFIG:
                MODE = val
    driver = start_driver()

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=["place_id", "place_name", "rca_note"])
        writer.writeheader()

        with open(INPUT_CSV, newline="", encoding="utf-8") as in_f:
            reader = csv.DictReader(in_f)
            # Normalize BOM + whitespace in headers
            reader.fieldnames = [fn.lstrip("\ufeff").strip() for fn in reader.fieldnames]
            for row in reader:
                # ---- Robust Place ID cleanup (handles "<br>" and HTML entities)
                pid_raw = (row.get("Place Id", "") or "").strip()
                pid_unescaped = html.unescape(pid_raw)               # "&lt;br&gt;123" → "<br>123"
                pid_no_tags = re.sub(r"<[^>]*>", "", pid_unescaped)  # "<br>123" → "123"
                m = re.search(r"\d+", pid_no_tags)
                pid = m.group(0) if m else ""
                if not pid:
                    print("❗ Missing Place ID; skipping.")
                    continue

                # Use the sheet value if present; we only act on "Hours".
                #contested_field = (row.get("Contested Field", "") or row.get("Contested Field Column", "") or "").strip()
                #if contested_field.lower() != "hours":
                #    print(f"↷ Skipping {pid}: contested_field is '{contested_field}' (not Hours)")
                #    continue

                # Process one POI
                try:
                    rec = scrape_rca_note_for_place(driver, pid)
                except Exception as e:
                    print(f"❌ Error for {pid}: {e}")
                    rec = None

                if rec is None:
                    # Early exit case (shouldn't hit because of the guard above)
                    continue

                print(f"→ {rec}")
                writer.writerow(rec)

    driver.quit()
    print("✅ Done.")