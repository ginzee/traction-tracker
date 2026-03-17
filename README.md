# Traction Tracker

A minimal personal goal tracker built with [Streamlit](https://streamlit.io), modelled on the **Rocks** methodology from Gino Wickman's *Traction* (EOS — Entrepreneurial Operating System).

## What it does

| Tab | Purpose |
|-----|---------|
| **Vision** | Capture your 10-year target, 3-year picture, and 1-year goals |
| **Rocks** | Track your 90-day priorities (Rocks) for the current quarter, each marked On Track / Off Track / Complete |
| **To-Dos** | Weekly action items, optionally linked to a Rock |

Data is saved locally to `data/data.json` (gitignored).

## The Rocks Methodology

In EOS, **Rocks** are the 3–7 most important things a person or company must accomplish in the next 90 days. The name comes from the idea that if you don't place the big rocks in the jar first, they won't fit. Rocks sit within a broader hierarchy:

```
10-Year Target
  └── 3-Year Picture
        └── 1-Year Goals
              └── Quarterly Rocks  ← the core unit
                    └── Weekly To-Dos
```

Rocks are reviewed weekly and kept to a simple status: **On Track** or **Off Track**.

## Setup

**Requirements:** Python 3.8+

```bash
# Clone the repo
git clone https://github.com/<your-username>/traction-tracker.git
cd traction-tracker

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501`. Your data is saved automatically to `data/data.json`.

## Project structure

```
traction-tracker/
├── app.py              # Streamlit app
├── requirements.txt
├── .gitignore
├── README.md
└── data/
    ├── .gitkeep        # Keeps the folder tracked in git
    └── data.json       # Your personal data (gitignored)
```
