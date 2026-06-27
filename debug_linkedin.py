"""
Run this standalone to debug LinkedIn step by step.
It will pause at each stage so you can see exactly what's happening.
"""
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

import credentials

def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    try:
        service = Service(ChromeDriverManager().install())
        driver  = webdriver.Chrome(service=service, options=options)
    except:
        driver  = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"}
    )
    driver.set_page_load_timeout(30)
    return driver

driver = get_driver()
wait   = WebDriverWait(driver, 10)

print("\n" + "="*50)
print("  LINKEDIN DEBUG MODE")
print("="*50)

# ── STEP 1: Login ──────────────────────────────────────
print("\n[1] Opening LinkedIn login page...")
try:
    driver.get("https://www.linkedin.com/login")
    time.sleep(3)
    print(f"  URL: {driver.current_url}")
    print(f"  Title: {driver.title}")
except Exception as e:
    print(f"  ❌ Page load error: {e}")

input("\n  👀 Can you see the LinkedIn login page? Press Enter to fill credentials...")

try:
    email = wait.until(EC.element_to_be_clickable((By.ID, "username")))
    email.clear()
    email.send_keys(credentials.LINKEDIN_EMAIL)
    pwd = driver.find_element(By.ID, "password")
    pwd.clear()
    pwd.send_keys(credentials.LINKEDIN_PASSWORD)
    driver.find_element(By.XPATH, "//button[@type='submit']").click()
    print("  ✅ Credentials filled and submitted")
except Exception as e:
    print(f"  ❌ Could not fill login form: {e}")

input("\n  👀 Complete any CAPTCHA/OTP if needed, then press Enter when feed is visible...")
print(f"  Current URL: {driver.current_url}")

# ── STEP 2: Search page ────────────────────────────────
print("\n[2] Loading job search page...")
TEST_ROLE = "Java Developer"
url = f"https://www.linkedin.com/jobs/search/?keywords={TEST_ROLE.replace(' ','%20')}&location=India&f_AL=true"

try:
    driver.get(url)
    time.sleep(6)
    print(f"  URL: {driver.current_url[:80]}")
    print(f"  Title: {driver.title}")
except Exception as e:
    print(f"  ❌ Search page error: {e}")
    try:
        driver.execute_script("window.stop();")
    except:
        pass

# Count job links
links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/jobs/view/']")
print(f"  Job links found: {len(links)}")

# Print first 5 titles
print("  First 5 job titles found:")
for i, l in enumerate(links[:5]):
    title = (l.get_attribute("aria-label") or l.text or "").strip()
    href  = (l.get_attribute("href") or "").split("?")[0]
    print(f"    {i+1}. '{title}' → {href[:60]}")

input("\n  👀 Do you see job cards in the browser? Press Enter to open first job...")

# ── STEP 3: Open one job ───────────────────────────────
good_links = [l for l in links if len((l.get_attribute("aria-label") or l.text or "").strip()) > 5]
if not good_links:
    print("  ❌ No valid job links found — LinkedIn may be blocking")
    input("Press Enter to quit...")
    driver.quit()
    exit()

first_url = good_links[0].get_attribute("href").split("?")[0]
first_title = (good_links[0].get_attribute("aria-label") or good_links[0].text).strip()
print(f"\n[3] Opening job: {first_title}")
print(f"    URL: {first_url}")

try:
    driver.get(first_url)
    time.sleep(4)
    print(f"  URL: {driver.current_url[:80]}")
    print(f"  Title: {driver.title}")
except Exception as e:
    print(f"  ❌ Job page error: {e}")

# Check all buttons on the page
print("\n  All visible buttons on page:")
buttons = driver.find_elements(By.TAG_NAME, "button")
for b in buttons:
    try:
        if b.is_displayed():
            txt   = b.text.strip()
            aria  = b.get_attribute("aria-label") or ""
            cls   = b.get_attribute("class") or ""
            print(f"    • text='{txt}' | aria='{aria}' | class snippet='{cls[:40]}'")
    except:
        pass

input("\n  👀 Do you see the Easy Apply button in the browser? Press Enter to click it...")

# ── STEP 4: Click Easy Apply ───────────────────────────
print("\n[4] Trying to click Easy Apply...")
clicked = False
for xp in [
    "//button[contains(@class,'jobs-apply-button') and contains(.,'Easy Apply')]",
    "//button[@aria-label[contains(.,'Easy Apply')]]",
    "//button[normalize-space()='Easy Apply']",
    "//button[contains(.,'Easy Apply')]",
]:
    try:
        btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, xp)))
        print(f"  ✅ Found button with XPath: {xp[:60]}")
        btn.click()
        clicked = True
        time.sleep(3)
        break
    except:
        print(f"  ✗ Not found: {xp[:60]}")

if not clicked:
    print("  ❌ Could not find Easy Apply button")

# ── STEP 5: Check modal ────────────────────────────────
print("\n[5] Checking modal / form after click...")
time.sleep(2)

print("  All visible buttons now:")
buttons = driver.find_elements(By.TAG_NAME, "button")
for b in buttons:
    try:
        if b.is_displayed():
            txt  = b.text.strip()
            aria = b.get_attribute("aria-label") or ""
            print(f"    • text='{txt}' | aria='{aria}'")
    except:
        pass

print("\n  All visible inputs:")
inputs = driver.find_elements(By.XPATH, "//input[@type='text' or @type='tel' or @type='number' or @type='email']")
for inp in inputs:
    try:
        if inp.is_displayed():
            label_id = inp.get_attribute("id") or ""
            val      = inp.get_attribute("value") or ""
            ph       = inp.get_attribute("placeholder") or ""
            print(f"    • id='{label_id}' | value='{val}' | placeholder='{ph}'")
    except:
        pass

input("\n  👀 What do you see in the browser right now? Press Enter to quit...")
driver.quit()
print("✅ Debug session ended")
