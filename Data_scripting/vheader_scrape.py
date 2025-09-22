

"""
Standalone: scrape Version Header prior to 2025-07-25 and output alongside
'Place ID' and 'Place Details Link'.

Usage:
    python3 vheader_scrape.py [--field hours|show] input.csv output.csv

If no args:
    input  -> BC_Hours_and_Closures_Edit_Contests.csv
    output -> vheader_output.csv
Field filter (optional):
    --field hours  → applies the Versions filter for Hours (hours_period)
    --field show   → applies the Versions filter for Show In Client (presence_period)
"""

import csv
import sys
import re
import traceback
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import (
    SessionNotCreatedException,
    WebDriverException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ---- Constants
TIMEOUT = 30
PATH = "https://apollo.geo.apple.com/p/release/"
THRESHOLD = datetime(2025, 7, 25)

# ---- Console colors
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
MAGENTA = "\033[95m"
RESET = "\033[0m"


def _dbg(msg: str) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{MAGENTA}[{ts}] {msg}{RESET}")


def _dbe(msg: str, e: Exception | None = None) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    if e is None:
        print(f"{RED}[{ts}] {msg}{RESET}")
    else:
        et = type(e).__name__
        print(f"{RED}[{ts}] {msg} | {et}: {e}{RESET}")


# =============================================================================
# Driver bootstrap
# =============================================================================

def start_driver():
    try:
        print("Initializing Safari webdriver...")
        driver = webdriver.Safari()
    except SessionNotCreatedException as ex:
        message = str(ex)
        if "Allow Remote Automation" in message:
            print(
                f"{RED}\tERROR: Must Allow Remote Automation. (Safari > Develop > Allow Remote Automation)\n{RESET}"
            )
        elif "already paired" in message:
            print(f"{RED}\tERROR: Must stop previous session to start new.\n{RESET}")
        else:
            print(
                f"{RED}\tERROR: SessionNotCreatedException. Report:\n{message}{RESET}"
            )
        traceback.print_exc()
        sys.exit(1)
    except WebDriverException as ex:
        try:
            print("Attempting to stop safaridriver service...")
            webdriver.Safari().service.stop()
            print("safaridriver service stopped.")
            driver = webdriver.Safari()
        except Exception:
            print(f"{RED}WebDriverException: {ex}{RESET}")
            sys.exit(1)
    except Exception as ex:
        print(f"{RED}Unexpected driver error: {type(ex).__name__}: {ex}{RESET}")
        traceback.print_exc()
        sys.exit(1)
    driver.set_window_rect(5, 30, 1440, 980)
    return driver


# =============================================================================
# Page helpers
# =============================================================================

def click_versions_tab(driver):
    WebDriverWait(driver, TIMEOUT).until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//a[contains(@class,'nav-link') and normalize-space()='Versions']",
            )
        )
    ).click()


def wait_versions_ui(driver):
    WebDriverWait(driver, TIMEOUT).until(
        lambda d: d.find_elements(By.CSS_SELECTOR, "a[id^='entry-']")
        or d.find_elements(By.CSS_SELECTOR, ".choices__inner, .choices")
    )


def ensure_versions_open(driver):
    try:
        active = driver.find_elements(
            By.XPATH,
            "//a[contains(@class,'nav-link') and contains(@class,'active') and normalize-space()='Versions']",
        )
        if active:
            wait_versions_ui(driver)
            return
    except Exception:
        pass
    click_versions_tab(driver)
    try:
        wait_versions_ui(driver)
    except Exception:
        pass


# =============================================================================
# Field filter helper
# =============================================================================

def choose_field(driver, filter_key: str) -> bool:
    """
    Apply the Versions subview filter (Choices.js) by its data-value.
    Accepts:
        'hours_period'     (Hours)
        'presence_period'  (Show In Client / Closures)
    Returns True if applied, False if control is not clickable (non-fatal).
    """
    dropdown_trigger_xpath = "//div[contains(@class,'choices__item--selectable') and @data-value='none']"
    try:
        WebDriverWait(driver, TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, dropdown_trigger_xpath))
        ).click()
    except TimeoutException:
        print(f"{YELLOW}[filter] Trigger not clickable; continuing without filter{RESET}")
        return False

    try:
        opt_xpath = f"//div[contains(@class,'choices__item') and @data-value='{filter_key}']"
        WebDriverWait(driver, TIMEOUT).until(
            EC.element_to_be_clickable((By.XPATH, opt_xpath))
        ).click()
        print(f"{GREEN}[filter] Selected {filter_key}{RESET}")
        return True
    except TimeoutException:
        print(f"{YELLOW}[filter] Option {filter_key} not found/clickable; continuing without filter{RESET}")
        return False


def collect_versions(driver):
    """Return list of (datetime, entry_id), sorted ascending (oldest → newest)."""
    try:
        WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[id^='entry-']"))
        )
    except TimeoutException:
        return []
    raw = driver.find_elements(By.CSS_SELECTOR, "a[id^='entry-']")
    out = []
    for e in raw:
        try:
            txt = e.find_element(By.TAG_NAME, "span").text  # "YYYY-MM-DD 01:23 PM CDT"
            dt = datetime.strptime(txt.rsplit(" ", 1)[0], "%Y-%m-%d %I:%M %p")
            out.append((dt, e.get_attribute("id")))
        except Exception:
            continue
    return sorted(out, key=lambda x: x[0])


def click_version(driver, entry_id):
    WebDriverWait(driver, TIMEOUT).until(
        EC.element_to_be_clickable((By.ID, entry_id))
    ).click()
    # Wait for common fields to render
    WebDriverWait(driver, TIMEOUT).until(
        EC.presence_of_element_located((By.XPATH, "//div[@title='Hours']"))
    )


# =============================================================================
# Extraction
# =============================================================================

def extract_brand_applier_vheader(driver):
    """Return relevant header texts from the selected version row."""
    try:
        selected_row = WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "tr.selected-row"))
        )
        tds = selected_row.find_elements(By.CSS_SELECTOR, "td.collapsed-column")
        header_texts: list[str] = []
        for td in tds:
            if td.find_elements(By.TAG_NAME, "input"):
                continue
            text = td.text.strip()
            if text:
                header_texts.append(text)
        filtered = [
            t
            for t in header_texts
            if not any(s in t for s in ["AM", "PM", "CDT", "UTC", "GMT"])
            and not t.replace(".", "").replace("-", "").replace("(", "").replace(")", "").replace(" ", "").isdigit()
        ]
        return filtered
    except Exception:
        return []


def select_prior_or_earliest(versions):
    if not versions:
        return None
    chosen = None
    for dt, vid in versions:
        if dt < THRESHOLD:
            chosen = (dt, vid)
    if chosen is None:
        chosen = versions[0]
    return chosen


def scrape_vheader_for_row(driver, place_details_link: str | None, place_id: str | None, filter_key: str | None = None) -> str:
    # 1) Navigate by link (preferred) or place_id
    if place_details_link and place_details_link.strip():
        driver.get(place_details_link.strip())
    elif place_id and place_id.strip():
        driver.get(PATH + place_id.strip())
    else:
        return ""

    # 2) Open Versions, then apply filter (order is important)
    click_versions_tab(driver)
    try:
        wait_versions_ui(driver)
    except Exception:
        pass
    
    if filter_key:
        _dbg(f"applying filter_key after Versions: {filter_key}")
        try:
            if not choose_field(driver, filter_key):
                print(f"{YELLOW}[filter] continuing without filter{RESET}")
        except Exception as e:
            _dbe(f"filter apply failed for key={filter_key}", e)
    
    versions = collect_versions(driver)

    if not versions:
        return ""
    chosen = select_prior_or_earliest(versions)
    if not chosen:
        return ""
    _, entry_id = chosen
    click_version(driver, entry_id)

    # 3) Extract Version Header
    vheader = extract_brand_applier_vheader(driver)
    return " | ".join(vheader) if isinstance(vheader, list) else (vheader or "")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    in_csv = sys.argv[1] if len(sys.argv) > 1 else "BC_Hours_and_Closures_Edit_Contests.csv"
    out_csv = sys.argv[2] if len(sys.argv) > 2 else "vheader_output.csv"

    # Optional field filter via --field hours|show
    field_arg = None
    for i, a in enumerate(list(sys.argv[1:])):
        if a == "--field" and (1 + i) < len(sys.argv[1:]):
            val = sys.argv[1:][i + 1].strip().lower()
            if val in ("hours", "show"):
                field_arg = "hours_period" if val == "hours" else "presence_period"
            break

    driver = start_driver()
    try:
        with open(out_csv, "w", newline="", encoding="utf-8") as out_f:
            writer = csv.DictWriter(
                out_f,
                fieldnames=[
                    "Place ID",
                    "Place Details Link",
                    "What Applied Brand (Version Header)",
                ],
            )
            writer.writeheader()

            with open(in_csv, newline="", encoding="utf-8") as in_f:
                reader = csv.DictReader(in_f)
                # normalize headers
                reader.fieldnames = [fn.lstrip("\ufeff").strip() for fn in reader.fieldnames]
                for row in reader:
                    pid = (row.get("Place ID", "") or "").strip()
                    link = (row.get("Place Details Link", "") or "").strip()

                    try:
                        vheader = scrape_vheader_for_row(driver, link, pid, field_arg)
                    except Exception as e:
                        _dbe(f"row error (Place ID={pid!r})", e)
                        vheader = ""

                    writer.writerow(
                        {
                            "Place ID": pid,
                            "Place Details Link": link,
                            "What Applied Brand (Version Header)": vheader,
                        }
                    )
        print(f"{GREEN}✔ VHeader scrape complete → {out_csv}{RESET}")
    finally:
        driver.quit()