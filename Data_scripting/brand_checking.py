"""
After entering Versions:
Click -> filter field
  Enter earliest Brand entry
    Check if Brand is applied
      *log poi name
        move to next version
          Once identified:
            Obtain the following:
                -Brand Name
                -What Applied Brand? (Source)
                -What Applied Brand (Version Header)
                -Brand Modern Category
               *-POI name prior to Brand Application
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

RED = "\033[91m"  # errors
GREEN = "\033[92m"  # notes
YELLOW = "\033[93m"  # warnings
MAGENTA = "\033[95m"  # end of each loop iteration warning to verify
RESET = "\033[0m"
INPUT_CSV = "tickets/brand_matching.csv"
OUTPUT_CSV = "tickets/matching_tagging_IN.csv"
TIMEOUT = 40


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


def extract_brand_name(driver):
    """Brand Name - Returns only the clean brand name text, removing trailing parentheses."""
    try:
        brand_row = WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@title='Brand']/following-sibling::div")
            )
        )
        value_div = brand_row.find_element(By.CSS_SELECTOR, "div.col-value.text-break")
        brand_name_text = value_div.text.strip()
        brand_name_text = re.sub(r"\s*\([^)]*\)$", "", brand_name_text)
        return brand_name_text
    except Exception:
        return "None"


def extract_brand_applier_source(driver):
    """What Applied Brand? (Source) - Extracts the brand badge hover text (title attribute)"""
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


def extract_brand_applier_vheader(driver):
    """What Applied Brand (Version Header) - Returns only the relevant header texts."""
    try:
        selected_row = WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "tr.selected-row"))
        )
        tds = selected_row.find_elements(By.CSS_SELECTOR, "td.collapsed-column")
        header_texts = []
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
            and not t.replace(".", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
            .replace(" ", "")
            .isdigit()
        ]
        return filtered
    except Exception:
        return []


def extract_brand_modern_category(driver):
    """Brand Modern Category"""
    try:
        mod_cat_row = WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@title='Modern Category']/following-sibling::div")
            )
        )
        mod_cat_element = mod_cat_row.find_element(By.TAG_NAME, "span")
        mod_cat_text = mod_cat_element.text.strip()
        return mod_cat_text
    except Exception:
        return "", ""


def extract_poi_name_prior(driver):
    """POI name prior to Brand Application"""
    try:
        prior_name_row = WebDriverWait(driver, TIMEOUT).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@title='Name']/following-sibling::div")
            )
        )
        prior_name_span = prior_name_row.find_element(By.TAG_NAME, "span")
        prior_name_text = prior_name_span.text.strip()
        return prior_name_text
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
                    By.XPATH,  # your chosen field "brand"
                    "//div[contains(@class, 'choices__item') and @data-value='brand']",
                )
            )
        ).click()
    except TimeoutException:
        print(f"{RED}Timeout: 'Brand' filter not found or not clickable.{RESET}")
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


def collect_versions(driver):
    """Return sorted list of (datetime, entry_id)."""
    wait = WebDriverWait(driver, TIMEOUT)
    wait.until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[id^='entry-']"))
    )
    raw = driver.find_elements(By.CSS_SELECTOR, "a[id^='entry-']")
    entries = []
    if len(raw) == 0:
        return []
    for e in raw:
        txt = e.find_element(By.TAG_NAME, "span").text
        dt = datetime.datetime.strptime(txt.rsplit(" ", 1)[0], "%Y-%m-%d %I:%M %p")
        entries.append((dt, e.get_attribute("id")))
    return sorted(entries, key=lambda x: x[0])


def click_version(driver, entry_id):
    wait = WebDriverWait(driver, TIMEOUT)
    wait.until(EC.element_to_be_clickable((By.ID, entry_id))).click()
    wait.until(
        EC.presence_of_element_located((By.XPATH, "//div[@title='Modern Category']"))
    )
    wait.until(EC.presence_of_element_located((By.XPATH, "//div[@title='Hours']")))


def scrape_badge(hyperlink, driver):
    print(f":arrows_counterclockwise: Processing POI={hyperlink}")
    driver.get(hyperlink)
    try:
        click_versions_tab(driver)
        # filtering for brand
        if not choose_field(driver):
            print(f"{RED}Skipping POI due to brand filter.{RESET}")
            return None
        versions = collect_versions(driver)
        # iterate up oldest -> newest
        prior_poi_name = None
        for dt, entry_id in versions:
            click_version(driver, entry_id)
            # brand check
            brand_name = extract_brand_name(driver)
            if brand_name and brand_name != "None":
                # scrape fields
                brand_app_hover = extract_brand_applier_source(driver)
                version_header = extract_brand_applier_vheader(driver)
                brand_modern_category = extract_brand_modern_category(driver)
                # scrape POI name prior to brand being applied
                if prior_poi_name is not None:
                    poi_name_prior = prior_poi_name
                else:
                    poi_name_prior = extract_poi_name_prior(driver)
                print("→ Scraped data for POI")
                return {
                    "Brand Name": brand_name,
                    "What Applied Brand? (Source)": brand_app_hover,
                    "What Applied Brand (Version Header)": version_header,
                    "Brand Modern Category": brand_modern_category,
                    "POI name prior to Brand Application": poi_name_prior,
                }
            # save POI name for next iteration
            prior_poi_name = extract_poi_name_prior(driver)
        # if no brand found, return empty
        print(f"{YELLOW}No Brand data found in any version.{RESET}")
        return {
            "Brand Name": "None",
            "What Applied Brand? (Source)": "",
            "What Applied Brand (Version Header)": [],
            "Brand Modern Category": "",
            "POI name prior to Brand Application": (
                prior_poi_name if prior_poi_name else ""
            ),
        }
    finally:
        pass


if __name__ == "__main__":
    driver = start_driver()
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(
            out_f,
            fieldnames=[
                "Brand Name",
                "What Applied Brand? (Source)",
                "What Applied Brand (Version Header)",
                "Brand Modern Category",
                "POI name prior to Brand Application",
            ],
        )
        writer.writeheader()
        with open(INPUT_CSV, newline="", encoding="utf-8") as in_f:
            reader = csv.DictReader(in_f)
            reader.fieldnames = [
                fn.lstrip("\ufeff").strip() for fn in reader.fieldnames
            ]
            for row in reader:
                hyperlink = row.get("Hyperlink", "").strip()
                if not hyperlink:
                    print(":exclamation: Missing Hyperlink; skipping.")
                    continue
                result = scrape_badge(hyperlink, driver)
                writer.writerow(result)
    driver.quit()
    print(":white_check_mark: All done.")
