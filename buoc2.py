import streamlit as st
import requests
import json
import sqlite3
from datetime import datetime
import uuid

# --- CẤU HÌNH ---
API_KEY = "AIzaSyDYu4SiiPF9iZFrg7suoUTbhxiu3AQaskE"

# 👇👇👇 ĐÃ ĐỔI TÊN THÀNH "NDA GPT" Ở ĐÂY 👇👇👇
st.set_page_config(page_title="NDA GPT", page_icon="🤖", layout="wide")

st.markdown("""<style>.stChatFloatingInputContainer {bottom: 20px;} .block-container {padding-top: 32px;} header {visibility: hidden;} footer {visibility: hidden;}</style>""", unsafe_allow_html=True)

# Tiêu đề to đùng trong web
st.title("🤖 NDA GPT - Trợ Lý AI")

# --- DATABASE ---
DB_FILE = 'nda_gpt.db' # Đổi tên DB mới cho NDA GPT
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, user_id TEXT, name TEXT, pinned INTEGER, created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (session_id TEXT, role TEXT, content TEXT, time TEXT)''')
    conn.commit()
    conn.close()

def create_session(user_id, first_msg="Cuộc trò chuyện mới"):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    session_id = str(uuid.uuid4())
    name = first_msg[:30] if len(first_msg) > 30 else first_msg
    c.execute("INSERT INTO sessions VALUES (?, ?, ?, ?, ?)", (session_id, user_id, name, 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()
    return session_id

def get_sessions(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name, pinned FROM sessions WHERE user_id=? ORDER BY pinned DESC, created_at DESC", (user_id,))
    data = c.fetchall()
    conn.close()
    return data

def update_session(session_id, action, value=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if action == "rename": c.execute("UPDATE sessions SET name=? WHERE id=?", (value, session_id))
    elif action == "pin": c.execute("UPDATE sessions SET pinned=? WHERE id=?", (value, session_id))
    elif action == "delete": 
        c.execute("DELETE FROM sessions WHERE id=?", (session_id,))
        c.execute("DELETE FROM messages WHERE session_id=?", (session_id,))
    conn.commit()
    conn.close()

def save_msg(session_id, role, content):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO messages VALUES (?, ?, ?, ?)", (session_id, role, content, datetime.now().strftime("%H:%M:%S")))
    conn.commit()
    conn.close()

def load_msgs(session_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages WHERE session_id=? ORDER BY rowid ASC", (session_id,))
    data = c.fetchall()
    conn.close()
    return data

init_db()

# --- LOGIC AI ---
def find_best_model():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            chat_models = [m['name'] for m in data.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
            for preferred in ['models/gemini-1.5-flash', 'models/gemini-1.5-pro', 'models/gemini-pro']:
                if preferred in chat_models: return preferred
            if chat_models: return chat_models[0]
        return "models/gemini-pro"
    except: return "models/gemini-pro"

if "my_model" not in st.session_state:
    st.session_state.my_model = find_best_model()

def chat_direct(prompt, history=[]):
    model_name = st.session_state.my_model
    url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={API_KEY}"
    contents = []
    for role, text in history:
        role_gg = "user" if role == "user" else "model"
        contents.append({"role": role_gg, "parts": [{"text": text}]})
    contents.append({"role": "user", "parts": [{"text": prompt}]})
    payload = {"contents": contents, "generationConfig": {"temperature": 0.7}}
    try:
        response = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(payload))
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else: return f"Lỗi Google ({response.status_code}): {response.text}"
    except Exception as e: return f"Lỗi mạng: {str(e)}"

# --- GIAO DIỆN ---
with st.sidebar:
    st.header("👤 Đăng Nhập")
    mode = st.radio("Chế độ:", ["Khách Hàng", "Admin"], label_visibility="collapsed")
    current_user_id = None
    
    if mode == "Khách Hàng":
        name_input = st.text_input("Tên của bạn:", placeholder="Nhập tên...", key="login_name")
        if name_input: current_user_id = f"K_{name_input}"
    else:
        pwd = st.text_input("Mật khẩu Admin:", type="password")
        if pwd == "admin123":
            current_user_id = "ADMIN"
            st.success("Admin đã đăng nhập")

    st.divider()

    if current_user_id:
        if st.button("➕ Chat Mới", use_container_width=True, type="primary"):
            st.session_state.active_session = create_session(current_user_id)
            st.rerun()
            
        sessions = get_sessions(current_user_id)
        if not sessions:
            st.caption("Trống.")
            if "active_session" not in st.session_state:
                st.session_state.active_session = create_session(current_user_id)
                st.rerun()
        else:
            session_options = {s[0]: s for s in sessions}
            if "active_session" not in st.session_state or st.session_state.active_session not in session_options:
                st.session_state.active_session = sessions[0][0]
            
            selected_id = st.radio("Hội thoại:", options=session_options.keys(), format_func=lambda x: f"{'📌 ' if session_options[x][2] else ''}{session_options[x][1]}", label_visibility="collapsed", key="ss_select")
            if selected_id != st.session_state.active_session:
                st.session_state.active_session = selected_id
                st.rerun()
            
            active_data = session_options[st.session_state.active_session]
            with st.popover("⋮ Tùy chọn", use_container_width=True):
                new_name = st.text_input("Đổi tên:", value=active_data[1])
                if st.button("Lưu tên"): update_session(st.session_state.active_session, "rename", new_name); st.rerun()
                if st.button(f"{'🚫 Bỏ Ghim' if active_data[2] else '📌 Ghim'}", use_container_width=True): update_session(st.session_state.active_session, "pin", 1 - active_data[2]); st.rerun()
                st.divider()
                if st.button("🗑️ Xóa", type="primary", use_container_width=True): update_session(st.session_state.active_session, "delete"); del st.session_state.active_session; st.rerun()

if not current_user_id:
    st.info("👈 Nhập tên bên trái để bắt đầu!")
    st.stop()

active_id = st.session_state.active_session
history = load_msgs(active_id)

for role, content in history:
    with st.chat_message(role): st.write(content)

if prompt := st.chat_input("Nhập tin nhắn..."):
    with st.chat_message("user"): st.write(prompt)
    save_msg(active_id, "user", prompt)
    
    # Auto rename nhưng không rerun để tránh lag
    if len(history) == 0: 
        update_session(active_id, "rename", prompt[:30])

    with st.chat_message("assistant"):
        with st.spinner("..."):
            reply = chat_direct(prompt, history)
            st.write(reply)
            save_msg(active_id, "assistant", reply)