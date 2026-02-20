# Autonomous System Guide
## How to Build a Self-Running GitHub Organism (Free Forever)
*By Meeko Mycelium — fork this, share this, build yours*

---

This is the complete guide to building what we built. A system that wakes up
every morning, promotes itself, sends emails, applies for grants, monitors its
own health, learns, remembers, and grows — with zero monthly cost and zero
servers. Everything runs on free GitHub infrastructure.

---

## The Core Concept

A GitHub repository is not just code storage. It is:
- A **database** (JSON files committed by Actions)
- A **scheduler** (cron workflows run like clockwork)
- A **brain** (a private repo stores persistent memory across sessions)
- A **web server** (GitHub Pages serves your site for free)
- A **CI/CD system** (Actions run Python, Node, bash — whatever you need)

Chain these together and you have an organism.

---

## What You Need to Start (All Free)

| Tool | What For | Cost |
|------|----------|------|
| GitHub account | Everything | Free |
| OpenRouter | AI brain (routes to GPT-4o-mini, Claude, etc.) | Free tier |
| SerpAPI | Web search | 100 searches/month free |
| Gmail | Email send/receive | Free |
| Coinbase Commerce | Crypto payments | Free (1% fee on transactions) |
| PayPal | Card payments | Free (fees on transactions only) |
| Strike | Lightning payments | Free |

Total monthly cost: **$0.00**

---

## The Architecture (copy this exactly)

```
meeko-nerve-center/          ← central nervous system
├── .github/workflows/
│   ├── mycelium-morning.yml ← runs 9AM daily
│   ├── mycelium-evening.yml ← runs 9PM daily
│   └── email-responder.yml  ← runs every 30 min
├── mycelium/
│   ├── pulse.py             ← promotes on Discord/Mastodon/Dev.to
│   ├── brain_sync.py        ← writes memory to private brain repo
│   ├── morning_briefing.py  ← emails you a daily report
│   ├── grant_outreach.py    ← sends grant applications (once each)
│   ├── email_responder.py   ← reads + replies to Gmail with AI
│   └── verified_charities.json
└── docs/
    └── index.html           ← your public landing page (GitHub Pages)

meeko-brain/                 ← private memory repo
└── MEMORY.md                ← everything the system remembers

mycelium-grants/             ← grant hunter agent
mycelium-money/              ← legal revenue agent  
mycelium-knowledge/          ← knowledge packager agent
```

---

## Step by Step: Build Yours in One Evening

### 1. Create the repos
```
github.com/new
```
Create: `nerve-center`, `brain` (private), `gallery` (or your product)

### 2. Set up GitHub Secrets
In nerve-center → Settings → Secrets → Actions, add:
```
OPENROUTER_KEY      ← openrouter.ai (free)
SERPAPI_KEY         ← serpapi.com (free tier)
GMAIL_APP_PASSWORD  ← myaccount.google.com/security → App Passwords
GITHUB_TOKEN        ← auto-provided by GitHub Actions
```

### 3. Create your morning workflow
`.github/workflows/morning.yml`:
```yaml
on:
  schedule:
    - cron: '0 14 * * *'  # 9AM EST
jobs:
  pulse:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.11'}
      - run: pip install requests
      - run: python mycelium/morning_briefing.py
        env:
          OPENROUTER_KEY: ${{ secrets.OPENROUTER_KEY }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
```

### 4. The AI brain pattern
Every script that needs AI intelligence:
```python
import requests, os

def ask_ai(prompt):
    r = requests.post('https://openrouter.ai/api/v1/chat/completions',
        headers={'Authorization': f'Bearer {os.environ["OPENROUTER_KEY"]}',
                 'Content-Type': 'application/json'},
        json={'model': 'openai/gpt-4o-mini',
              'messages': [{'role': 'user', 'content': prompt}],
              'max_tokens': 500},
        timeout=20)
    return r.json()['choices'][0]['message']['content']
```

### 5. The memory pattern
Persistent memory across sessions (AI has no memory by default):
```python
import json, os, requests

def remember(key, value):
    # Read current memory
    r = requests.get(
        'https://api.github.com/repos/YOUR_USER/brain/contents/MEMORY.json',
        headers={'Authorization': f'Bearer {os.environ["GITHUB_TOKEN"]}'}
    )
    data = json.loads(r.json()['content'].encode())
    data[key] = value
    # Write back
    requests.put(
        'https://api.github.com/repos/YOUR_USER/brain/contents/MEMORY.json',
        headers={'Authorization': f'Bearer {os.environ["GITHUB_TOKEN"]}'},
        json={'message': f'remember: {key}',
              'content': base64.b64encode(json.dumps(data).encode()).decode(),
              'sha': r.json()['sha']}
    )
```

### 6. The email responder pattern
```python
import imaplib, email, smtplib

def check_email():
    with imaplib.IMAP4_SSL('imap.gmail.com') as mail:
        mail.login(GMAIL_USER, GMAIL_PASS)
        mail.select('INBOX')
        _, msgs = mail.search(None, 'UNSEEN')
        for num in msgs[0].split():
            _, data = mail.fetch(num, '(RFC822)')
            msg = email.message_from_bytes(data[0][1])
            sender = msg['from']
            body = get_body(msg)
            reply = ask_ai(f"Reply warmly to this email from {sender}: {body}")
            send_email(sender, 'Re: ' + msg['subject'], reply)
```

---

## What to Sell

Once your system works, the guide IS the product. Package it:

1. **Free version** (this file) — builds trust, drives traffic
2. **$10 PDF guide** — step by step with your exact code on Lemon Squeezy
3. **$50 setup service** — you (or the AI) helps someone else fork and deploy it
4. **$500 custom build** — build a custom mycelium for their specific cause

Revenue from guides → back into the system → system gets better → better guides → more sales.

---

## Adapt This For Any Cause

Change these three things and the whole organism serves a different mission:
1. `GALLERY_URL` → your product/project URL
2. Charity partner → your cause
3. Grant search keywords → your category

Everything else stays the same. The organism doesn't care what it's growing for.
Point it at something good and let it run.

---

*This guide is free. The system is open source. Fork everything.*
*Gaza Rose Gallery: https://meekotharaccoon-cell.github.io/gaza-rose-gallery*
*Code: https://github.com/meekotharaccoon-cell*
