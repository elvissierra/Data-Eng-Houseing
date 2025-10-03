

"""
Standalone POI name scraper.

Reads a CSV with a column header "Place Id" (note the capital I in Id),
opens each POI details page using PATH + <Place Id>, and writes a CSV
with columns: place_id, place_name.

Usage (defaults shown):
    python Data_scripting/place_name.py [INPUT_CSV] [OUTPUT_CSV] [ID_COLUMN]

Defaults:
    INPUT_CSV = Data_scripting/BC_Hours_and_Closures_Edit_Contests.csv
    OUTPUT_CSV = poi_names_output.csv
    ID_COLUMN  = "Place Id"
"""

import csv
import html
import re
import sys
import traceback
import time
from selenium import webdriver
from selenium.common.exceptions import SessionNotCreatedException, WebDriverException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Console colors (optional)
RED = "\033[91m"
RESET = "\033[0m"

# --- Config ---
TIMEOUT = 30
PATH = "https://apollo.geo.apple.com/p/release/"  # base details page

# Throttling / resilience defaults (can be overridden via CLI flags)
STARTUP_DELAY = 3.0   # seconds to pause after launching the driver
NAV_DELAY = 1.25      # seconds to pause right after driver.get(url)
RETRIES = 3           # navigation/ready retries per POI

DEFAULT_INPUT = "2_BC_Hours_and_Closures_Edit_Contests.csv"
DEFAULT_OUTPUT = "poi_names_output.csv"
DEFAULT_ID_COLUMN = "Place Id"  # <- per request


def start_driver():
    """Start Safari WebDriver with the project's standard resilience."""
    try:
        print("Initializing Safari webdriver...")
        driver = webdriver.Safari()
    except SessionNotCreatedException as ex:
        message = str(ex)
        if "Allow Remote Automation" in message:
            print(f"{RED}\tERROR: Must Allow Remote Automation. (Safari > Develop > Allow Remote Automation){RESET}")
        elif "already paired" in message:
            print(f"{RED}\tERROR: Must stop previous session to start new.{RESET}")
        else:
            print(f"{RED}\tERROR: Could not start webdriver: {message}{RESET}")
        traceback.print_exc()
        sys.exit(1)
    except WebDriverException as ex:
        try:
            print("Attempting to stop safaridriver service...")
            webdriver.Safari().service.stop()
            print("safaridriver service stopped.")
            driver = webdriver.Safari()
        except Exception:
            print(f"{RED}ERROR: Could not start webdriver: {ex}{RESET}")
            sys.exit(1)
    except Exception as ex:
        print(f"{RED}\tERROR: Unexpected error starting webdriver: {ex}{RESET}")
        traceback.print_exc()
        sys.exit(1)

    driver.set_window_rect(5, 30, 1440, 980)
    driver.implicitly_wait(2)
    time.sleep(STARTUP_DELAY)
    return driver


def _wait_ready_state(driver, timeout: int = TIMEOUT):
    """Poll document.readyState until 'complete' or timeout."""
    end = time.time() + timeout
    while time.time() < end:
        try:
            state = driver.execute_script("return document.readyState")
            if state == "complete":
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


def _wait_url_contains(driver, needle: str, timeout: int = TIMEOUT):
    """Wait until current_url contains substring needle."""
    end = time.time() + timeout
    while time.time() < end:
        try:
            if needle in (driver.current_url or ""):
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


def _wait_details_loaded(driver):
    """Wait for reliable markers on the details page so name selectors are present."""
    try:
        # Prefer the Name row label as a ready signal; fall back to Hours.
        WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, "//div[@title='Name']"))
        )
    except TimeoutException:
        try:
            WebDriverWait(driver, TIMEOUT).until(
                EC.presence_of_element_located((By.XPATH, "//div[@title='Hours']"))
            )
        except TimeoutException:
            # Non-fatal; we'll still attempt to read the name
            pass


def _get_place_name(driver) -> str:
    """Best-effort extraction of the POI's display name.

    Priority order:
      1) Details row value next to the label div[@title='Name']
      2) Common header/title fallbacks
    """
    try:
        # 1) Canonical: the details row labeled Name, value column spans
        value_containers = driver.find_elements(By.XPATH, "//div[@title='Name']/following-sibling::div")
        if value_containers:
            # Grab visible text from first span or direct text
            spans = value_containers[0].find_elements(By.XPATH, ".//span[normalize-space()]")
            if spans:
                txt = spans[0].text.strip()
                if txt:
                    return txt
            raw = value_containers[0].text.strip()
            if raw:
                return raw

        # 2) Header/title based heuristics
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


def _clean_place_id(raw: str) -> str:
    """Strip tags/entities and pull first number; if none, return raw."""
    s = (raw or "").strip()
    if not s:
        return ""
    s = html.unescape(s)
    s = re.sub(r"<[^>]*>", "", s)  # drop any HTML like <br>
    m = re.search(r"\d+", s)
    return m.group(0) if m else s



def scrape_name_for_row(driver, place_id: str) -> dict:
    url = PATH + str(place_id)

    last_exc = None
    for attempt in range(1, RETRIES + 1):
        try:
            driver.get(url)
            # small human-like pause so SSO / redirects can settle
            time.sleep(NAV_DELAY)

            # wait for page load & expected URL shape
            _wait_ready_state(driver, timeout=TIMEOUT)
            _wait_url_contains(driver, "/p/release/", timeout=TIMEOUT)

            # try to wait for details markers
            _wait_details_loaded(driver)

            # minor jiggle to trigger lazy loads
            try:
                driver.execute_script("window.scrollBy(0, 60)")
                time.sleep(0.15)
                driver.execute_script("window.scrollBy(0, -60)")
            except Exception:
                pass

            name = _get_place_name(driver)
            if name:
                return {"place_id": str(place_id), "place_name": name}
            # If name blank, raise to retry
            raise TimeoutException("Name not found yet")
        except Exception as e:
            last_exc = e
            # backoff before retry
            time.sleep(STARTUP_DELAY * (attempt))
    # After retries, return best-effort (blank name) and log once
    print(f"{RED}Failed to load/scrape name for {place_id}: {last_exc}{RESET}")
    return {"place_id": str(place_id), "place_name": ""}


def main(input_csv: str, output_csv: str, id_column: str):
    driver = start_driver()
    try:
        with open(output_csv, "w", newline="", encoding="utf-8") as out_f:
            writer = csv.DictWriter(out_f, fieldnames=["place_id", "place_name"])
            writer.writeheader()

            with open(input_csv, newline="", encoding="utf-8") as in_f:
                reader = csv.DictReader(in_f)
                # Normalize BOM + whitespace in headers
                reader.fieldnames = [fn.lstrip("\ufeff").strip() for fn in reader.fieldnames]

                for row in reader:
                    raw = row.get(id_column, "")
                    pid = _clean_place_id(raw)
                    if not pid:
                        print(":exclamation: Missing Place Id; skipping.")
                        continue
                    rec = scrape_name_for_row(driver, pid)
                    print(f"→ {rec}")
                    writer.writerow(rec)
    finally:
        driver.quit()
        print("✅ Done (POI names).")


if __name__ == "__main__":
    # Optional throttling flags: --startup-delay, --nav-delay, --retries
    for i, arg in enumerate(list(sys.argv)):
        if arg == "--startup-delay" and len(sys.argv) > i + 1:
            try:
                globals()["STARTUP_DELAY"] = float(sys.argv[i + 1])
            except Exception:
                pass
        if arg == "--nav-delay" and len(sys.argv) > i + 1:
            try:
                globals()["NAV_DELAY"] = float(sys.argv[i + 1])
            except Exception:
                pass
        if arg == "--retries" and len(sys.argv) > i + 1:
            try:
                globals()["RETRIES"] = int(sys.argv[i + 1])
            except Exception:
                pass
    # CLI args: INPUT OUTPUT ID_COLUMN
    input_csv = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT
    output_csv = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT
    id_column = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_ID_COLUMN
    main(input_csv, output_csv, id_column)