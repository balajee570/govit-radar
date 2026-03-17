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

# ── UI STYLE ───────────────────────────────────────────────────────
st.markdown("""
<style>
.stApp { background-color: #ffffff; font-family: 'Segoe UI'; }
.result-block {
    background: #f8fafc; border: 1px solid #e2e8f0;
    border-radius: 10px; padding: 20px;
    margin-top: 16px; font-size: 14px;
    line-height: 1.7; white-space: pre-wrap;
}
.ts { font-size: 11px; color: #94a3b8; text-align: right; }
</style>
""", unsafe_allow_html=True)

# ── KEYS ───────────────────────────────────────────────────────────
def get_key(k):
    try:
        return st.secrets[k]
    except:
        return ""

# ── SMART EXPIRY FILTER (LIGHT) ────────────────────────────────────
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

# ── SINGLE TAVILY FETCH ────────────────────────────────────────────
def fetch_raw():

    query = f"""
latest govt IT jobs India NIC DRDO ISRO BPSC UPSC PSU recruitment apply online {now_ist().year}
"""

    client = TavilyClient(api_key=get_key("TAVILY_API_KEY"))

    res = client.search(
        query=query,
        search_depth="advanced",
        max_results=25,   # 🔥 bigger single pull
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
            "content": content[:400],
            "published": r.get("published_date", "unknown"),
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
                "max_tokens": 1200
            },
            timeout=30
        )

        data = resp.json()

        content = data["choices"][0]["message"].get("content")

        if not content:
            return None, "Empty response"

        return content.strip(), None

    except Exception as e:
        return None, str(e)

# ── REFINE (SINGLE CALL) ───────────────────────────────────────────
def refine(raw, today_str):

    text = "\n".join(
        f"Title: {r['title']}\nURL: {r['url']}\nInfo: {r['content']}\n---"
        for r in raw
    )[:5000]  # 🔥 control tokens

    prompt = f"""
Today's date: {today_str}

ONLY include ACTIVE government jobs.

STRICT:
- Must be currently open
- Must have clear job role + org
- Ignore expired or unclear entries

DATA:
{text}

FORMAT:
• [Post] — [Org]
  [Short role]
  Apply: [URL]

No explanation.
"""

    messages = [
        {"role": "system", "content": "Filter active govt jobs."},
        {"role": "user", "content": prompt}
    ]

    return call_sarvam(messages)

# ── UI ─────────────────────────────────────────────────────────────
st.markdown("## 📡 GovIT Radar")
st.markdown(f"*{now_ist().strftime('%d %b %Y')}*")

if st.button("🔍 Fetch Active Openings"):

    with st.spinner("Fetching latest jobs..."):
        raw = fetch_raw()

    st.write(f"Fetched {len(raw)} raw items")

    if not raw:
        st.warning("No jobs found")
        st.stop()

    with st.spinner("Filtering with AI..."):
        output, error = refine(raw, now_ist().strftime("%d %B %Y"))

    if error:
        st.error(error)

    elif not output:
        st.warning("No valid jobs found")

    else:
        st.markdown(f'<div class="result-block">{output}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="ts">{now_ist().strftime("%d %b %Y %I:%M %p")} IST</div>',
            unsafe_allow_html=True
        )