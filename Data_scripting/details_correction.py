"""
Scrape Corrections data from KittyHawk-SIG ticket details by Ticket ID.

Logic:
1) Build URL: PATH + <Ticket ID>
2) Wait for page to load and locate the "Corrections" section by div[@title='Corrections']
3) Scrape ALL visible text contained in the value container next to that label
4) Write to CSV with columns: "Ticket ID", "Corrections"
"""

import csv
import sys
import traceback
from selenium import webdriver
from selenium.common.exceptions import SessionNotCreatedException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import re
import time

# ---------- Config ----------
PATH = "https://apollo.geo.apple.com/tickets/kittyhawk-sig/"
INPUT_CSV = "NEI_report.csv"             # must contain column "Ticket ID"
OUTPUT_CSV = "NEI_report_output.csv"
TIMEOUT = 30

RED = "\033[91m"  # errors
GREEN = "\033[92m"  # notes
YELLOW = "\033[93m"  # warnings
MAGENTA = "\033[95`m"  # end of each loop iteration warning to verify
RESET = "\033[0m"

# Optional pacing/cleansing
DELAY_BETWEEN_TICKETS = 0.75  # seconds; slow down if pages feel racy
SLOW_MODE_EXTRA_WAIT = 0.5    # extra wait after navigation

# ---------- Helper ----------
def clean_ticket_id(value: str) -> str:
    """
    Normalize a Ticket ID read from CSV rows:
      - strip BOM/whitespace/quotes
      - remove leading non-alphanumeric noise
      - collapse internal spaces
    If the ID is purely numeric with stray symbols, keep only digits.
    """
    if value is None:
        return ""
    s = str(value)
    # Remove BOM and surrounding whitespace/quotes
    s = s.replace("\ufeff", "").strip().strip('"').strip("'")
    # Collapse spaces
    s = re.sub(r"\s+", "", s)
    if not s:
        return ""
    # If it contains digits only plus noise, keep only digits
    if re.fullmatch(r"[\W_]*\d[\d\W_]*", s):
        digits = re.sub(r"\D", "", s)
        return digits
    # Otherwise, drop any leading non-alphanumeric run
    s = re.sub(r"^[^A-Za-z0-9]+", "", s)
    return s

# ---------- Driver ----------
def start_driver():
    try:
        print("Initializing Safari webdriver...")
        driver = webdriver.Safari()
    except SessionNotCreatedException as ex:
        message = str(ex)
        if "Allow Remote Automation" in message:
            print(f"{RED}ERROR: Enable Safari › Develop › Allow Remote Automation{RESET}")
        elif "already paired" in message:
            print(f"{RED}ERROR: Stop the previous safaridriver session first.{RESET}")
        else:
            print(f"{RED}ERROR: Could not start webdriver (SessionNotCreatedException): {message}{RESET}")
        traceback.print_exc()
        sys.exit(1)
    except WebDriverException as ex:
        try:
            print("Attempting to stop safaridriver service and retry...")
            webdriver.Safari().service.stop()
            driver = webdriver.Safari()
        except Exception:
            print(f"{RED}ERROR: WebDriverException: {type(ex).__name__}: {ex}{RESET}")
            sys.exit(1)
    except Exception as ex:
        print(f"{RED}ERROR: Unknown during driver start: {type(ex).__name__}: {ex}{RESET}")
        traceback.print_exc()
        sys.exit(1)

    driver.set_window_rect(5, 30, 1440, 980)
    return driver

def extract_corrections_structured(driver):
    """
    Return structured corrections:
      - list_items: list of bullet items
      - json_blocks: list of JSON blobs (minified)
      - code_blocks: list of non-JSON code snippets
      - all_text: flattened visible text for reference
    """
    wait = WebDriverWait(driver, TIMEOUT)
    try:
        label_el = wait.until(
            EC.presence_of_element_located((By.XPATH, "//div[@title='Corrections']"))
        )
    except TimeoutException:
        return {"list_items": [], "json_blocks": [], "code_blocks": [], "all_text": ""}

    try:
        value_container = label_el.find_element(By.XPATH, "following-sibling::div[1]")
    except NoSuchElementException:
        return {"list_items": [], "json_blocks": [], "code_blocks": [], "all_text": ""}

    # Collect list items
    list_items = []
    for li in value_container.find_elements(By.CSS_SELECTOR, "li"):
        txt = (li.text or "").strip()
        if txt:
            list_items.append(txt)

    # Collect code blocks
    raw_code_blocks = []
    for code in value_container.find_elements(By.TAG_NAME, "code"):
        txt = (code.text or "").strip()
        if txt:
            raw_code_blocks.append(txt)

    json_blocks = []
    code_blocks = []
    for block in raw_code_blocks:
        candidate = block.strip()
        # Quick guards: starts with { or [ is likely JSON
        if candidate.startswith("{") or candidate.startswith("["):
            try:
                obj = json.loads(candidate)
                json_blocks.append(json.dumps(obj, separators=(",", ":")))
                continue
            except Exception:
                pass
        # If not JSON or parse failed, keep as code text
        code_blocks.append(candidate)

    # Flatten all visible text as a reference column
    all_lines = []
    seen = set()
    for line in (value_container.text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if line in list_items or line in raw_code_blocks:
            # already represented explicitly
            pass
        if line not in seen:
            seen.add(line)
            all_lines.append(line)

    return {
        "list_items": list_items,
        "json_blocks": json_blocks,
        "code_blocks": code_blocks,
        "all_text": " | ".join(all_lines),
    }

# ---------- Main ----------
def clean_ticket_id(value: str) -> str:
    """
    Normalize a Ticket ID from CSV. Some rows contain HTML like '&lt;br&gt;123...'.
    We:
      - convert common HTML entities (&lt; &gt; &amp;)
      - remove any <br> or <br/> tags
      - extract the longest run of digits (ticket IDs are numeric only)
    Returns '' if no digit run is found.
    """
    if value is None:
        return ""
    s = str(value)
    # Remove BOM and trim whitespace/quotes
    s = s.replace("\ufeff", "").strip().strip('"').strip("'")
    # Decode minimal HTML entities that show up in CSV
    s = s.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    # Drop any <br> tags (case-insensitive, optional slash/space)
    s = re.sub(r"(?i)<\s*br\s*/?\s*>", "", s)
    # Now extract the longest digit run (ticket ids are numeric)
    digit_runs = re.findall(r"\d+", s)
    if not digit_runs:
        return ""
    # choose the longest sequence of digits
    return max(digit_runs, key=len)

def main():
    driver = start_driver()

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=["Ticket ID", "Corrections_List", "Corrections_JSON", "Corrections_Code", "Corrections_Text"])
        writer.writeheader()

        with open(INPUT_CSV, newline="", encoding="utf-8") as in_f:
            reader = csv.DictReader(in_f)
            # Handle potential BOM and trim headers
            reader.fieldnames = [fn.lstrip("\ufeff").strip() for fn in reader.fieldnames]

            for i, row in enumerate(reader, start=1):
                raw_id = (row.get("Ticket ID") or "")
                ticket_id = clean_ticket_id(raw_id)
                if not ticket_id:
                    print(f"{YELLOW}Row {i}: Empty/invalid 'Ticket ID' after cleaning (raw='{raw_id}'); skipping.{RESET}")
                    continue
                if str(raw_id).strip() != ticket_id:
                    print(f"{YELLOW}Row {i}: cleaned Ticket ID from '{raw_id}' -> '{ticket_id}' (removed HTML/noise){RESET}")

                print(f"\n=== Processing Ticket {ticket_id} ===")
                try:
                    open_ticket(ticket_id, driver)
                    data = extract_corrections_structured(driver)
                    writer.writerow({
                        "Ticket ID": ticket_id,
                        "Corrections_List": " ; ".join(data["list_items"]) if data else "",
                        "Corrections_JSON": " || ".join(data["json_blocks"]) if data else "",
                        "Corrections_Code": " || ".join(data["code_blocks"]) if data else "",
                        "Corrections_Text": data["all_text"] if data else "",
                    })
                    print(f"{GREEN}✓ Wrote corrections for {ticket_id}{RESET}")
                    time.sleep(DELAY_BETWEEN_TICKETS)
                except Exception as ex:
                    print(f"{RED}✗ Error on ticket {ticket_id}: {type(ex).__name__}: {ex}{RESET}")
                    traceback.print_exc()
                    # Write an empty/partial row so we preserve ordering
                    writer.writerow({
                        "Ticket ID": ticket_id,
                        "Corrections_List": "",
                        "Corrections_JSON": "",
                        "Corrections_Code": "",
                        "Corrections_Text": "",
                    })
                    time.sleep(DELAY_BETWEEN_TICKETS)

    driver.quit()
    print(f"{GREEN}✅ Done. Output → {OUTPUT_CSV}{RESET}")

def open_ticket(ticket_id: str, driver) -> None:
    """Navigate directly to the KittyHawk-SIG ticket details page."""
    url = PATH + ticket_id
    driver.get(url)
    # Give Safari a moment to settle if the page is heavy
    time.sleep(SLOW_MODE_EXTRA_WAIT)

if __name__ == "__main__":
    main()
