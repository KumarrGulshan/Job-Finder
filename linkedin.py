import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

import credentials
from db import already_applied, log_application
from matcher import score_job, SKILL_WEIGHTS
from form_filler import fill_and_submit, close_modal

WAIT = 10
seen_this_session = set()

# ─── Safe page load ───────────────────────────────────
def safe_get(driver, url: str) -> bool:
    try:
        driver.set_page_load_timeout(35)
        driver.get(url)
        return True
    except TimeoutException:
        try: driver.execute_script("window.stop();")
        except: pass
        return True
    except WebDriverException as e:
        print(f"    ❌ Page error: {str(e)[:60]}")
        return False

# ─── Login ────────────────────────────────────────────
def login_linkedin(driver):
    print("\n🔐 Logging into LinkedIn...")
    safe_get(driver, "https://www.linkedin.com/login")
    time.sleep(4)
    try:
        wait  = WebDriverWait(driver, 15)
        email = wait.until(EC.presence_of_element_located((By.ID, "username")))
        time.sleep(1)
        email.clear()
        email.send_keys(credentials.LINKEDIN_EMAIL)
        time.sleep(0.5)
        pwd = driver.find_element(By.ID, "password")
        pwd.clear()
        pwd.send_keys(credentials.LINKEDIN_PASSWORD)
        time.sleep(0.5)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(6)
        if "feed" in driver.current_url or "mynetwork" in driver.current_url:
            print("✅ LinkedIn auto-login successful!")
            return True
    except Exception as e:
        print(f"  ⚠️  Auto-login issue: {str(e)[:60]}")

    print("  ⚠️  Please login manually in the browser (OTP/CAPTCHA etc.)")
    input("  ✋ Press Enter ONLY after you can see your LinkedIn feed: ")
    print("✅ LinkedIn login done!")
    return True


# ─── Collect job URLs from search results ─────────────
def search_linkedin(driver, role: str, max_jobs: int = 10) -> list:
    print(f"\n🔍 Searching LinkedIn: {role}")

    # Use geoId=102713980 for India, remove sortBy to get relevance order
    query = role.replace(" ", "%20")
    url   = (
        f"https://www.linkedin.com/jobs/search/"
        f"?keywords={query}&geoId=102713980&f_AL=true&f_E=1%2C2"
        # f_E=1,2 = Internship + Entry level — best for freshers
    )
    safe_get(driver, url)
    time.sleep(6)
    try: driver.execute_script("window.stop();")
    except: pass

    # Scroll to load more cards
    for _ in range(3):
        try:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1.2)
        except: pass

    jobs      = []
    seen_urls = set()

    try:
        links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/jobs/view/']")
    except:
        links = []

    for link in links:
        try:
            href  = (link.get_attribute("href") or "").split("?")[0].strip()
            title = (link.get_attribute("aria-label") or link.text or "").strip()

            if not href or not title or href in seen_urls:
                continue
            if title.isdigit() or "notification" in title.lower():
                continue
            if len(title) < 5 or len(title) > 150:
                continue

            seen_urls.add(href)
            jobs.append({
                "title": title, "company": "",
                "url": href, "description": "", "location": ""
            })
            if len(jobs) >= max_jobs:
                break
        except: pass

    print(f"  ✅ Collected {len(jobs)} jobs for '{role}'")
    return jobs


# ─── Get full job details from job page ───────────────
def get_job_details(driver, url: str) -> tuple:
    """Returns (title, company, description). Waits for content to load."""
    try:
        safe_get(driver, url)
        # Wait for job title to appear — signals page is ready
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1"))
            )
        except:
            pass
        time.sleep(2)
        try: driver.execute_script("window.stop();")
        except: pass

        # Title
        title = ""
        for sel in [
            "h1.top-card-layout__title",
            "h1.t-24.t-bold",
            ".job-details-jobs-unified-top-card__job-title h1",
            "h1.jobs-unified-top-card__job-title",
            "h1"
        ]:
            try:
                title = driver.find_element(By.CSS_SELECTOR, sel).text.strip()
                if title: break
            except: pass

        # Company
        company = ""
        for sel in [
            "a.topcard__org-name-link",
            ".job-details-jobs-unified-top-card__company-name a",
            ".jobs-unified-top-card__company-name a",
            ".topcard__flavor--black-link",
        ]:
            try:
                company = driver.find_element(By.CSS_SELECTOR, sel).text.strip()
                if company: break
            except: pass

        # Try "Show more" to expand description
        try:
            show_more = driver.find_element(By.XPATH,
                "//button[contains(@class,'show-more') or "
                "contains(text(),'Show more') or "
                "contains(text(),'See more')]")
            driver.execute_script("arguments[0].click();", show_more)
            time.sleep(1)
        except: pass

        # Description
        desc = ""
        for sel in [
            "div.jobs-description__content",
            "div.show-more-less-html__markup",
            "div[class*='description__text']",
            "div.jobs-box__html-content",
            "section.job-details",
        ]:
            try:
                desc = driver.find_element(By.CSS_SELECTOR, sel).text.strip()
                if len(desc) > 50:
                    break
            except: pass

        return title, company, desc[:1500]

    except Exception as e:
        return "", "", ""


# ─── Score job with title fallback ────────────────────
def smart_score(profile, title, company, desc) -> int:
    """
    If description is empty, score based on title keywords only
    but with a boost so title-only matches aren't penalised too hard.
    """
    if desc:
        return score_job(profile, title=title, description=desc)
    else:
        # Score on title only — use a lower MAX to compensate
        from matcher import SKILL_WEIGHTS, FRESHER_BONUS, PENALTY_KEYWORDS
        import re
        text = title.lower()
        raw  = 0
        profile_kw = set()
        for field in ("skills", "frameworks", "databases", "tools", "languages"):
            for item in profile.get(field, []):
                kw = item.lower().strip()
                profile_kw.add(kw)
                if kw == "react": profile_kw.update(["react.js","reactjs"])
                if kw == "spring boot": profile_kw.add("spring")

        for kw, w in SKILL_WEIGHTS.items():
            if kw in text and kw in profile_kw:
                raw += w
        for kw, p in PENALTY_KEYWORDS.items():
            if kw in text: raw += p
        if profile.get("experience_years", 0) == 0:
            for kw, b in FRESHER_BONUS.items():
                if kw in text: raw += b; break

        return max(0, min(100, int((raw / 20) * 100)))


# ─── Apply to one job ─────────────────────────────────
def apply_linkedin_job(driver, job: dict, profile: dict) -> bool:
    url   = job["url"]
    title = job["title"]

    try:
        safe_get(driver, url)
        # Wait for page to be interactive
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
        except: pass
        time.sleep(3)

        # Already applied?
        try:
            badge = driver.find_element(By.XPATH,
                "//*[contains(text(),'Applied') and "
                "not(contains(text(),'Easy Apply'))]")
            if badge.is_displayed():
                print(f"    ⚠️  Already applied: {title}")
                return False
        except: pass

        # Find Easy Apply button
        easy_apply_btn = None
        for xp in [
            "//button[@aria-label[contains(.,'Easy Apply')]]",
            "//button[normalize-space()='Easy Apply']",
            "//button[contains(.,'Easy Apply')]",
        ]:
            try:
                easy_apply_btn = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable((By.XPATH, xp)))
                break
            except: pass

        if not easy_apply_btn:
            print(f"    ⚠️  No Easy Apply button: {title}")
            return False

        driver.execute_script("arguments[0].scrollIntoView(true);", easy_apply_btn)
        time.sleep(0.5)
        easy_apply_btn.click()
        time.sleep(3)

        # Wait for modal content
        try:
            WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR,
                    "div.jobs-easy-apply-modal button, "
                    "div.artdeco-modal button"
                ))
            )
        except: pass
        time.sleep(1)

        # Show modal buttons for debugging
        try:
            modal_btns = driver.find_elements(By.XPATH,
                "//div[contains(@class,'easy-apply-modal') or "
                "contains(@class,'artdeco-modal')]//button")
            visible = [(b.text.strip(), b.get_attribute("aria-label"))
                       for b in modal_btns
                       if b.is_displayed() and (b.text.strip() or b.get_attribute("aria-label"))]
            if visible:
                print(f"    Modal buttons: {visible[:6]}")
        except: pass

        print(f"    📋 Filling form: {title}")
        success = fill_and_submit(driver, profile)
        if not success:
            close_modal(driver)
        return success

    except TimeoutException:
        print(f"    ⏱️  Timeout — skipping: {title}")
        try: close_modal(driver)
        except: pass
        return False
    except Exception as e:
        print(f"    ❌ Error: {str(e)[:80]}")
        try: close_modal(driver)
        except: pass
        return False


# ─── Main runner ──────────────────────────────────────
def run_linkedin(driver, profile: dict, roles: list,
                 threshold: int = 60, max_apply: int = 3):
    global seen_this_session
    seen_this_session = set()

    if not login_linkedin(driver):
        return 0

    print("  🔄 Verifying LinkedIn session...")
    safe_get(driver, "https://www.linkedin.com/feed/")
    time.sleep(3)
    if "linkedin.com" not in driver.current_url:
        print("  ❌ LinkedIn session invalid")
        return 0
    print("  ✅ Session verified\n")

    total_applied = 0

    for role in roles:
        jobs = search_linkedin(driver, role, max_jobs=10)
        if not jobs:
            print(f"  ⚠️  No jobs found for: {role}")
            continue

        applied_this_role = 0

        for job in jobs:
            if applied_this_role >= max_apply:
                break

            url   = job["url"]
            title = job["title"]

            if already_applied(url) or url in seen_this_session:
                print(f"  ⏭️  Skip (seen): {title[:50]}")
                continue
            seen_this_session.add(url)

            # Fetch full details
            d_title, d_company, desc = get_job_details(driver, url)
            if d_title:   job["title"]   = d_title;   title     = d_title
            if d_company: job["company"] = d_company
            job["description"] = desc

            score = smart_score(profile, title, job.get("company",""), desc)
            co    = job.get("company","?") or "?"
            print(f"  📊 Score {score}% — {title[:45]} @ {co[:20]}")

            if score < threshold:
                print(f"  ⛔ Below threshold ({threshold}%), skipping")
                log_application(url, title, job.get("company",""),
                                "LinkedIn", score, "skipped")
                continue

            print(f"  🚀 Applying: {title[:50]}")
            success = apply_linkedin_job(driver, job, profile)

            status = "applied" if success else "failed"
            log_application(url, title, job.get("company",""),
                            "LinkedIn", score, status)

            if success:
                print(f"  ✅ Applied! [{applied_this_role+1}/{max_apply}]")
                applied_this_role += 1
                total_applied += 1
            else:
                print(f"  ❌ Apply failed: {title[:50]}")

            time.sleep(2)

        print(f"  📌 LinkedIn '{role}': applied to {applied_this_role} jobs")
        time.sleep(3)  # small pause between roles

    return total_applied
