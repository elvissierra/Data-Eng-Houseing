"""
Scraping from the POI/Gemini Tab
    PATH=https://apollo.geo.apple.com/p/release/
    Show In Client / Closed
    Vendors
    Modern Category
    URLs

"""

import csv
import sys
import json
import re
import time
import traceback
from datetime import datetime
from selenium import webdriver
from selenium.common.exceptions import SessionNotCreatedException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import html

# ---- Console colors for easy scanning in Terminal output
RED = "\033[91m"    # errors
GREEN = "\033[92m"  # notes
YELLOW = "\033[93m" # warnings / non-fatal issues
MAGENTA = "\033[95m"# debug or step markers
RESET = "\033[0m"

# ---- Minimal loggers for debug and error output
def _dbg(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{MAGENTA}[{ts}] {msg}{RESET}")

def _dbe(msg, e=None):
    ts = datetime.now().strftime("%H:%M:%S")
    if e is None:
        print(f"{RED}[{ts}] {msg}{RESET}")
    else:
        et = type(e).__name__
        print(f"{RED}[{ts}] {msg} | {et}: {e}{RESET}")


# ---- Paths & constants
PATH = "https://apollo.geo.apple.com/p/release/"
INPUT_CSV = "csv_files/Jacaranda - Family Services Review - Data.csv"
OUTPUT_CSV = "csv_files/Jacaranda.csv"

TIMEOUT = 30

# ---------------- Gemini helpers ----------------
def ensure_gemini_open(driver):
    """
    Idempotently open the 'Gemini' tab on the details page.
    Waits until the Gemini shell renders (we detect either the 'Vendor Contributions'
    title, or any Gemini section header such as 'URL' or 'Modern Category').
    """
    try:
        # If already on Gemini, do nothing
        active = driver.find_elements(
            By.XPATH,
            "//a[contains(@class,'nav-link') and contains(@class,'active') and normalize-space()='Gemini']",
        )
        if not active:
            WebDriverWait(driver, TIMEOUT).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//a[contains(@class,'nav-link') and normalize-space()='Gemini']")
                )
            ).click()
        # Wait for a Gemini section to exist
        WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@title='Vendor Contributions' or @title='URL' or @title='Show In Client' or @title='Modern Category']")
            )
        )
    except Exception as e:
        _dbe("Failed to open Gemini tab", e)
        raise

def _panel_after_title(driver, title_text: str):
    """
    Given a section title div[@title='<title_text>'], return its trailing panel node.
    Returns None if not found.
    """
    try:
        label = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, f"//div[@title='{title_text}']"))
        )
        return label.find_element(By.XPATH, "following-sibling::div")
    except Exception:
        return None

def scrape_show_in_client(driver) -> str:
    """
    Read the current Show In Client value, e.g., 'Yes (Open)' or 'No (Closed)'.
    """
    panel = _panel_after_title(driver, "Show In Client")
    if not panel:
        return ""
    # Prefer any visible value container under the panel
    try:
        val = panel.find_element(By.XPATH, ".//div[contains(@class,'col-value')]").text.strip()
        return " ".join(val.split())
    except NoSuchElementException:
        return ""

def scrape_modern_category(driver) -> str:
    """
    Collect modern categories shown in Gemini as a comma-separated list.
    Uses any visible muted span text if available; falls back to link text.
    """
    panel = _panel_after_title(driver, "Modern Category")
    if not panel:
        return ""
    texts = []
    try:
        # Preferred: the code-like muted span, e.g., 'health_care.mental_health_service'
        for el in panel.find_elements(By.CSS_SELECTOR, "span.text-muted, span.font-weight-normal, span"):
            t = el.text.strip()
            if t:
                texts.append(t)
        # Fallback: anchor text(s)
        if not texts:
            for a in panel.find_elements(By.TAG_NAME, "a"):
                t = a.text.strip()
                if t:
                    texts.append(t)
    except Exception:
        pass
    # De-duplicate while preserving order
    seen = set()
    ordered = []
    for t in texts:
        if t not in seen:
            ordered.append(t)
            seen.add(t)
    return ", ".join(ordered)

def scrape_urls(driver) -> str:
    """
    Collect all visible URLs in the Gemini 'URL' section as a comma-separated list of hrefs.
    """
    panel = _panel_after_title(driver, "URL")
    if not panel:
        return ""
    hrefs = []
    try:
        for a in panel.find_elements(By.TAG_NAME, "a"):
            href = (a.get_attribute("href") or "").strip()
            if href:
                hrefs.append(href)
    except Exception:
        pass
    # De-duplicate while preserving order
    seen = set()
    ordered = []
    for u in hrefs:
        if u not in seen:
            ordered.append(u)
            seen.add(u)
    return ", ".join(ordered)

def scrape_vendor_contributions(driver) -> str:
    """
    Extract the Gemini 'Vendor Contributions' table as a compact JSON string.
    Each row becomes {name, vendor, internal_id, score, partners} where available.
    """
    panel = _panel_after_title(driver, "Vendor Contributions")
    if not panel:
        return ""
    rows = []
    try:
        table = panel.find_element(By.CSS_SELECTOR, "table")
        # Identify column order from headers
        headers = [th.text.strip().lower() for th in table.find_elements(By.CSS_SELECTOR, "thead th")]
        body_tr = table.find_elements(By.CSS_SELECTOR, "tbody tr")
        for tr in body_tr:
            cells = [td.text.strip() for td in tr.find_elements(By.CSS_SELECTOR, "td")]
            if not cells:
                continue
            row = {}
            for idx, key in enumerate(headers):
                val = cells[idx] if idx < len(cells) else ""
                row[key] = val
            # Normalize a few expected keys
            norm = {
                "name": row.get("name", ""),
                "vendor": row.get("vendor", ""),
                "internal_id": row.get("vendor internal id", "") or row.get("internal id", ""),
                "score": row.get("score", ""),
                "partners": row.get("partners", ""),
            }
            rows.append(norm)
    except Exception:
        # If the table shape changes, at least return any visible text block
        try:
            txt = panel.text.strip()
            return json.dumps({"raw": " ".join(txt.split())})
        except Exception:
            return ""
    try:
        return json.dumps(rows, ensure_ascii=False)
    except Exception:
        # Fallback serialization
        return str(rows)

# ---------------- Orchestrator for scraping Gemini ----------------
def scrape_gemini(place_id: str, driver) -> dict:
    """
    Load the details page for the given place_id, open the Gemini tab,
    and return a dict with all requested fields.
    """
    _dbg(f"Navigating to details for {place_id}")
    driver.get(PATH + place_id)
    try:
        WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@class,'nav-link') and normalize-space()='Gemini']"))
        )
    except Exception as e:
        _dbe("Details shell did not render as expected", e)
        raise
    ensure_gemini_open(driver)

    result = {
        "place_id": place_id,
        "Show In Client": scrape_show_in_client(driver),
        "Vendors": scrape_vendor_contributions(driver),
        "Modern Category": scrape_modern_category(driver),
        "URLs": scrape_urls(driver),
    }
    _dbg(f"scraped: {json.dumps(result)}")
    return result


def start_driver():
    """
    Start Safari WebDriver with sane defaults. This mirrors the approach used
    in your brand script: try to gracefully handle common safaridriver issues.
    """
    try:
        print("Initializing Safari webdriver...")
        driver = webdriver.Safari()
    except SessionNotCreatedException as ex:
        message = str(ex)
        if "Allow Remote Automation" in message:
            print(
                f"{RED}\tERROR: Must Allow Remote Automation. (Safari > Develop > check Allow Remote Automation)\n{RESET}"
            )
        elif "already paired" in message:
            print(f"{RED}\tERROR: Must stop previous session to start new.\n{RESET}")
        else:
            print(
                f"{RED}\tERROR: Could not start webdriver due to unknown error of type SessionNotCreatedException, report:\n{message}{RESET}"
            )
        traceback.print_exc()
        sys.exit()
    except WebDriverException as ex:
        # Common case where the service needs to be restarted
        try:
            print("Attempting to stop safaridriver service...")
            webdriver.Safari().service.stop()
            print("safaridriver service stopped.")
            driver = webdriver.Safari()
        except:
            error_type = type(ex).__name__
            message = str(ex)
            print(
                f"{RED}ERROR: Could not start webdriver due to unknown error of type {error_type}, report:\n{message}{RESET}"
            )
            sys.exit()
    except Exception as ex:
        error_type = type(ex).__name__
        message = str(ex)
        print(
            f"{RED}\tERROR: Could not start webdriver due to unknown error of type {error_type}, report:\n{message}{RESET}"
        )
        traceback.print_exc()
        sys.exit()
    driver.set_window_rect(5, 30, 1440, 980)
    return driver


def hours_or_show_client_badge(driver, contested_field=None) -> dict:
    """
    On the currently selected version, read the edited badge text for either Hours or Show In Client.
    Returns a dict with a 'mode' and one of 'hours_edit_badge' or 'sic_edit_badge' populated.
    """
    want_hours = (contested_field or "").strip().lower() == "hours"
    title = "Hours" if want_hours else "Show In Client"
    try:
        label = WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, f"//div[@title='{title}']"))
        )
        panel = label.find_element(By.XPATH, "following-sibling::div")
        badge = ""
        try:
            badge = panel.find_element(By.CSS_SELECTOR, ".audit-badge").text.strip()
        except NoSuchElementException:
            try:
                badge = panel.find_element(By.XPATH, ".//span[contains(@class,'badge')]").text.strip()
            except NoSuchElementException:
                badge = ""
        return {"mode": "Hours", "hours_edit_badge": badge} if want_hours else {"mode": "Closures", "sic_edit_badge": badge}
    except Exception:
        return {"mode": "Hours" if want_hours else "Closures", "hours_edit_badge" if want_hours else "sic_edit_badge": ""}
    

if __name__ == "__main__":
    driver = start_driver()

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(
            out_f,
            fieldnames=[
                "place_id",
                "Show In Client",
                "Vendors",
                "Modern Category",
                "URLs",
            ],
        )
        writer.writeheader()

        with open(INPUT_CSV, newline="", encoding="utf-8") as in_f:
            reader = csv.DictReader(in_f)
            # Normalize possible BOM + whitespace in header names
            reader.fieldnames = [fn.lstrip("\ufeff").strip() for fn in reader.fieldnames]
            for row in reader:
                # ---- Robust Place ID cleanup (handles "<br>" and HTML entities)
                pid_raw = (row.get("Place ID", "") or "").strip()
                pid_unescaped = html.unescape(pid_raw)
                pid_no_tags = re.sub(r"<[^>]*>", "", pid_unescaped).strip()
                m = re.search(r"\d+", pid_no_tags)
                pid = m.group(0) if m else ""
                _dbg(f"row Place ID raw={pid_raw!r} → parsed pid={pid!r}")
                if not pid:
                    print("❗ Missing Place ID; skipping.")
                    continue

                print(f"\n=== Processing {pid} ===")
                try:
                    result = scrape_gemini(pid, driver)
                except Exception as e:
                    _dbe("Error in scrape_gemini", e)
                    import traceback as _tb
                    print(_tb.format_exc())
                    result = {"place_id": pid, "Show In Client": "", "Vendors": "", "Modern Category": "", "URLs": ""}
                print(f"→ Result: {json.dumps(result)}")
                writer.writerow(result)

    driver.quit()
    print("✅ All done.")