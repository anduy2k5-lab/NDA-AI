import streamlit as st
import google.generativeai as genai
import uuid
from datetime import datetime
import os

# --- CẤU HÌNH BẢO MẬT (QUAN TRỌNG NHẤT) ---
# Code này sẽ ưu tiên lấy Key từ "Két sắt" (Secrets) khi lên Cloud
try:
    if "API_KEY" in st.secrets:
        API_KEY = st.secrets["API_KEY"]
    else:
        # Nếu chạy trên máy tính cá nhân (Local) thì dùng dòng này
        # (Lưu ý: Khi đưa lên GitHub, dòng này không sao vì Cloud sẽ ưu tiên st.secrets ở trên)
        API_KEY = "AIzaSyDYu4SiiPF9iZFrg7suoUTbhxiu3AQaskE" 
except:
    API_KEY = "AIzaSyDYu4SiiPF9iZFrg7suoUTbhxiu3AQaskE"

# Kiểm tra lần cuối xem có chìa khóa chưa
if not API_KEY:
    st.error("⚠️ Chưa tìm thấy API Key! Hãy vào phần Settings -> Secrets trên Streamlit Cloud để điền Key.")
    st.stop()

st.set_page_config(page_title="NDA GPT", page_icon="🤖", layout="wide")
st.title("🤖 NDA GPT - Trợ Lý AI")

# --- LOGIC AI ---
def chat_with_google(prompt, history):
    try:
        genai.configure(api_key=API_KEY)
        # Sử dụng model Flash cho nhanh
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        chat_history = []
        for role, text in history:
            role_gg = "user" if role == "user" else "model"
            chat_history.append({"role": role_gg, "parts": [text]})
            
        chat = model.start_chat(history=chat_history)
        response = chat.send_message(prompt)
        return response.text
    except Exception as e:
        return f"Lỗi kết nối: {str(e)}"

# --- GIAO DIỆN ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if prompt := st.chat_input("Nhập tin nhắn..."):
    with st.chat_message("user"):
        st.write(prompt)
    
    history_for_ai = [(m["role"], m["content"]) for m in st.session_state.messages]
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("NDA GPT đang suy nghĩ..."):
            response = chat_with_google(prompt, history_for_ai)
            st.write(response)
    st.session_state.messages.append({"role": "assistant", "content": response})