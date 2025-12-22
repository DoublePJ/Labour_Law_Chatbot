import streamlit as st
import requests

st.set_page_config(page_title="ทนายแรงงาน AI (Test Mode)", page_icon="⚖️")
st.title("⚖️ ระบบทดสอบ Context Awareness")
st.caption("ทดสอบการจำบริบท: ลองถามคำถามต่อเนื่อง เช่น 'ลาป่วยได้กี่วัน' แล้วตามด้วย 'แล้วต้องมีใบรับรองแพทย์ไหม'")

# 1. สร้างตัวแปรเก็บประวัติถ้ายังไม่มี
if "messages" not in st.session_state:
    st.session_state.messages = []

# 2. วนลูปแสดงประวัติการคุยเก่าๆ
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 3. ช่องรับคำถาม
if prompt := st.chat_input("พิมพ์คำถาม..."):
    # แสดงคำถาม user
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 4. ส่งไปหา API (พร้อมประวัติ!)
    with st.chat_message("assistant"):
        with st.spinner("กำลังคิดและเรียบเรียงคำถามใหม่..."):
            try:
                # เตรียมข้อมูลส่ง (Payload)
                payload = {
                    "question": prompt,
                    # ส่งประวัติทั้งหมดที่มีไปให้ Backend (ตัดอันล่าสุดออกเพราะซ้ำกับ question)
                    "history": st.session_state.messages[:-1] 
                }

                # ยิง API
                response = requests.post(
                    "http://127.0.0.1:8000/chat",
                    json=payload,
                    timeout=60
                )

                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("answer", "")
                    sources = data.get("sources", [])
                    
                    st.markdown(answer)
                    if sources:
                        st.info(f"📚 อ้างอิง: {', '.join(sources)}")
                    
                    # บันทึกคำตอบ AI ลงประวัติ
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                else:
                    st.error(f"Error: {response.status_code} - {response.text}")

            except Exception as e:
                st.error(f"เชื่อมต่อไม่ได้: {e}")