"""
    LOGIC:
        place details page
            -versions 
                - grab present Hours or Show In Client Badge
                - filter by Hours or Show In Client depending on column header (Contested Field Column)
                - grab hours/show in client badge at edit (prior to 7/25)
                - grab edit date
                - in todos page click first visible item and scrape source level 2 "str (str)"
                - if edited badge -> open and read json( RCA indicator )
"""
                #- identify hours mismatch severity (follow the rules in “Other info" tab

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

RED = "\033[91m"  # errors
GREEN = "\033[92m"  # notes
YELLOW = "\033[93m"  # warnings
MAGENTA = "\033[95m"  # end of each loop iteration warning to verify
RESET = "\033[0m"

def _dbg(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{MAGENTA}[{ts}] {msg}{RESET}")

PATH = "https://apollo.geo.apple.com/p/release/"
INPUT_CSV = "Data_scripting/BC_Hours_and_Closures_Edit_Contests.csv"
OUTPUT_CSV = "BC_hours_&_closures_output.csv"

TIMEOUT = 30
THRESHOLD = datetime(2025, 7, 25)



def start_driver():
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




def click_versions_tab(driver):
    WebDriverWait(driver, TIMEOUT).until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//a[contains(@class,'nav-link') and normalize-space()='Versions']",
            )
        )
    ).click()
    try:
        driver.execute_script("window.scrollTo(0,0);")
    except Exception:
        pass
    wait_versions_ui(driver)

# Helper: Wait until either the Versions list or field filter control is present
def wait_versions_ui(driver):
    """Wait until either the Versions list or the field filter control is present."""
    try:
        WebDriverWait(driver, TIMEOUT).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, "a[id^='entry-']") or
                      d.find_elements(By.CSS_SELECTOR, ".choices__inner, .choices")
        )
    except Exception:
        pass

def ensure_versions_open(driver):
    """
    Ensure we're on the Versions page before interacting with filters.
    If the Versions tab isn't active, click it and wait for the UI to render.
    """
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

def click_todos_tab(driver):
    WebDriverWait(driver, TIMEOUT).until(
        EC.element_to_be_clickable(
            (By.XPATH, "//a[contains(@class,'nav-link') and (normalize-space()='ToDos' or normalize-space()='Todos' or normalize-space()='To-Do')]")
        )
    ).click()
    WebDriverWait(driver, TIMEOUT).until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "[data-test-id='todo-summary__todo-title'], [data-test-id='todo-summary_todo-title'], .todo-summary, [data-test-id='thread-item'], .thread__item")
        )
    )

def todo_source_lvl_2(driver) -> str:
    def _title_to_lvl2(title_txt: str) -> str:
        if not title_txt:
            return ""
        first_chunk = re.split(r"\s+[–-]\s+", title_txt, maxsplit=1)[0]
        m = re.search(r".+?\([^)]*\)", first_chunk)
        return m.group(0).strip() if m else first_chunk.strip()

    try:
        click_todos_tab(driver)
    except Exception:
        return ""

    for sel in ("[data-test-id='todo-summary__todo-title']",
                "[data-test-id='todo-summary_todo-title']",
                ".todo-summary .section-header",
                ".todo-summary h1",
                ".todo-summary h2"):
        try:
            t = driver.find_element(By.CSS_SELECTOR, sel).text.strip()
            if t:
                return _title_to_lvl2(t)
        except NoSuchElementException:
            continue

    for sel in (".view-place-todos__todo-list [data-test-id='thread-item']",
                ".view-place-todos__todo-list .thread__item",
                "[data-test-id='thread-item']",
                ".thread__item"):
        rows = driver.find_elements(By.CSS_SELECTOR, sel)
        rows = [r for r in rows if r.is_displayed()]
        if rows:
            try:
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable(rows[0])).click()
            except Exception:
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", rows[0])
                    driver.execute_script("arguments[0].click();", rows[0])
                except Exception:
                    pass
            break

    for sel in ("[data-test-id='todo-summary__todo-title']",
                "[data-test-id='todo-summary_todo-title']",
                ".todo-summary .section-header",
                ".todo-summary h1",
                ".todo-summary h2"):
        try:
            t = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, sel))).text.strip()
            if t:
                return _title_to_lvl2(t)
        except Exception:
            continue

    return ""

def get_present_badge(driver, contested_field=None) -> str:
    want_hours = (contested_field or "").strip().lower() == "hours"
    label_title = "Hours" if want_hours else "Show In Client"
    try:
        label = WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located((By.XPATH, f"//div[@title='{label_title}']"))
        )
        panel = label.find_element(By.XPATH, "following-sibling::div")
        try:
            return panel.find_element(By.CSS_SELECTOR, ".audit-badge").text.strip()
        except NoSuchElementException:
            try:
                return panel.find_element(By.XPATH, ".//span[contains(@class,'badge')]").text.strip()
            except NoSuchElementException:
                return ""
    except Exception:
        return ""

def hours_or_show_client_badge(driver, contested_field=None) -> dict:
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


def choose_field(driver, filter_key: str) -> bool:
    """
    Open the Choices.js dropdown and select option by data-value (reference-style).
    filter_key ∈ {'hours_period', 'presence_period'}
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
    """Return sorted list of (datetime, entry_id) ascending (oldest → newest)."""
    wait = WebDriverWait(driver, TIMEOUT)
    try:
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[id^='entry-']")))
    except TimeoutException:
        return []
    raw = driver.find_elements(By.CSS_SELECTOR, "a[id^='entry-']")
    entries = []
    for e in raw:
        try:
            txt = e.find_element(By.TAG_NAME, "span").text  # "YYYY-MM-DD 01:23 PM CDT"
            dt = datetime.strptime(txt.rsplit(" ", 1)[0], "%Y-%m-%d %I:%M %p")
            entries.append((dt, e.get_attribute("id")))
        except Exception:
            continue
    return sorted(entries, key=lambda x: x[0])

def click_version(driver, entry_id):
    wait = WebDriverWait(driver, TIMEOUT)
    wait.until(EC.element_to_be_clickable((By.ID, entry_id))).click()
    wait.until(EC.presence_of_element_located((By.XPATH, "//div[@title='Show In Client']")))
    wait.until(EC.presence_of_element_located((By.XPATH, "//div[@title='Hours']")))


def find_change_version(place_id, driver, contested_field=None):
    print(f"🔄 Processing place_id={place_id}")
    driver.get(PATH + place_id)
    WebDriverWait(driver, TIMEOUT).until(
        EC.presence_of_element_located((By.XPATH, "//a[contains(@class,'nav-link') and normalize-space()='Versions']"))
    )

    present_badge = get_present_badge(driver, contested_field) or ""

    click_versions_tab(driver)
    norm_cf = (contested_field or "").strip().lower()
    filter_key = "hours_period" if norm_cf == "hours" else "presence_period"
    if not choose_field(driver, filter_key):
        print(f"{YELLOW}[filter] continuing without filter{RESET}")

    versions = collect_versions(driver)
    if not versions:
        return {"place_id": place_id, "edited_at": "", "present_badge": present_badge,
                "show_client_edited_badge": "", "todo_source_lvl_2": "", "rca_indicator": ""}

    chosen = None
    for dt, vid in versions:
        if dt < THRESHOLD:
            chosen = (dt, vid)
    if chosen is None:
        chosen = versions[0]
    prior_dt, prior_id = chosen

    click_version(driver, prior_id)

    scraped = hours_or_show_client_badge(driver, contested_field)
    mode = scraped.get("mode")
    edited_badge = scraped.get("hours_edit_badge", "") if mode == "Hours" else scraped.get("sic_edit_badge", "")

    edited_at_str = f"{prior_dt.month}/{prior_dt.day}/{prior_dt.year}" if isinstance(prior_dt, datetime) else str(prior_dt)

    source_lvl_2 = todo_source_lvl_2(driver) or ""
    rca_indicator = ""  # disabled

    return {
        "place_id": place_id,
        "edited_at": edited_at_str,
        "present_badge": present_badge,
        "show_client_edited_badge": edited_badge,
        "todo_source_lvl_2": source_lvl_2,
        "rca_indicator": rca_indicator,
    }


if __name__ == "__main__":
    driver = start_driver()

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(
            out_f,
            fieldnames=[
                "place_id",
                "edited_at",
                "present_badge",
                "show_client_edited_badge",
                "todo_source_lvl_2",
                "rca_indicator",
            ],
        )
        writer.writeheader()

        with open(INPUT_CSV, newline="", encoding="utf-8") as in_f:
            reader = csv.DictReader(in_f)
            reader.fieldnames = [fn.lstrip("\ufeff").strip() for fn in reader.fieldnames]
            for row in reader:
                pid_raw = (row.get("Place ID", "") or "").strip()
                pid_unescaped = html.unescape(pid_raw)
                pid_no_tags = re.sub(r"<[^>]*>", "", pid_unescaped).strip()
                m = re.search(r"\d+", pid_no_tags)
                pid = m.group(0) if m else ""
                if not pid:
                    print("❗ Missing Place ID; skipping.")
                    continue
                
                contested_field = (row.get("Contested Field", "") or row.get("Contested Field Column", "") or "").strip()
                print(f"\n=== Processing {pid} ===")
                try:
                    result = find_change_version(pid, driver, contested_field=contested_field)
                except Exception as e:
                    print(f"{RED}❌ Error in find_change_version for {pid}: {e}{RESET}")
                    result = {"place_id": pid, "edited_at": "", "present_badge": "", "show_client_edited_badge": "", "todo_source_lvl_2": "", "rca_indicator": ""}
                print(f"→ Result: {json.dumps(result)}")
                writer.writerow(result)

    driver.quit()
    print("✅ All done.")