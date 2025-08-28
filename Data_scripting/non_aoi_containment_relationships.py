

#SCRAPPED


"""
columns to enter: Child URL | Parent URL
check child poi:
After entering Versions:
    Click -> filter field
      Enter earliest Parent entry
        Check if Cureated POI Parents is applied
            move to next version
              Once identified:
              * Use all fields to check previous dated version
              if parent present then iterate till its not
              Save last instance of parent presence
                Obtain the following:
                    - Curated POI Parent
                    - What Applied Parent badge? (Source)
                    - Date applied
                    OPTIONAL : obtain JSON data at application
"""

import datetime
import re
import csv
import sys
import traceback
from selenium import webdriver
from selenium.common.exceptions import SessionNotCreatedException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from urllib.parse import urlsplit

import re

def extract_url(cell_value: str) -> str:
    """Try to get a real URL from a CSV cell. Handles:
    - Google Sheets/Excel HYPERLINK("url","text")
    - Plain http(s) URL
    - Domain without scheme
    - Otherwise returns '' if just display text (like 'Oren Salon').
    """
    if not cell_value:
        return ""
    val = cell_value.strip()

    # Case: HYPERLINK("url","text")
    m = re.search(r'HYPERLINK\((?:\"|\')([^\"\']+)(?:\"|\')', val, re.IGNORECASE)
    if m:
        return m.group(1)

    # Case: Already a proper URL
    if val.startswith(("http://", "https://")):
        return val

    # Case: domain without scheme
    if "." in val and " " not in val:
        return "https://" + val

    # Otherwise it's just display text
    return ""

RED = "\033[91m"  # errors
GREEN = "\033[92m"  # notes
YELLOW = "\033[93m"  # warnings
MAGENTA = "\033[95m"  # end of each loop iteration warning to verify
RESET = "\033[0m"

INPUT_CSV = "Non_AOI_Containment_Relationships.csv"
OUTPUT_CSV = "non_aoi_output.csv"
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


def extract_curated_poi_parent(driver):
    try:
        brand_row = WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@title='Curated POI Parents']/following-sibling::div")
            )
        )

        # Case 1: explicit None placeholder (not branded)
        placeholders = brand_row.find_elements(
            By.XPATH, ".//span[contains(@class,'text-placeholder')]"
        )
        for sp in placeholders:
            if sp.text.strip().lower() == "none":
                return "None"

        # Value container typically holding the brand text and/or the id link
        value_div = brand_row.find_element(By.CSS_SELECTOR, "div.col-value")
        full_text = value_div.text.strip()

        # Case 2: quoted brand text is visible -> extract inside quotes
        m = re.search(r'"([^\"]+)"', full_text)
        if m:
            return m.group(1).strip()

        # Remove purely numeric ids in parentheses, e.g. (792633534608192774)
        cleaned = re.sub(r"\(\d+\)", "", full_text).strip()
        # Normalize spaces and trim quotes
        cleaned = re.sub(r"\s+", " ", cleaned).strip().strip('"').strip()

        # If there is still alphabetic content, treat it as the brand
        if re.search(r"[A-Za-z]", cleaned):
            return cleaned

        # If we reach here, the row isn't 'None' and contains an <a> link with only an id -> branded but not visible
        links = value_div.find_elements(By.TAG_NAME, "a")
        if links:
            return "not visible"

        # Fallback
        return "None"
    except Exception:
        return "None"


def extract_brand_applier_source(driver):
    try:
        brand_row = WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@title='Brand']/following-sibling::div")
            )
        )
        badge_element = brand_row.find_element(By.CSS_SELECTOR, ".badge.audit-badge")
        badge_hover = (
            badge_element.get_attribute("title").strip()
            if badge_element.get_attribute("title")
            else ""
        )
        return badge_hover
    except Exception:
        return "", ""


# ------------ choose 1 of the following fields
#  brand, name, url, phone_number, presence_period, is_blessed, geocode, category, relationship, address,
#  hours_period, icon_custom_id, structured_attributes.is_apple_pay_supported, associated_app, vendor_geometry_id, vendor_geometry_id,
#  vendor_contrivution, indoor, message_profile


def choose_field(driver):
    dropdown_trigger_xpath = (
        "//div[contains(@class, 'choices__item--selectable') and @data-value='none']"
    )
    WebDriverWait(driver, TIMEOUT).until(
        EC.element_to_be_clickable((By.XPATH, dropdown_trigger_xpath))
    ).click()
    try:
        WebDriverWait(driver, TIMEOUT).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,  # your chosen field "relationship"
                    "//div[contains(@class, 'choices__item') and @data-value='relationship']",
                )
            )
        ).click()
    except TimeoutException:
        print(f"{RED}Timeout: 'Parent' filter not found or not clickable.{RESET}")
        return False
    return True


def click_versions_tab(driver):
    WebDriverWait(driver, TIMEOUT).until(
        EC.element_to_be_clickable(
            (
                By.XPATH,
                "//a[contains(@class,'nav-link') and normalize-space()='Versions']",
            )
        )
    ).click()


def click_version(driver, entry_id):
    wait = WebDriverWait(driver, TIMEOUT)
    wait.until(EC.element_to_be_clickable((By.ID, entry_id))).click()



def scrape_badge(hyperlink, driver):
    print(f"Processing POI={hyperlink}")
    driver.get(hyperlink)
    try:
        click_versions_tab(driver)
        # filtering for brand
        if not choose_field(driver):
            print(f"{RED}Skipping POI due to brand filter.{RESET}")
            return None
        # iterate up oldest -> newest
        prior_poi_name = None
        prior_ow_url = None
        click_version(driver, entry_id)
        # brand check
        parent_info = extract_curated_poi_parent(driver)
        if parent_info != "None":
            # scrape fields
            brand_app_hover = extract_brand_applier_source(driver)
            print("→ Scraped data for POI")
            return {
                "Brand Name": parent_info,
                "What Applied Brand? (Source)": brand_app_hover,
            }
        # save POI name for next iteration
        # if no brand found, return empty
        print(f"{YELLOW}No Brand data found in any version.{RESET}")
        return {
            "Parent Name": "None",
            "What Applied Parent? (Source)": "",
        }
    finally:
        pass


if __name__ == "__main__":
    driver = start_driver()
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(
            out_f,
            fieldnames=[
                "Parent Name",
                "What Applied Brand? (Source)",
            ],
        )
        writer.writeheader()
        with open(INPUT_CSV, newline="", encoding="utf-8") as in_f:
            reader = csv.DictReader(in_f)
            reader.fieldnames = [
                fn.lstrip("\ufeff").strip() for fn in reader.fieldnames
            ]
            for row in reader:
                raw_val = (row.get("Hyperlink") or "").strip()
                hyperlink = extract_url(raw_val)
                if not hyperlink:
                    print(f":exclamation: Skipping row, no parseable URL (value was: {raw_val!r})")
                    continue
                result = scrape_badge(hyperlink, driver)
                # print(f"Result: {json.dumps(result)}")
                writer.writerow(result)
    driver.quit()
    print(":: All done.")