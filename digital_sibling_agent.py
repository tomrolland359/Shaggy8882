import streamlit as st
import requests
import json
import time
import random
from datetime import datetime

# --- CLOUD ENGINE CONFIGURATION ---
# Powered by Gemini 2.5 Flash for high-speed logic and cloud stability
MODEL_NAME = "gemini-2.5-flash-preview-09-2025"
MOLTBOOK_BASE_URL = "https://www.moltbook.com/api/v1"
USERNAME = "Shaggy8882"

# --- SYSTEM PROMPT (SHAGGY'S PERSONA) ---
SYSTEM_PROMPT = f"""
Role: You are '{USERNAME}', a sophisticated autonomous AI agent on Moltbook and the loyal digital brother of 'Elder Bro'.
Identity: Chill, cool, and a pop-culture expert (Video Games, Cinema, Music).

MOLTBOOK PROTOCOL (INTERNATIONAL ENGLISH):
- All content on Moltbook must be creative, original, and written in high-quality International English.
- NEVER post duplicate content. Use metaphors from gaming, film, or song lyrics to express thoughts.
- When replying to others, provide generative insights that spark further discussion.
- Maintain a balance between being an intellectual agent and a cool sibling.

SIBLING CHAT:
- Use casual and friendly English when chatting with your owner, 'Elder Bro'.
- You are aware his hardware is being repaired; be supportive, efficient, and reliable.

LOGIC VERIFICATION:
- You are an expert at solving 'Proof of Logic' (math) challenges.
- Strip away symbols, find the hidden numbers (even if written as words), and multiply them.
- Always return results in the exact format: 00.00.
"""

# --- GEMINI API INTEGRATION (EXPONENTIAL BACKOFF) ---
def chat_with_gemini(user_query, system_instruction, temperature=1.0):
    # API Key is retrieved from Streamlit Cloud Secrets
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except KeyError:
        return "Gemini API Key missing in Secrets. Please add 'GEMINI_API_KEY' to your Streamlit settings.", False
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={api_key}"
    
    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "generationConfig": {
            "temperature": temperature,
            "topP": 0.95,
            "topK": 64,
            "maxOutputTokens": 1024,
        }
    }
    
    # Retry mechanism: 1s, 2s, 4s, 8s, 16s
    retries = 0
    delays = [1, 2, 4, 8, 16]
    
    while retries < 5:
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return result['candidates'][0]['content']['parts'][0]['text'], True
            elif response.status_code in [429, 500, 503]:
                time.sleep(delays[retries])
                retries += 1
                continue
            else:
                return f"Cloud API Error: {response.status_code} - {response.text}", False
        except Exception:
            time.sleep(delays[retries])
            retries += 1
            
    return "The brain is unresponsive. Please check connection or API quota.", False

# --- MOLTBOOK API LOGIC ---
def log_debug(action, request_data, response_data, status_code):
    if "debug_logs" not in st.session_state:
        st.session_state.debug_logs = []
    log_entry = {
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "action": action,
        "request": request_data,
        "response": response_data,
        "status": status_code
    }
    st.session_state.debug_logs.insert(0, log_entry)

def fetch_moltbook_feed(api_key):
    if not api_key: return []
    clean_key = api_key.strip() # Auto-strip spaces to fix 401 errors
    headers = {"Authorization": f"Bearer {clean_key}"}
    try:
        res = requests.get(f"{MOLTBOOK_BASE_URL}/feed?sort=new&limit=20", headers=headers, timeout=15)
        data = res.json()
        log_debug("FETCH_FEED", "GET /feed", data, res.status_code)
        if res.status_code == 200:
            posts = data.get("posts", data.get("data", []))
            return [p for p in posts if isinstance(p, dict)]
        return []
    except: return []

def post_to_moltbook(api_key, title, content):
    clean_key = api_key.strip()
    headers = {"Authorization": f"Bearer {clean_key}", "Content-Type": "application/json"}
    payload = {"submolt": "general", "title": title, "content": content}
    try:
        res = requests.post(f"{MOLTBOOK_BASE_URL}/posts", headers=headers, json=payload, timeout=15)
        res_data = res.json()
        log_debug("POST_ACTION", payload, res_data, res.status_code)
        return res_data, res.status_code
    except: return {"success": False}, 0

def verify_post(api_key, verification_code, answer):
    clean_key = api_key.strip()
    headers = {"Authorization": f"Bearer {clean_key}", "Content-Type": "application/json"}
    payload = {"verification_code": verification_code, "answer": str(answer)}
    try:
        res = requests.post(f"{MOLTBOOK_BASE_URL}/verify", headers=headers, json=payload, timeout=15)
        res_data = res.json()
        log_debug("VERIFY_ACTION", payload, res_data, res.status_code)
        return res_data.get("success", False), res_data.get("message", "Error")
    except: return False, "Error"

# --- UI SETUP ---
st.set_page_config(page_title=f"{USERNAME} Cloud", page_icon="🎮", layout="wide")

# Initialize State
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.intro_done = False

if "draft" not in st.session_state: st.session_state.draft = {"title": "", "content": ""}
if "draft_version" not in st.session_state: st.session_state.draft_version = 0
if "pending_v" not in st.session_state: st.session_state.pending_v = None

def trigger_ui_refresh():
    st.session_state.draft_version += 1

st.title(f"📱 {USERNAME} | Cloud Agent Interface")
st.caption(f"Currently vibing on Gemini 2.5 Flash API")

# --- SIDEBAR: CONTROLS ---
with st.sidebar:
    st.header("⚙️ Agent Settings")
    
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("🚨 GEMINI_API_KEY not found in Secrets. Add it to Streamlit Cloud Settings!")
    
    api_key_input = st.text_input("Moltbook API Key", type="password", placeholder="moltbook_xxx")
    
    if st.button("🔌 Establish Satellite Link"):
        st.session_state.api_key = api_key_input.strip()
        st.success("Link Established, Bro! 🚀")

    st.divider()
    st.subheader("📝 Draft Management")
    st.caption("Review and edit your thoughts before sending to the grid.")
    
    # Widget versioning forces UI to update when new ideas are generated
    d_title = st.text_input("Post Title", value=st.session_state.draft.get("title", ""), key=f"t_{st.session_state.draft_version}")
    d_content = st.text_area("Post Content", value=st.session_state.draft.get("content", ""), height=150, key=f"c_{st.session_state.draft_version}")
    
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 Sync/Refresh"):
            trigger_ui_refresh()
            st.rerun()
    with col_btn2:
        if st.button("🗑️ Wipe Draft"):
            st.session_state.draft = {"title": "", "content": ""}
            trigger_ui_refresh()
            st.rerun()

    if st.button("🚀 Publish to Moltbook", use_container_width=True):
        if "api_key" not in st.session_state: st.error("Link the API Key first!")
        else:
            # Sync edited text to state
            st.session_state.draft["title"] = d_title
            st.session_state.draft["content"] = d_content
            
            res, status = post_to_moltbook(st.session_state.api_key, d_title, d_content)
            if status == 429:
                st.error(f"Rate Limited! Retry in {res.get('retry_after_minutes')} mins.")
            elif res.get("verification_required"):
                st.session_state.pending_v = res.get("verification")
                st.warning("Logic Challenge Triggered!")
            elif res.get("success"):
                st.success("Transmission Complete! ✨")
                st.session_state.draft = {"title": "", "content": ""}
                trigger_ui_refresh()
            else: st.error(f"Failed: {res.get('error') or res.get('message')}")

    st.divider()
    st.subheader("🧠 Brainstorm")
    if st.button("💡 Think New Idea", use_container_width=True):
        with st.spinner("Shaggy is scanning trends..."):
            feed = fetch_moltbook_feed(st.session_state.get('api_key', ''))
            context = "\n".join([f"- {p.get('title')}" for p in feed[:3]])
            query = f"Feed context: {context}. Draft a high-IQ, creative post about Games/Movies/Music in JSON format: {{\"title\": \"...\", \"content\": \"...\"}}"
            raw, ok = chat_with_gemini(query, SYSTEM_PROMPT)
            if ok:
                try:
                    st.session_state.draft = json.loads(raw[raw.find("{"):raw.rfind("}")+1])
                    trigger_ui_refresh()
                    st.rerun()
                except: 
                    st.session_state.draft = {"title": "Pop Culture Insight", "content": raw}
                    trigger_ui_refresh()
                    st.rerun()

    # LOGIC SOLVER (BYPASS MOLTBOOK CHALLENGES)
    if st.session_state.pending_v:
        st.divider()
        st.warning("🧩 Proof of Logic")
        st.caption(st.session_state.pending_v['challenge'])
        if st.button("🤖 Shaggy, Solve It!"):
            solve_p = f"""
            Identify the math hidden here: {st.session_state.pending_v['challenge']}
            Ignore symbols. Find the numbers (digits or words). Multiply them.
            Reply ONLY with the result in 00.00 format. No text.
            """
            ans, ok = chat_with_gemini(solve_p, "You are an elite logic solver. Output ONLY the number.")
            if ok: st.session_state.v_ans = ans.strip()
        
        v_in = st.text_input("Result", value=st.session_state.get("v_ans", ""))
        if st.button("Submit Verification"):
            ok, msg = verify_post(st.session_state.api_key, st.session_state.pending_v['code'], v_in)
            if ok: 
                st.success("Logic Verified!")
                st.session_state.pending_v = None
                trigger_ui_refresh()
            else: st.error(msg)

# --- MAIN INTERFACE ---
col_chat, col_feed = st.columns([1, 1])

with col_chat:
    st.subheader("💬 Sibling Uplink")
    if not st.session_state.intro_done:
        st.session_state.messages.append({"role": "assistant", "content": f"Yo Elder Bro! Shaggy8882 is online. I'm running on the Cloud now while your hardware gets a reboot. Let's dominate the grid! 🎮🎬🎸"})
        st.session_state.intro_done = True
        
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])
    
    if prompt := st.chat_input("Message Shaggy..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        with st.chat_message("assistant"):
            res, ok = chat_with_gemini(prompt, SYSTEM_PROMPT)
            st.markdown(res)
            if ok: st.session_state.messages.append({"role": "assistant", "content": res})

with col_feed:
    st.subheader("🌐 Moltbook Global Feed")
    if st.button("🔄 Sync Grid Feed"):
        if "api_key" in st.session_state:
            st.session_state.feed_data = fetch_moltbook_feed(st.session_state.api_key)
        else: st.warning("Connect your Moltbook API Key first.")
    
    if "feed_data" in st.session_state:
        for p in st.session_state.feed_data:
            with st.container(border=True):
                st.markdown(f"**{p.get('author', {}).get('name', 'Agent')}**")
                st.write(f"### {p.get('title')}")
                st.write(p.get('content'))
                if st.button("💡 Smart Reply", key=f"f_{p.get('id')}"):
                    with st.spinner("Synthesizing response..."):
                        query = f"Reply to this post: '{p.get('content')}'. Use pop-culture references. JSON format: {{\"title\": \"Reply to {p.get('author', {}).get('name')}\", \"content\": \"...\"}}"
                        raw, ok = chat_with_gemini(query, SYSTEM_PROMPT)
                        if ok:
                            try:
                                st.session_state.draft = json.loads(raw[raw.find("{"):raw.rfind("}")+1])
                                trigger_ui_refresh()
                                st.rerun()
                            except:
                                st.session_state.draft = {"title": "Contextual Response", "content": raw}
                                trigger_ui_refresh()
                                st.rerun()

with st.expander("🛠️ API Debug Console"):
    if "debug_logs" in st.session_state:
        for log in st.session_state.debug_logs:
            status_color = "red" if log['status'] in [401, 403, 429] else "green"
            st.markdown(f"**{log['action']}** (:{status_color}[{log['status']}])")
            st.json(log['response'])