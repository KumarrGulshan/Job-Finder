import re

SKILL_WEIGHTS = {
    "java":          10,
    "python":        10,
    "dart":          10,
    "javascript":    8,
    "sql":           6,
    "c":             4,

    "spring boot":   10,
    "spring":        7,
    "flutter":       10,
    "react":         10,
    "react.js":      10,
    "reactjs":       10,
    "next.js":       6,
    "node":          5,
    "websocket":     6,
    "stomp":         4,
    "jwt":           5,
    "oauth":         4,
    "rest api":      6,
    "restful":       5,
    "microservices": 5,
    "jpa":           4,
    "hibernate":     4,
    "tailwind":      4,
    "android":       5,
    "mobile":        5,

    "mongodb":       6,
    "mysql":         6,
    "postgresql":    5,
    "postgres":      5,
    "redis":         4,

    "git":           4,
    "docker":        5,
    "aws":           5,
    "kafka":         4,
    "pytorch":       5,
    "numpy":         3,
    "pandas":        3,

    "full stack":    8,
    "fullstack":     8,
    "backend":       8,
    "frontend":      6,
    "software developer":  8,
    "software engineer":   8,
    "java developer":      8,
    "flutter developer":   8,
    "react developer":     8,
}

PENALTY_KEYWORDS = {
    "ios native":    -8,
    "swift":         -8,
    "objective-c":   -8,
    "angular":       -5,
    "vue":           -4,
    "php":           -6,
    "ruby":          -6,
    "golang":        -5,
    "devops":        -4,
    "machine learning engineer": -5,
    "c++":           -4,
    "embedded":      -6,
}

FRESHER_BONUS = {
    "fresher":         10,
    "fresh graduate":  10,
    "0-1 year":        10,
    "0-2 year":        8,
    "0 - 1 year":      10,
    "0 - 2 year":      8,
    "entry level":     8,
    "trainee":         6,
    "graduate":        5,
    "campus":          5,
}

MAX_RAW_SCORE = 40

def score_job(profile: dict, title: str, description: str = "") -> int:
    text = f"{title} {description}".lower()
    text = re.sub(r"[^\w\s\.\+\#]", " ", text)

    # Build profile keyword set with aliases
    profile_keywords = set()
    for field in ("skills", "frameworks", "databases", "tools", "languages"):
        for item in profile.get(field, []):
            kw = item.lower().strip()
            profile_keywords.add(kw)
            # Aliases
            if kw == "react.js":
                profile_keywords.update(["react", "reactjs"])
            if kw == "react":
                profile_keywords.update(["react.js", "reactjs"])
            if kw == "spring boot":
                profile_keywords.add("spring")
            if kw == "postgresql":
                profile_keywords.add("postgres")
            if kw == "mongodb":
                profile_keywords.add("mongo")
            if kw == "dart":
                profile_keywords.add("flutter")   # dart = flutter dev
            if kw == "flutter":
                profile_keywords.add("dart")
            if kw == "javascript":
                profile_keywords.update(["js", "typescript"])

    raw = 0

    for keyword, weight in SKILL_WEIGHTS.items():
        if keyword in text and keyword in profile_keywords:
            raw += weight

    for keyword, penalty in PENALTY_KEYWORDS.items():
        if keyword in text:
            raw += penalty

    exp = profile.get("experience_years", 0)
    if exp <= 1:
        for keyword, bonus in FRESHER_BONUS.items():
            if keyword in text:
                raw += bonus
                break

    preferred = [c.lower() for c in profile.get("preferred_cities", [])]
    for city in preferred:
        if city in text:
            raw += 5
            break

    return max(0, min(100, int((raw / MAX_RAW_SCORE) * 100)))


def filter_jobs(profile: dict, jobs: list, threshold: int = 60) -> list:
    scored = []
    for job in jobs:
        s = score_job(profile, job.get("title",""), job.get("description",""))
        job["score"] = s
        if s >= threshold:
            scored.append(job)
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


if __name__ == "__main__":
    import json
    try:
        with open("profile.json") as f:
            profile = json.load(f)
    except FileNotFoundError:
        print("❌ profile.json not found.")
        exit(1)

    test_jobs = [
        {"title": "Java Backend Developer",   "company": "Tech Corp",    "url": "u1", "description": "Java Spring Boot REST API MySQL fresher welcome"},
        {"title": "Flutter Developer",         "company": "StartupXYZ",   "url": "u2", "description": "Flutter Dart Android mobile app 0-1 year experience"},
        {"title": "React.js Frontend Dev",     "company": "WebAgency",    "url": "u3", "description": "React.js JavaScript REST API entry level position"},
        {"title": "Full Stack Developer",      "company": "Product Co",   "url": "u4", "description": "Spring Boot React MongoDB JWT WebSocket fresher apply"},
        {"title": "iOS Swift Developer",       "company": "Apple Partner","url": "u5", "description": "iOS Swift Objective-C 2 years required"},
        {"title": "Software Developer",        "company": "MNC",          "url": "u6", "description": "Java Python SQL Git Docker software developer fresher"},
    ]

    print(f"\n{'─'*58}")
    print(f"  {'Job Title':<32} {'Company':<15} Score")
    print(f"{'─'*58}")
    results = filter_jobs(profile, test_jobs, threshold=0)
    for job in results:
        flag = "✅" if job["score"] >= 60 else "⛔"
        print(f"  {flag} {job['title']:<30} {job['company']:<15} {job['score']}%")
    good = [j for j in results if j["score"] >= 60]
    print(f"{'─'*58}")
    print(f"\n  Will apply to: {len(good)}/{len(test_jobs)} jobs (score ≥ 60%)\n")
