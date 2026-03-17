import streamlit as st
import requests
import re
from datetime import datetime, timezone, timedelta
from tavily import TavilyClient

# ── TIME ───────────────────────────────────────────────────────────
IST = timezone(timedelta(hours=5, minutes=30))
def now_ist():
    return datetime.now(IST)

# ── CONFIG ─────────────────────────────────────────────────────────
SARVAM_URL   = "https://api.sarvam.ai/v1/chat/completions"
SARVAM_MODEL = "sarvam-105b"

st.set_page_config(page_title="GovIT Radar", page_icon="📡", layout="centered")

# ── UI ─────────────────────────────────────────────────────────────
st.markdown("## 📡 GovIT Radar")
st.markdown(f"*{now_ist().strftime('%d %b %Y')}*")

# ── KEYS ───────────────────────────────────────────────────────────
def get_key(k):
    try:
        return st.secrets[k]
    except:
        return ""

# ── LIGHT EXPIRY FILTER ────────────────────────────────────────────
def is_expired(text, today):
    text = text.lower()

    if "last date" not in text and "apply" not in text:
        return False

    patterns = [
        r'(\d{1,2}\s+[a-zA-Z]+\s+\d{4})',
        r'(\d{1,2}/\d{1,2}/\d{4})'
    ]

    for p in patterns:
        matches = re.findall(p, text)
        for d in matches:
            try:
                parsed = datetime.strptime(d, "%d %B %Y")
            except:
                try:
                    parsed = datetime.strptime(d, "%d/%m/%Y")
                except:
                    continue

            if parsed.date() < today.date():
                return True

    return False

# ── SINGLE TAVILY CALL ─────────────────────────────────────────────
def fetch_raw():

    query = f"""
latest govt IT jobs India NIC DRDO ISRO PSU UPSC recruitment apply online {now_ist().year}
"""

    client = TavilyClient(api_key=get_key("TAVILY_API_KEY"))

    res = client.search(
        query=query,
        search_depth="advanced",
        max_results=25,
        days=60
    )

    found = []
    seen = set()

    for r in res.get("results", []):
        url = r.get("url", "")
        title = r.get("title", "")
        content = r.get("content", "")

        if not url or url in seen:
            continue

        if is_expired(title + " " + content, now_ist()):
            continue

        seen.add(url)

        found.append({
            "title": title,
            "url": url,
            "content": content[:300],
        })

    return found

# ── SARVAM CALL ────────────────────────────────────────────────────
def call_sarvam(messages):
    try:
        resp = requests.post(
            SARVAM_URL,
            headers={"api-subscription-key": get_key("SARVAM_API_KEY")},
            json={
                "model": SARVAM_MODEL,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 800
            },
            timeout=30
        )

        data = resp.json()
        choice = data.get("choices", [{}])[0]

        content = choice.get("message", {}).get("content")

        if not content:
            return None, f"Empty (finish_reason={choice.get('finish_reason')})"

        return content.strip(), None

    except Exception as e:
        return None, str(e)

# ── BATCHED REFINE (NO TOKEN LIMIT ISSUE) ───────────────────────────
def refine(raw, today_str):

    def batch(items, size=5):
        for i in range(0, len(items), size):
            yield items[i:i+size]

    outputs = []

    for b in batch(raw, 5):

        text = "\n".join(
            f"{r['title']} | {r['url']}"
            for r in b
        )

        prompt = f"""
Today's date: {today_str}

Extract ACTIVE government IT jobs.

STRICT:
- Only active jobs
- Ignore expired or unclear items

DATA:
{text}

FORMAT:
• [Role] — [Org]
  Apply: [URL]

Max 5 jobs.
"""

        messages = [
            {"role": "system", "content": "Extract jobs."},
            {"role": "user", "content": prompt}
        ]

        out, _ = call_sarvam(messages)

        if out:
            outputs.append(out)

    if not outputs:
        return None, "No valid output"

    return "\n".join(outputs), None

# ── UI ACTION ──────────────────────────────────────────────────────
if st.button("🔍 Fetch Active Openings"):

    try:
        with st.spinner("Fetching jobs..."):
            raw = fetch_raw()

        st.write(f"Fetched {len(raw)} items")

        if not raw:
            st.warning("No jobs found")
            st.stop()

        # Limit input size (important)
        raw = raw[:15]

        with st.spinner("Filtering with AI..."):
            output, error = refine(raw, now_ist().strftime("%d %B %Y"))

        if error:
            st.error(error)

        elif not output:
            st.warning("LLM returned empty. Showing raw results:")
            for r in raw[:5]:
                st.write(f"• {r['title']}")
                st.write(r["url"])

        else:
            st.markdown(output)

    except Exception as e:
        st.error(f"CRASH: {str(e)}")