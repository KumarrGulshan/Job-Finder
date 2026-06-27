import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from resume_parser import get_profile
from db import init_db, print_stats
from naukri import run_naukri
from linkedin import run_linkedin

# ─── Config ───────────────────────────────────────────
ROLES = [
    "Full Stack Developer",
    "Java Developer",
    "Flutter Developer",
    "React.js Developer",
    "Software Developer",
]

SCORE_THRESHOLD    = 60
MAX_APPLY_PER_ROLE = 3

# ─── Fresh Chrome for each platform ───────────────────
def get_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    try:
        service = Service(ChromeDriverManager().install())
        driver  = webdriver.Chrome(service=service, options=options)
    except Exception:
        driver  = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"}
    )
    driver.set_page_load_timeout(60)   # don't hang forever on slow pages
    return driver


def quit_driver(driver):
    try:
        driver.quit()
    except Exception:
        pass


# ─── Main ─────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  🤖 Job Application Bot — Starting")
    print("=" * 55)

    profile = get_profile()
    print(f"\n📄 Profile: {profile['name']}")
    print(f"  Skills : {', '.join(profile.get('skills', []))}")
    print(f"  Target : {len(ROLES)} roles × 2 platforms")
    print(f"  Filter : score ≥ {SCORE_THRESHOLD}%")

    init_db()

    naukri_total   = 0
    linkedin_total = 0

    # ══ NAUKRI — its own browser session ══════════════
    print("\n" + "─" * 55)
    print("  NAUKRI")
    print("─" * 55)
    print("🌐 Starting Chrome for Naukri...")
    driver_naukri = get_driver()
    try:
        naukri_total = run_naukri(
            driver_naukri, profile, ROLES,
            threshold=SCORE_THRESHOLD,
            max_apply=MAX_APPLY_PER_ROLE
        )
    except KeyboardInterrupt:
        print("\n⛔ Stopped by user")
        quit_driver(driver_naukri)
        return
    except Exception as e:
        print(f"\n❌ Naukri error: {e}")
    finally:
        print("\n🔒 Closing Naukri browser...")
        quit_driver(driver_naukri)

    # Cool-down between platforms
    print("\n⏸️  Waiting 20s before opening LinkedIn...")
    for i in [20, 15, 10, 5]:
        print(f"  {i}s...")
        time.sleep(5)

    # ══ LINKEDIN — fresh browser session ══════════════
    print("\n" + "─" * 55)
    print("  LINKEDIN")
    print("─" * 55)
    print("🌐 Starting fresh Chrome for LinkedIn...")
    driver_linkedin = get_driver()
    try:
        linkedin_total = run_linkedin(
            driver_linkedin, profile, ROLES,
            threshold=SCORE_THRESHOLD,
            max_apply=MAX_APPLY_PER_ROLE
        )
    except KeyboardInterrupt:
        print("\n⛔ Stopped by user")
    except Exception as e:
        print(f"\n❌ LinkedIn error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n🔒 Closing LinkedIn browser...")
        quit_driver(driver_linkedin)

    # ══ Summary ═══════════════════════════════════════
    print("\n" + "=" * 55)
    print("  📊 SESSION SUMMARY")
    print("=" * 55)
    print(f"  Naukri applied   : {naukri_total} jobs")
    print(f"  LinkedIn applied : {linkedin_total} jobs")
    print(f"  Total this run   : {naukri_total + linkedin_total} jobs")
    print_stats()
    print("✅ All done!")


if __name__ == "__main__":
    main()
