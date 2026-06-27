import os
import json
import anthropic
import credentials
from pdfminer.high_level import extract_text

PROFILE_CACHE = "profile.json"

# ─── Extract raw text from PDF ────────────────────────
def extract_resume_text(pdf_path: str) -> str:
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(
            f"Resume not found at '{pdf_path}'\n"
            f"Put your resume PDF in the job/ folder and name it: resume.pdf"
        )
    print(f"📄 Reading resume: {pdf_path}")
    text = extract_text(pdf_path)
    if not text.strip():
        raise ValueError("Could not extract text from PDF. Is it a scanned image?")
    return text

# ─── Send to Claude, get structured JSON back ─────────
def parse_with_claude(resume_text: str) -> dict:
    print("🤖 Sending to Claude API for parsing...")
    client = anthropic.Anthropic(api_key=credentials.ANTHROPIC_API_KEY)

    prompt = f"""You are a resume parser. Extract information from the resume below and return ONLY a valid JSON object — no explanation, no markdown, no code fences.

Return exactly this structure (fill every field, use empty string or 0 if not found):
{{
  "name": "",
  "email": "",
  "phone": "",
  "city": "",
  "state": "",
  "linkedin_url": "",
  "github_url": "",
  "experience_years": 0,
  "current_role": "",
  "education": {{
    "degree": "",
    "branch": "",
    "college": "",
    "year_of_passing": ""
  }},
  "skills": [],
  "frameworks": [],
  "languages": [],
  "databases": [],
  "tools": [],
  "projects": [
    {{
      "name": "",
      "description": "",
      "tech_stack": []
    }}
  ],
  "certifications": [],
  "notice_period": "Immediate",
  "summary": ""
}}

Resume:
{resume_text}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()

    # Strip markdown fences if model adds them anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)

# ─── Merge with credentials.py overrides ──────────────
def merge_with_credentials(profile: dict) -> dict:
    """
    credentials.py values win over resume-parsed values.
    This ensures phone/city/notice period are always correct.
    """
    overrides = {
        "name":           credentials.YOUR_NAME,
        "phone":          credentials.YOUR_PHONE,
        "email":          credentials.YOUR_EMAIL,
        "city":           credentials.YOUR_CITY,
        "state":          credentials.YOUR_STATE,
        "notice_period":  credentials.YOUR_NOTICE,
        "experience_years": credentials.EXPERIENCE_YEARS,
        "expected_salary":  credentials.EXPECTED_SALARY,
        "current_salary":   credentials.CURRENT_SALARY,
        "preferred_cities": credentials.PREFERRED_CITIES,
    }
    profile.update({k: v for k, v in overrides.items() if v not in (None, "", 0, [])})
    return profile

# ─── Main entry point ─────────────────────────────────
def get_profile(force_refresh: bool = False) -> dict:
    if os.path.exists(PROFILE_CACHE) and not force_refresh:
        print(f"✅ Loaded profile from cache ({PROFILE_CACHE})")
        with open(PROFILE_CACHE, "r") as f:
            return json.load(f)

    # ── Fill this manually instead of using Claude API ──
    profile = {
        "name":             credentials.YOUR_NAME,
        "email":            credentials.YOUR_EMAIL,
        "phone":            credentials.YOUR_PHONE,
        "city":             credentials.YOUR_CITY,
        "state":            credentials.YOUR_STATE,
        "experience_years": credentials.EXPERIENCE_YEARS,
        "notice_period":    credentials.YOUR_NOTICE,
        "expected_salary":  credentials.EXPECTED_SALARY,
        "current_salary":   credentials.CURRENT_SALARY,
        "preferred_cities": credentials.PREFERRED_CITIES,

        # ── Edit these to match your actual resume ──
        "skills":      ["Java", "Python", "Dart", "JavaScript"],
        "frameworks":  ["Spring Boot", "Flutter", "React"],
        "databases":   ["MySQL", "PostgreSQL"],
        "tools":       ["Git", "Docker", "Postman"],
        "languages":   ["Java", "Python", "Dart"],
        "education": {
            "degree":          "B.Tech",
            "branch":          "Computer Science",
            "college":         "Your College Name",
            "year_of_passing": "2025"
        },
        "projects": [
            {
                "name":        "Transformer Language Model",
                "description": "Built from scratch using PyTorch",
                "tech_stack":  ["Python", "PyTorch"]
            }
        ],
        "certifications": [],
        "summary": "Final year CS student with backend experience in Spring Boot and Dart, expanding into Flutter and React."
    }

    with open(PROFILE_CACHE, "w") as f:
        json.dump(profile, f, indent=2)

    print(f"✅ Profile saved to {PROFILE_CACHE}")
    return profile


# ─── Run directly to test ─────────────────────────────
if __name__ == "__main__":
    profile = get_profile(force_refresh=True)

    print("\n" + "─" * 40)
    print(f"  Name     : {profile.get('name')}")
    print(f"  Email    : {profile.get('email')}")
    print(f"  Phone    : {profile.get('phone')}")
    print(f"  City     : {profile.get('city')}")
    print(f"  Exp      : {profile.get('experience_years')} years")
    print(f"  Skills   : {', '.join(profile.get('skills', [])[:6])}")
    print(f"  Frameworks: {', '.join(profile.get('frameworks', [])[:5])}")
    print(f"  Projects : {len(profile.get('projects', []))} found")
    print("─" * 40)
    print("\n📁 Full profile saved in profile.json")
