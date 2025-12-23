import streamlit as st
import requests
import json
import time
st.set_page_config(page_title="ทนายแรงงาน AI (Streaming Mode)", page_icon="⚖️")
st.title("⚖️ ระบบทดสอบ Context Awareness + Streaming")
st.caption("ทดสอบระบบตอบกลับแบบ Real-time (พิมพ์ทีละคำ)")

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

    # 4. ส่วนตอบกลับแบบ Streaming
    with st.chat_message("assistant"):
        # สร้างกล่องเปล่าๆ รอรับข้อความ
        answer_placeholder = st.empty()
        full_response = ""
        sources_list = []

        try:
            # เตรียมข้อมูลส่ง (Payload)
            payload = {
                "question": prompt,
                "history": st.session_state.messages[:-1] 
            }

            # --- [จุดสำคัญที่แก้] ---
            # 1. ยิงไปที่ /chat_stream (ไม่ใช่ /chat)
            # 2. ใส่ stream=True เพื่อบอก requests ว่าขอรับข้อมูลเรื่อยๆ
            with requests.post(
                "http://127.0.0.1:8000/chat_stream",
                json=payload,
                stream=True, 
                timeout=60
            ) as response:

                if response.status_code == 200:
                    for line in response.iter_lines():
                        if line:
                            json_line = line.decode('utf-8')
                            data = json.loads(json_line)

                            if data.get("type") == "sources":
                                sources_list = data.get("data", [])
                            
                            elif data.get("type") == "content":
                                chunk = data.get("data", "")
                                full_response += chunk
                                answer_placeholder.markdown(full_response + "▌")
                                
                                # --- [2] เพิ่มความหน่วงตรงนี้ ---
                                # แนะนำ 0.02 - 0.05 วินาที (ถ้า 0.5 จะช้ามาก)
                                time.sleep(0.02) 
                    
                    
                    
                    # จบการทำงาน: แสดงข้อความตัวเต็ม (ลบ cursor ออก)
                    answer_placeholder.markdown(full_response)
                    
                    # แสดง Sources (ถ้ามี)
                    if sources_list:
                        st.info(f"📚 อ้างอิง: {', '.join(sources_list)}")
                    
                    # บันทึกคำตอบลงประวัติ
                    st.session_state.messages.append({"role": "assistant", "content": full_response})

                else:
                    st.error(f"Error: {response.status_code} - {response.text}")

        except Exception as e:
            st.error(f"เชื่อมต่อไม่ได้: {e}")