import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import credentials
from db import already_applied, log_application
from matcher import score_job
from form_filler import fill_and_submit, close_modal

WAIT = 10

# ─── Login ────────────────────────────────────────────
def login_naukri(driver):
    print("\n🔐 Logging into Naukri...")
    driver.get("https://www.naukri.com/nlogin/login")
    wait = WebDriverWait(driver, WAIT)
    try:
        email = wait.until(EC.element_to_be_clickable((By.ID, "usernameField")))
        email.clear()
        email.send_keys(credentials.NAUKRI_EMAIL)
        pwd = driver.find_element(By.ID, "passwordField")
        pwd.clear()
        pwd.send_keys(credentials.NAUKRI_PASSWORD)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(4)
        print("✅ Naukri login successful!")
        return True
    except Exception as e:
        print(f"❌ Naukri login failed: {e}")
        return False


# ─── Build best search URL for a role ────────────────
def _search_url(role: str) -> str:
    """
    Always use the keyword search URL — works for every role.
    The slug-based URL (e.g. /full-stack-developer-jobs) fails for
    roles Naukri doesn't have a preset page for.
    """
    q = role.replace(" ", "%20").replace(".", "-")
    return (
        f"https://www.naukri.com/jobs-in-india"
        f"?k={q}&experience=0&freshness=7"
    )


# ─── Check if job uses Naukri's own apply flow ───────
def _is_naukri_apply(driver) -> bool:
    """
    Returns True if the job uses Naukri's internal apply (not external redirect).
    Checks before clicking Apply to avoid wasting time on external sites.
    """
    try:
        # External apply jobs show a different button label
        ext_signals = [
            "//button[contains(@class,'externalApply')]",
            "//a[contains(@class,'externalApply')]",
            "//*[contains(text(),'Apply on company website')]",
            "//*[contains(text(),'Apply on employer')]",
        ]
        for xp in ext_signals:
            els = driver.find_elements(By.XPATH, xp)
            if els and els[0].is_displayed():
                return False
        return True
    except:
        return True


# ─── Search Naukri ────────────────────────────────────
def search_naukri(driver, role: str, max_jobs: int = 10) -> list:
    print(f"\n🔍 Searching Naukri: {role}")
    url = _search_url(role)
    print(f"  📍 URL: {url[:80]}")
    driver.get(url)
    time.sleep(4)

    jobs = []

    # Try multiple selectors
    card_selectors = [
        "div[class*='srp-jobtuple']",
        "article.jobTuple",
        "div.jobTuple",
        "div[class*='job-card']",
        "div[class*='jobCard']",
    ]

    cards = []
    for sel in card_selectors:
        cards = driver.find_elements(By.CSS_SELECTOR, sel)
        if cards:
            print(f"  Found {len(cards)} cards with: {sel}")
            break

    if not cards:
        # Fallback: link-based scraping
        print("  ⚠️  Trying link fallback...")
        links = driver.find_elements(
            By.XPATH,
            "//a[contains(@href,'naukri.com') and "
            "(contains(@href,'-JD-') or contains(@href,'/job-listings-'))]"
        )
        for lnk in links[:max_jobs]:
            try:
                href  = lnk.get_attribute("href") or ""
                title = lnk.text.strip()
                if href and title and len(title) > 3:
                    jobs.append({"title": title, "company": "",
                                 "url": href, "description": "", "location": ""})
            except:
                pass
        if not jobs:
            print(f"  ⚠️  No cards found for: {role}")
        return jobs[:max_jobs]

    for card in cards[:max_jobs]:
        try:
            title = ""
            href  = ""
            for sel in ["a.title", "a[class*='title']",
                        ".jobTupleHeader a", "h2 a",
                        "a[class*='job-title']"]:
                try:
                    el    = card.find_element(By.CSS_SELECTOR, sel)
                    title = el.text.strip()
                    href  = el.get_attribute("href") or ""
                    if title and href:
                        break
                except:
                    pass

            company = ""
            for sel in ["a.subTitle", "a[class*='comp']",
                        ".companyInfo a", ".comp-name",
                        "a[class*='company']"]:
                try:
                    company = card.find_element(By.CSS_SELECTOR, sel).text.strip()
                    if company:
                        break
                except:
                    pass

            desc = ""
            try:
                desc = card.find_element(
                    By.CSS_SELECTOR,
                    "div[class*='desc'], ul.tags-gt, div[class*='job-description']"
                ).text.strip()
            except:
                pass

            if title and href:
                jobs.append({
                    "title": title, "company": company,
                    "url": href, "description": desc, "location": ""
                })
        except:
            pass

    print(f"  ✅ Collected {len(jobs)} jobs for '{role}'")
    return jobs[:max_jobs]


# ─── Apply to one Naukri job ──────────────────────────
def apply_naukri_job(driver, job: dict, profile: dict) -> bool:
    url   = job["url"]
    title = job["title"]
    wait  = WebDriverWait(driver, WAIT)

    try:
        driver.get(url)
        time.sleep(3)

        # ── Detect external apply BEFORE clicking anything ──
        if not _is_naukri_apply(driver):
            from form_filler import human_handoff
            decision = human_handoff(driver,
                reason="This job applies on the company's own website (not Naukri)",
                context=f"Job: {title} | URL: {url[:60]}"
            )
            if decision == "submitted":
                return True
            else:
                return False

        # ── Find Apply button ──
        apply_btn = None
        apply_xpaths = [
            "//button[normalize-space()='Apply']",
            "//button[normalize-space()='Apply Now']",
            "//button[contains(@class,'apply-button') and not(contains(@class,'external'))]",
            "//button[contains(text(),'Apply') and not(contains(text(),'Applied')) "
            "and not(contains(@class,'external'))]",
        ]
        for xp in apply_xpaths:
            try:
                apply_btn = wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
                break
            except:
                pass

        if not apply_btn:
            print(f"    ⚠️  No Apply button: {title}")
            return False

        apply_btn.click()
        time.sleep(3)

        # If new tab opened check it's not an external site
        if len(driver.window_handles) > 1:
            driver.switch_to.window(driver.window_handles[-1])
            time.sleep(2)
            current = driver.current_url
            if "naukri.com" not in current:
                from form_filler import human_handoff
                print(f"    🌐 Opened external site: {current[:60]}")
                decision = human_handoff(driver,
                    reason="Redirected to company website — bot cannot fill external forms automatically",
                    context=f"External URL: {current[:80]}"
                )
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                return decision == "submitted"

        # Already applied?
        page = driver.page_source.lower()
        if "already applied" in page or "application submitted" in page:
            print(f"    ⚠️  Already applied: {title}")
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
            return False

        success = fill_and_submit(driver, profile)

        if not success:
            page = driver.page_source.lower()
            if "application submitted" in page or "successfully applied" in page:
                success = True
            else:
                close_modal(driver)

        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            time.sleep(1)

        return success

    except Exception as e:
        print(f"    ❌ Error: {e}")
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        return False


# ─── Main Naukri runner ───────────────────────────────
def run_naukri(driver, profile: dict, roles: list,
               threshold: int = 60, max_apply: int = 3):
    if not login_naukri(driver):
        return 0

    total_applied = 0

    for role in roles:
        jobs = search_naukri(driver, role, max_jobs=10)
        if not jobs:
            continue

        applied_this_role = 0

        for job in jobs:
            if applied_this_role >= max_apply:
                break

            url   = job["url"]
            title = job["title"]

            if already_applied(url):
                print(f"  ⏭️  Skip (already applied): {title}")
                continue

            score = score_job(profile, title=title,
                              description=job.get("description", ""))
            print(f"  📊 Score {score}% — {title} @ {job.get('company','?')}")

            if score < threshold:
                print(f"  ⛔ Below threshold ({threshold}%), skipping")
                log_application(url, title, job.get("company", ""),
                                "Naukri", score, "skipped")
                continue

            print(f"  🚀 Applying: {title}")
            success = apply_naukri_job(driver, job, profile)

            status = "applied" if success else "failed"
            log_application(url, title, job.get("company", ""),
                            "Naukri", score, status)

            if success:
                print(f"  ✅ Applied! [{applied_this_role+1}/{max_apply}]")
                applied_this_role += 1
                total_applied += 1
            else:
                print(f"  ❌ Apply failed: {title}")

            time.sleep(2)

        print(f"  📌 Naukri '{role}': applied to {applied_this_role} jobs")

    return total_applied
