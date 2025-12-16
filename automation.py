import argparse
import sys
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Parse args
parser = argparse.ArgumentParser(description="Instagram Automation for Sheinverse")
parser.add_argument("--user", required=True, help="Instagram username/email")
parser.add_argument("--pass", required=True, help="Instagram password")
parser.add_argument("--output", default="output.txt", help="Log output file")
args = parser.parse_args()

username = args.user
password = args.pass
log_file = args.output

print(f"🚀 Starting automation for {username}...", file=sys.stderr)
with open(log_file, "a") as f:
    f.write(f"Starting for {username} at {time.ctime()}\n")

# ADB check (for Android/Termux)
os.system("adb devices > /dev/null 2>&1")
print("ADB checked (assuming device connected)...", file=sys.stderr)

# Consent URL (from your script)
consent_url = "https://www.instagram.com/consent/?flow=ig_biz_login_oauth&params_json=%7B%22client_id%22%3A%22713904474873404%22%2C%22redirect_uri%22%3A%22https%3A%5C%2F%5C%2Fsheinverse.galleri5.com%5C%2Finstagram%22%2C%22response_type%22%3A%22code%22%2C%22state%22%3Anull%2C%22scope%22%3A%22instagram_business_basic%22%2C%22logger_id%22%3A%2284155d6f-26ca-484b-a2b2-cf3b579c1fc7%22%2C%22app_id%22%3A%22713904474873404%22%2C%22platform_app_id%22%3A%22713904474873404%22%7D&source=oauth_permissions_page_www"

target_prefix = "https://sheinverse.galleri5.com/instagram"

# Chrome options for Android/Headless
options = Options()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_experimental_option("androidPackage", "com.android.chrome")  # For Android
options.add_argument("--headless")  # Hidden mode for bot
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")

try:
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 30)
    print("Browser launched!", file=sys.stderr)

    def log(msg):
        print(msg, file=sys.stderr)
        with open(log_file, "a") as f:
            f.write(msg + "\n")

    def login_to_instagram():
        log("🔑 Logging into Instagram...")
        driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(5)

        try:
            username_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))
            username_field.clear()
            username_field.send_keys(username)

            password_field = driver.find_element(By.NAME, "password")
            password_field.clear()
            password_field.send_keys(password)

            login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
            login_button.click()

            time.sleep(10)

            # Handle popups
            try:
                save_info = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now')]")))
                save_info.click()
                time.sleep(2)
            except TimeoutException:
                pass

            try:
                not_now = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Not Now')]")))
                not_now.click()
                time.sleep(2)
            except TimeoutException:
                pass

            log("✅ Login successful!")
            return True
        except Exception as e:
            log(f"❌ Login error: {str(e)}")
            return False

    def switch_to_professional_creator():
        log("🔄 Switching to Professional Creator...")
        try:
            # Go to profile
            driver.get(f"https://www.instagram.com/{username}/")
            time.sleep(5)

            # Menu button (3 dots)
            menu_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@aria-label='Options'] | //svg[@aria-label='More options']")))
            menu_button.click()
            time.sleep(3)

            # Settings
            settings_link = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[contains(@href, 'settings')] | //div[contains(text(), 'Settings')]")))
            settings_link.click()
            time.sleep(3)

            # Account type
            account_type_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Account type') or contains(@href, 'account_type')]")
            account_type_link.click()
            time.sleep(3)

            # Switch to professional
            switch_pro_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Switch to professional')] | //button[contains(text(), 'Switch')]")))
            switch_pro_button.click()
            time.sleep(3)

            # Choose Creator
            creator_option = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Creator')]")))
            creator_option.click()
            time.sleep(3)

            # Category (first one)
            try:
                category = driver.find_element(By.XPATH, "//div[@role='button'][1]")
                category.click()
                time.sleep(2)
                continue_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Continue') or contains(text(), 'Next')]")
                continue_btn.click()
                time.sleep(3)
            except NoSuchElementException:
                log("Category skip (already set?)")

            # Done
            try:
                done_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Done')]")
                done_btn.click()
            except NoSuchElementException:
                pass

            log("✅ Switched to Professional Creator!")
            return True
        except Exception as e:
            log(f"❌ Switch error: {str(e)}")
            return False

    def handle_consent_and_get_redirect():
        log("🔗 Handling consent & redirect...")
        driver.get(consent_url)
        time.sleep(5)

        try:
            allow_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Allow')]")))
            allow_button.click()
            time.sleep(10)

            current_url = driver.current_url
            log(f"📄 URL after allow: {current_url}")

            if target_prefix in current_url:
                log(f"✅ Success! Sheinverse URL: {current_url}")
                with open(log_file, "a") as f:
                    f.write(f"FINAL_URL: {current_url}\n")
                return current_url
            else:
                log("❌ Redirect failed — no sheinverse URL found.")
                return None
        except Exception as e:
            log(f"❌ Consent error: {str(e)}")
            return None

    # Main retry loop (3 attempts)
    max_retries = 3
    result = None
    for attempt in range(max_retries):
        log(f"🔄 Attempt {attempt + 1}/{max_retries}")
        time.sleep(3)

        if login_to_instagram():
            if switch_to_professional_creator():
                result = handle_consent_and_get_redirect()
                if result:
                    break
            time.sleep(5)
        else:
            log("Login failed, retrying...")

    if result:
        log(f"🎉 FINAL SUCCESS URL: {result}")
    else:
        log("💥 All retries failed. Check creds or try manually.")

except Exception as e:
    log(f"🚨 Global error: {str(e)}")
finally:
    time.sleep(10)  # Keep browser open briefly
    driver.quit()
    log("Browser closed.")
