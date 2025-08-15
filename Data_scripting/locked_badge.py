import csv
import sys
import json
import time
import traceback
from datetime import datetime
from selenium import webdriver
from selenium.common.exceptions import SessionNotCreatedException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException


RED = "\033[91m"  # errors
GREEN = "\033[92m"  # notes
YELLOW = "\033[93m"  # warnings
MAGENTA = "\033[95m"  # end of each loop iteration warning to verify
RESET = "\033[0m"


PATH = "https://apollo.geo.apple.com/?query="
INPUT_CSV = "tickets/input.csv"
OUTPUT_CSV = "tickets/output.csv"
TIMEOUT = 30


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


def get_locked_label(driver):
    wait = WebDriverWait(driver, TIMEOUT)
    label = wait.until(
        EC.presence_of_element_located((By.XPATH, "//div[@title='Locked']"))
    )
    panel = label.find_element(By.XPATH, "following-sibling::div")
    modern = []
    for row in panel.find_elements(By.CSS_SELECTOR, ".audit-row.row-details"):
        try:
            name = row.find_element(By.CSS_SELECTOR, ".category-display").text.strip()
            badge = row.find_element(By.CSS_SELECTOR, ".badge.audit-badge").text.strip()
            modern.append({"name": name, "badge": badge})
        except:
            continue
    return modern


# remove up to versions check
# instead of versions check-> find locked  field and scrap along with underscript
def find_change_version(place_id, driver, threshold=datetime(2025, 6, 20)):
    wait = WebDriverWait(driver, TIMEOUT)
    print(f"🔄 Processing place_id={place_id}")
    main, popup = open_and_switch(place_id, driver)
    try:
        click_versions_tab(driver)
        versions = collect_versions(driver)

        base_idx, (base_dt, base_id) = next(
            (i, pair) for i, pair in enumerate(versions) if pair[0] >= threshold
        )
        click_version(driver, base_id)

        prev_dt = base_dt

        mod_panel = driver.find_element(
            By.XPATH, "//div[@title='Modern Category']/following-sibling::div[1]"
        )
        prev_mod_el = mod_panel.find_element(By.CSS_SELECTOR, ".audit-badge")
        prev_mod_badge = prev_mod_el.text.strip()
        prev_mod_badge_hover = prev_mod_el.get_attribute("title").strip()

        try:
            audit_row = driver.find_element(
                By.XPATH,
                "//div[contains(@class,'audit-row')][.//div[@data-test-id='hours']]",
            )
            prev_hours_el = audit_row.find_element(By.CSS_SELECTOR, ".audit-badge")
            prev_hours_badge = prev_hours_el.text.strip()
            prev_hours_badge_hover = prev_hours_el.get_attribute("title").strip()
        except NoSuchElementException:
            prev_hours_badge = ""
            prev_hours_badge_hover = ""

        for dt, eid in versions[base_idx + 1 :]:
            print(f"⤷ Processing version {eid} at {dt}")
            click_version(driver, eid)

            mod_panel = driver.find_element(
                By.XPATH, "//div[@title='Modern Category']/following-sibling::div[1]"
            )
            curr_mod_el = mod_panel.find_element(By.CSS_SELECTOR, ".audit-badge")
            curr_mod_badge = curr_mod_el.text.strip()
            curr_mod_badge_hover = curr_mod_el.get_attribute("title").strip()

            try:
                audit_row = driver.find_element(
                    By.XPATH,
                    "//div[contains(@class,'audit-row')][.//div[@data-test-id='hours']]",
                )
                curr_hours_el = audit_row.find_element(By.CSS_SELECTOR, ".audit-badge")
                curr_hours_badge = curr_hours_el.text.strip()
                curr_hours_badge_hover = curr_hours_el.get_attribute("title").strip()
            except NoSuchElementException:
                curr_hours_badge = ""
                curr_hours_badge_hover = ""

            if (
                curr_mod_badge != prev_mod_badge
                or curr_mod_badge_hover != prev_mod_badge_hover
                or curr_hours_badge != prev_hours_badge
                or curr_hours_badge_hover != prev_hours_badge_hover
            ):
                print(f"❗ Change at {dt} — returning prior version’s ({prev_dt}) data")
                return {
                    "place_id": place_id,
                    "changed_at": prev_dt.isoformat(),
                    "hours_badge": prev_hours_badge,
                    "hours_badge_hover": prev_hours_badge_hover,
                    "modern_cat_badge": prev_mod_badge,
                    "modern_cat_badge_hover": prev_mod_badge_hover,
                }

            prev_dt = dt
            prev_mod_badge = curr_mod_badge
            prev_mod_badge_hover = curr_mod_badge_hover
            prev_hours_badge = curr_hours_badge
            prev_hours_badge_hover = curr_hours_badge_hover

        print("→ No change detected; returning last-seen data")
        return {
            "place_id": place_id,
            "changed_at": "No change was detected",
            "hours_badge": prev_hours_badge,
            "hours_badge_hover": prev_hours_badge_hover,
            "modern_cat_badge": prev_mod_badge,
            "modern_cat_badge_hover": prev_mod_badge_hover,
        }

    finally:
        driver.close()
        driver.switch_to.window(main)


if __name__ == "__main__":
    driver = start_driver()

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(
            out_f,
            fieldnames=[
                "place_id",
                "changed_at",
                "hours_badge",
                "hours_badge_hover",
                "modern_cat_badge",
                "modern_cat_badge_hover",
            ],
        )
        writer.writeheader()

        with open(INPUT_CSV, newline="", encoding="utf-8") as in_f:
            reader = csv.DictReader(in_f)
            reader.fieldnames = [
                fn.lstrip("\ufeff").strip() for fn in reader.fieldnames
            ]
            for row in reader:
                pid = row.get("Place ID", "").strip()
                if not pid:
                    print("❗ Missing Place ID; skipping.")
                    continue

                print(f"\n=== Processing {pid} ===")
                result = find_change_version(pid, driver)
                print(f"→ Result: {json.dumps(result)}")
                writer.writerow(result)

    driver.quit()
    print("✅ All done.")

"""

            (Editing locked by setting is_blessed:
            No)

            
<div class="text-muted font-size-sm">
            (Editing locked by setting is_blessed:
            No)

            <!----></div>
 No
          
<!---->
<div class="col-value text-break col-10"><!----> No
          <div class="text-muted font-size-sm">
            (Editing locked by setting is_blessed:
            No)

            <!----></div></div>
<div title="Locked" class="col-label col-2"><div class="col-label__label">
        Locked
       </div> <div class="col-label__sub-label text-placeholder"></div></div>
<div class="row row-details row-details-separated-when-compact"><div title="Locked" class="col-label col-2"><div class="col-label__label">
        Locked
       </div> <div class="col-label__sub-label text-placeholder"></div></div> <div class="col-value text-break col-10"><!----> No
          <div class="text-muted font-size-sm">
            (Editing locked by setting is_blessed:
            No)

            <!----></div></div></div>
<!---->
<div class="row row-details row-details-separated-when-compact"><div title="High Profile" class="col-label col-2"><div class="col-label__label">
        High Profile
       </div> <div class="col-label__sub-label text-placeholder"></div></div> <div class="col-value text-break col-10"><!----> <span class="text-placeholder">
  None
</span></div></div>
<div class="row row-details row-details-separated-when-compact"><div title="Significance" class="col-label col-2"><div class="col-label__label">
        Significance
       </div> <div class="col-label__sub-label text-placeholder"></div></div> <div class="col-value text-break col-10"><!----> <span class="text-placeholder">
  None
</span></div></div>
"""
