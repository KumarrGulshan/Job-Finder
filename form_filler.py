import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import StaleElementReferenceException

# ─── Find modal — returns (element, is_modal) ─────────
def get_modal(driver):
    for sel in [
        "div.jobs-easy-apply-modal",
        "div[data-test-modal]",
        "div.artdeco-modal",
    ]:
        try:
            el = driver.find_element(By.CSS_SELECTOR, sel)
            if el.is_displayed():
                return el
        except:
            pass
    return None  # no modal found

def find_elements(driver, xpath: str):
    """Search inside modal if found, otherwise whole page."""
    modal = get_modal(driver)
    try:
        if modal:
            # scoped search inside modal
            return modal.find_elements(By.XPATH, f".{xpath}")
        else:
            return driver.find_elements(By.XPATH, xpath)
    except:
        return []

def find_element(driver, xpath: str):
    modal = get_modal(driver)
    try:
        if modal:
            return modal.find_element(By.XPATH, f".{xpath}")
        else:
            return driver.find_element(By.XPATH, xpath)
    except:
        return None

# ─── Get label for an input ───────────────────────────
def get_label(driver, element) -> str:
    try:
        el_id = element.get_attribute("id")
        if el_id:
            label = driver.find_element(By.XPATH, f"//label[@for='{el_id}']")
            return label.text.lower().strip()
    except: pass
    try:
        label = element.find_element(By.XPATH,
            "./ancestor::div[1]//label | ./ancestor::div[2]//label")
        return label.text.lower().strip()
    except: pass
    try:
        return (element.get_attribute("placeholder") or "").lower().strip()
    except: pass
    return ""

# ─── Smart answer from profile ────────────────────────
def smart_answer(label: str, profile: dict) -> str:
    l = label.lower()
    if any(k in l for k in ["phone", "mobile", "contact"]):
        return profile.get("phone", "")
    if any(k in l for k in ["email", "mail"]):
        return profile.get("email", "")
    if "first name" in l or "firstname" in l:
        return profile.get("name", "").split()[0]
    if "last name" in l or "lastname" in l or "surname" in l:
        parts = profile.get("name", "").split()
        return parts[-1] if len(parts) > 1 else ""
    if "full name" in l or (l.strip() == "name"):
        return profile.get("name", "")
    if any(k in l for k in ["city", "location", "current location"]):
        return profile.get("city", "")
    if any(k in l for k in ["state", "province"]):
        return profile.get("state", "")
    if any(k in l for k in ["notice", "joining"]):
        return profile.get("notice_period", "Immediate")
    if any(k in l for k in ["current salary", "current ctc"]):
        return str(profile.get("current_salary", "0"))
    if any(k in l for k in ["expected salary", "expected ctc", "desired"]):
        return str(profile.get("expected_salary", "400000"))
    if any(k in l for k in ["year", "experience", "exp"]):
        return str(profile.get("experience_years", "0"))
    if any(k in l for k in ["college", "university", "institution"]):
        return profile.get("education", {}).get("college", "")
    if any(k in l for k in ["degree", "qualification"]):
        return profile.get("education", {}).get("degree", "B.Tech")
    if any(k in l for k in ["branch", "specialization"]):
        return profile.get("education", {}).get("branch", "Computer Science")
    if any(k in l for k in ["passing year", "graduation year"]):
        return profile.get("education", {}).get("year_of_passing", "2026")
    if "linkedin" in l:
        return profile.get("linkedin_url", "")
    if "github" in l or "portfolio" in l:
        return profile.get("github_url", "")
    if any(k in l for k in ["pincode", "zip", "postal"]):
        return "825001"
    return ""

# ─── Fill text inputs ─────────────────────────────────
def fill_inputs(driver, profile: dict):
    inputs = find_elements(driver,
        "//input[@type='text' or @type='number' or @type='tel' or @type='email']")
    for inp in inputs:
        try:
            if not inp.is_displayed() or not inp.is_enabled():
                continue
            if (inp.get_attribute("value") or "").strip():
                continue
            label  = get_label(driver, inp)
            answer = smart_answer(label, profile)
            if answer:
                inp.clear()
                inp.send_keys(answer)
                time.sleep(0.2)
        except StaleElementReferenceException:
            pass
        except: pass

# ─── Fill textareas ───────────────────────────────────
def fill_textareas(driver, profile: dict):
    areas = find_elements(driver, "//textarea")
    for area in areas:
        try:
            if not area.is_displayed(): continue
            if (area.get_attribute("value") or area.text or "").strip(): continue
            area.send_keys(profile.get("summary",
                "Motivated fresher with strong Java, Spring Boot, Flutter and React skills."))
            time.sleep(0.2)
        except: pass

# ─── Fill dropdowns ───────────────────────────────────
def fill_selects(driver, profile: dict):
    selects = find_elements(driver, "//select")
    for sel_el in selects:
        try:
            if not sel_el.is_displayed(): continue
            s = Select(sel_el)
            current = s.first_selected_option.text.strip().lower()
            if current in ["", "select", "select an option",
                           "-- select --", "choose", "please select"]:
                label   = get_label(driver, sel_el)
                options = [o.text.lower() for o in s.options]
                if any(k in label for k in ["notice", "joining"]):
                    for i, opt in enumerate(options):
                        if "immediate" in opt or opt.startswith("0"):
                            s.select_by_index(i); break
                    else:
                        s.select_by_index(1)
                elif any(k in label for k in ["experience", "year"]):
                    for i, opt in enumerate(options):
                        if "fresher" in opt or opt.startswith("0") or "less" in opt:
                            s.select_by_index(i); break
                    else:
                        s.select_by_index(1)
                else:
                    s.select_by_index(1)
        except: pass

# ─── Fill radio buttons ───────────────────────────────
def fill_radios(driver):
    radios   = find_elements(driver, "//input[@type='radio']")
    answered = set()
    for radio in radios:
        try:
            if not radio.is_displayed(): continue
            name = radio.get_attribute("name") or radio.get_attribute("id") or ""
            if name in answered: continue
            label = get_label(driver, radio)
            if "yes" in label:
                driver.execute_script("arguments[0].click();", radio)
                answered.add(name)
            elif name not in answered:
                driver.execute_script("arguments[0].click();", radio)
                answered.add(name)
        except: pass

# ─── Fill checkboxes ──────────────────────────────────
def fill_checkboxes(driver):
    boxes = find_elements(driver, "//input[@type='checkbox']")
    for cb in boxes:
        try:
            if cb.is_displayed() and not cb.is_selected():
                driver.execute_script("arguments[0].click();", cb)
        except: pass

# ─── Click Next / Submit ──────────────────────────────
def click_next_or_submit(driver) -> str:
    """
    Searches modal first, then whole page.
    Returns: 'submitted' | 'next' | 'stuck'
    """
    # Get all visible buttons — modal-scoped if possible
    modal = get_modal(driver)
    try:
        if modal:
            btns = modal.find_elements(By.TAG_NAME, "button")
        else:
            btns = driver.find_elements(By.TAG_NAME, "button")
    except:
        return "stuck"

    submit_btn = None
    next_btn   = None

    for btn in btns:
        try:
            if not btn.is_displayed():
                continue
            txt  = (btn.text or "").strip().lower()
            aria = (btn.get_attribute("aria-label") or "").strip().lower()

            # Submit — highest priority
            if "submit" in txt or "submit" in aria:
                submit_btn = btn
                break  # found submit — stop looking

            # Next / Continue / Review
            if next_btn is None:
                if any(k in txt  for k in ["next", "continue", "review"]):
                    next_btn = btn
                if any(k in aria for k in ["next", "continue", "review",
                                            "next step", "your application"]):
                    next_btn = btn
        except:
            pass

    if submit_btn:
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
            time.sleep(0.3)
            submit_btn.click()
            return "submitted"
        except: pass

    if next_btn:
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
            time.sleep(0.3)
            next_btn.click()
            return "next"
        except: pass

    return "stuck"

# ─── Main fill + submit loop ──────────────────────────
def fill_and_submit(driver, profile: dict, max_steps: int = 8) -> bool:
    for step in range(1, max_steps + 1):
        time.sleep(2)

        # Debug — show all visible buttons this step
        try:
            modal = get_modal(driver)
            src   = modal if modal else driver
            btns  = src.find_elements(By.TAG_NAME, "button")
            visible = [
                (b.text.strip(), b.get_attribute("aria-label"))
                for b in btns
                if b.is_displayed() and (b.text.strip() or b.get_attribute("aria-label"))
            ]
            if visible:
                print(f"    [step {step}] buttons: {visible[:6]}")
        except: pass

        fill_inputs(driver, profile)
        fill_textareas(driver, profile)
        fill_selects(driver, profile)
        fill_radios(driver)

        result = click_next_or_submit(driver)

        if result == "submitted":
            time.sleep(2)
            print(f"    ✅ Submitted on step {step}!")
            # Dismiss confirmation
            for xp in ["//button[@aria-label='Dismiss']",
                        "//button[contains(text(),'Done')]",
                        "//button[contains(text(),'Close')]"]:
                try:
                    driver.find_element(By.XPATH, xp).click()
                    break
                except: pass
            return True

        elif result == "next":
            print(f"    ➡️  Step {step} → next")
            continue

        else:
            print(f"    ⚠️  Step {step}: stuck — handing off to you")
            # Show what fields are empty on this step
            try:
                inputs = find_elements(driver,
                    "//input[@type='text' or @type='number' or @type='tel']")
                empty = []
                for inp in inputs:
                    try:
                        if inp.is_displayed() and not (inp.get_attribute('value') or '').strip():
                            ph = inp.get_attribute('placeholder') or inp.get_attribute('id') or 'unknown'
                            empty.append(ph)
                    except: pass
                if empty:
                    print(f"    📋 Empty fields: {empty}")
            except: pass

            decision = human_handoff(driver,
                reason=f"Bot stuck on step {step} — could not find Next/Submit button or missing info",
                context=f"Step {step} of the application form"
            )
            if decision == "submitted":
                return True
            elif decision == "skip":
                return False
            elif decision == "bot_submit":
                result2 = click_next_or_submit(driver)
                if result2 == "submitted":
                    print(f"    ✅ Submitted!")
                    return True
                else:
                    print(f"    ❌ Still could not submit — skipping")
                    return False

    return False

# ─── Close / discard modal ────────────────────────────
def close_modal(driver):
    for xp in ["//button[@aria-label='Dismiss']"]:
        try:
            driver.find_element(By.XPATH, xp).click()
            time.sleep(1)
            break
        except: pass
    for xp in ["//button[contains(text(),'Discard')]",
                "//button[@data-control-name='discard_application_confirm_btn']"]:
        try:
            driver.find_element(By.XPATH, xp).click()
            time.sleep(1)
            break
        except: pass

# ─── Human Handoff ────────────────────────────────────
def human_handoff(driver, reason: str, context: str = "") -> str:
    """
    Pauses the bot and hands control to you.
    You fill/click whatever the bot couldn't.
    Returns: 'done' | 'skip' | 'submitted'
    """
    print("\n" + "🟡"*25)
    print("  🤚 HUMAN NEEDED")
    print("🟡"*25)
    print(f"\n  Reason  : {reason}")
    if context:
        print(f"  Context : {context}")
    print(f"\n  Browser : {driver.current_url[:80]}")

    # Show unfilled inputs so you know what to fill
    try:
        inputs = driver.find_elements(By.XPATH,
            "//input[@type='text' or @type='number' or @type='tel' or @type='email']")
        empty = []
        for inp in inputs:
            try:
                if inp.is_displayed() and not (inp.get_attribute("value") or "").strip():
                    ph = inp.get_attribute("placeholder") or inp.get_attribute("id") or "?"
                    empty.append(ph)
            except: pass
        if empty:
            print(f"\n  ⚠️  Unfilled fields : {empty}")
    except: pass

    # Show visible buttons so you know what to click next
    try:
        btns = driver.find_elements(By.TAG_NAME, "button")
        visible_btns = [
            b.text.strip() or b.get_attribute("aria-label")
            for b in btns
            if b.is_displayed() and (b.text.strip() or b.get_attribute("aria-label"))
        ]
        if visible_btns:
            print(f"  🖱️  Visible buttons : {visible_btns[:8]}")
    except: pass

    print("\n  What would you like to do?")
    print("  [d] I filled and submitted it myself  → mark as done")
    print("  [s] Skip this job                     → move to next")
    print("  [b] Bot should try to submit now      → bot clicks submit")
    print()

    while True:
        choice = input("  Your choice (d/s/b): ").strip().lower()
        if choice == "d":
            print("  ✅ Marked as submitted by you\n")
            return "submitted"
        elif choice == "s":
            print("  ⏭️  Skipping this job\n")
            return "skip"
        elif choice == "b":
            print("  🤖 Bot will try to click Submit now...\n")
            return "bot_submit"
        else:
            print("  Please enter d, s, or b")
