# Job Bot Setup

## Folder structure
```
job/
├── main.py              # run this
├── credentials.py       # your private info — never push to git
├── resume_parser.py
├── db.py
├── matcher.py
├── form_filler.py
├── naukri.py
├── linkedin.py
├── resume.pdf           # your resume — drop it here
├── profile.json         # auto-generated after first run
├── requirements.txt
├── .gitignore
├── data/
│   └── applications.db  # auto-generated SQLite log
└── logs/
    └── run.log          # auto-generated logs
```

## Setup (one time)

```bash
cd ~/Documents/job
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Fill in credentials
Open credentials.py and fill every field marked with "..."

## Add your resume
Copy your resume PDF into this folder and name it resume.pdf

## Run
```bash
python main.py
```
