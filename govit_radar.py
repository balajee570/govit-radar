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
.stApp { background-color: #ffffff !important; font-family: 'Segoe UI'; }
section[data-testid="stSidebar"] { display: none !important; }
#MainMenu, footer { visibility: hidden; }
.result-block {
    background: #f8fafc; border: 1px solid #e2e8f0;
    border-radius: 10px; padding: 22px;
    margin-top: 16px; font-size: 14px;
    line-height: 1.8; white-space: pre-wrap;
}
.ts { font-size: 11px; color: #94a3b8; text-align: right; }
.debug-box {
    background: #fff8f0; border: 1px solid #fcd0a0;
    border-radius: 8px; padding: 12px;
    font-size: 12px; color: #7a4010;
    white-space: pre-wrap;
}
</style>
""", unsafe_allow_html=True)

# ── KEYS ───────────────────────────────────────────────────────────
def get_key(k):
    try:
        return st.secrets[k]
    except:
        return ""

# ── EXPIRY FILTER ──────────────────────────────────────────────────
def is_expired(text, today):
    text = text.lower()

    patterns = [
        r'(\d{1,2}\s+[a-zA-Z]+\s+\d{4})',
        r'(\d{1,2}/\d{1,2}/\d{4})',
        r'(\d{1,2}-\d{1,2}-\d{4})'
    ]

    for p in patterns:
        match = re.search(p, text)
        if match:
            date_str = match.group(1)

            for fmt in ["%d %B %Y", "%d/%m/%Y", "%d-%m-%Y"]:
                try:
                    parsed = datetime.strptime(date_str, fmt)
                    if parsed.date() < today.date():
                        return True
                except:
                    continue
    return False

# ── QUERIES ────────────────────────────────────────────────────────
def get_queries():
    yr    = now_ist().year
    month = now_ist().strftime("%B")

    return [
        f"latest govt IT jobs India {month} {yr}",
        f"government software engineer vacancy India {yr}",
        f"NIC scientist B recruitment apply online {yr}",
        f"central government IT officer jobs {yr}",
        f"PSU IT jobs recruitment {month} {yr}",
        f"DRDO IT engineer recruitment {yr}",
        f"ISRO software engineer recruitment {yr}",
        f"freshers government IT jobs India {yr}",
        f"government data analyst jobs India {yr}",
        f"MeitY Digital India jobs apply online {yr}",
        f"contract IT jobs government India {yr}",
        f"walk-in IT jobs government India {month} {yr}"
    ]

# ── FETCH DATA ─────────────────────────────────────────────────────
def fetch_raw():
    client = TavilyClient(api_key=get_key("TAVILY_API_KEY"))
    seen_urls, seen_titles, found = set(), set(), []

    for q in get_queries():
        try:
            res = client.search(
                query=q,
                search_depth="advanced",
                max_results=8,
                days=30,
                include_domains=[
                    "upsc.gov.in", "ssc.nic.in", "nic.in",
                    "meity.gov.in", "bpsc.bih.nic.in",
                    "employment.gov.in", "ncs.gov.in",
                    "freejobalert.com", "freshersworld.com",
                    "govtjobguru.in", "testbook.com",
                    "adda247.com", "gradeup.co",
                    "thehindu.com", "timesofindia.com",
                    "ndtv.com", "livemint.com",
                    "jagran.com",
                    "digitalindia.gov.in", "cdac.in",
                    "bel-india.in", "drdo.gov.in", "isro.gov.in"
                ]
            )

            for r in res.get("results", []):
                url   = r.get("url", "")
                title = r.get("title", "").strip().lower()
                content = r.get("content", "")

                if not url or url in seen_urls:
                    continue

                if title in seen_titles:
                    continue

                combined = (title + " " + content)

                if is_expired(combined, now_ist()):
                    continue

                seen_urls.add(url)
                seen_titles.add(title)

                found.append({
                    "title": r.get("title", ""),
                    "url": url,
                    "content": content[:400],
                    "published": r.get("published_date", "unknown"),
                })

        except:
            continue

    found = sorted(found, key=lambda x: x.get("published",""), reverse=True)
    return found

# ── SARVAM CALL ────────────────────────────────────────────────────
def call_sarvam(api_key, messages):
    try:
        resp = requests.post(
            SARVAM_URL,
            headers={"api-subscription-key": api_key},
            json={
                "model": SARVAM_MODEL,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 1500
            },
            timeout=45
        )

        data = resp.json()

        if resp.status_code != 200:
            return None, str(data)

        content = data["choices"][0]["message"].get("content")

        if not content:
            return None, f"Incomplete response. Finish reason: {data['choices'][0].get('finish_reason')}"

        return content.strip(), None

    except Exception as e:
        return None, str(e)

# ── CHUNKING ───────────────────────────────────────────────────────
def chunk_text(items, chunk_size=6):
    for i in range(0, len(items), chunk_size):
        yield items[i:i+chunk_size]

# ── REFINE CHUNK ───────────────────────────────────────────────────
def refine_chunk(chunk, today_str):

    text = "\n".join(
        f"Title: {r['title']}\n"
        f"Published: {r['published']}\n"
        f"URL: {r['url']}\n"
        f"Info: {r['content']}\n---"
        for r in chunk
    )

    prompt = f"""
Today's date: {today_str}

STRICT RULES:
- Only include ACTIVE jobs
- If last date missing → discard
- If last date < today → discard
- If unsure → discard

DATA:
{text}

OUTPUT:
• [Post Name] — [Organization]
  [Short role]
  [Last date]
  Apply: [URL]

No explanation.
"""

    messages = [
        {"role": "system", "content": "Filter active govt jobs only."},
        {"role": "user", "content": prompt}
    ]

    return call_sarvam(get_key("SARVAM_API_KEY"), messages)

# ── MAIN REFINE ────────────────────────────────────────────────────
def refine(raw, today_str):

    outputs = []

    for chunk in chunk_text(raw, 6):
        out, err = refine_chunk(chunk, today_str)
        if out:
            outputs.append(out)

    if not outputs:
        return None, "All chunks failed"

    combined = "\n".join(outputs)
    return combined, None

# ── UI ─────────────────────────────────────────────────────────────
st.markdown("## 📡 GovIT Radar")
st.markdown(f"*{now_ist().strftime('%d %b %Y')}*")

if st.button("🔍 Fetch Active Openings"):

    tv_key = get_key("TAVILY_API_KEY")
    sv_key = get_key("SARVAM_API_KEY")

    if not tv_key or not sv_key:
        st.error("API keys missing in secrets.toml")
        st.stop()

    with st.spinner("Fetching jobs..."):
        raw = fetch_raw()

    if not raw:
        st.warning("No results found")
        st.stop()

    with st.spinner("Filtering with AI..."):
        output, error = refine(raw, now_ist().strftime("%d %B %Y"))

    if error:
        st.markdown(f'<div class="debug-box">{error}</div>', unsafe_allow_html=True)

    elif not output:
        st.warning("No filtered jobs. Showing raw results:")
        for r in raw[:5]:
            st.write(f"• {r['title']}")
            st.write(r["url"])

    else:
        st.markdown(f'<div class="result-block">{output}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="ts">{now_ist().strftime("%d %b %Y %I:%M %p")} IST</div>',
            unsafe_allow_html=True
        )