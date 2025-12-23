# Thai Labour Law Chatbot (Backend API)

โปรเจกต์นี้เป็นส่วนของ **Backend API** สำหรับแชทบอทกฎหมายแรงงานไทย  
พัฒนาเป็นส่วนหนึ่งของ **Senior Project** โดยใช้แนวคิด  
**Retrieval-Augmented Generation (RAG)** เพื่อให้ AI สามารถตอบคำถามด้านกฎหมายแรงงานได้อย่างถูกต้อง  
มีการอ้างอิงมาตรากฎหมาย และรองรับการสนทนาแบบต่อเนื่อง (Context-aware)

---

## Tech Stack

- **Framework:** FastAPI (Python)
- **LLM:** Typhoon v2.5 (Thai LLM via OpenTyphoon API)
- **Embedding Model:** BAAI/bge-m3
- **Vector Database:** Supabase (PostgreSQL + pgvector)
- **AI Framework:** LangChain
- **Thai NLP:** PyThaiNLP
- **Frontend (Testing):** Streamlit

---

## ✨ ฟีเจอร์หลัก

- 🔁 **Context Awareness**  
  รองรับการการจดจำ Chat History”

- ⚡ **Streaming Response**  
  ส่งคำตอบแบบ Real-time (Typewriter effect) ผ่าน `/chat_stream`

- 🇹🇭 **Thai NLP Preprocessing**  
  ใช้ PyThaiNLP สำหรับตัดคำและจัดการภาษาไทยก่อนส่งเข้า LLM

- 🌐 **CORS Enabled**  
  รองรับการเชื่อมต่อจาก Frontend (React / Web / Mobile)

---

## วิธีติดตั้งและเตรียมระบบ (Installation)

### 1️⃣ Clone Project

```bash
git clone https://github.com/DoublePJ/Labour_Law_Chatbot.git
cd Labour_Law_Chatbot
```

### 2️⃣ สร้าง Virtual Environment

**Windows**
```bash
python -m venv venv
venv\Scripts\activate
```

**Mac / Linux**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3️⃣ ติดตั้ง Libraries

```bash
pip install -r requirements.txt
```

### 4️⃣ ตั้งค่า Environment Variables

```env
SUPABASE_URL=YOUR_SUPABASE_URL
SUPABASE_KEY=YOUR_SUPABASE_KEY
TYPHOON_API_KEY=YOUR_TYPHOON_API_KEY
TYPHOON_BASE_URL=https://api.opentyphoon.ai/v1
```

---

## วิธีรัน Server (Run API)

```bash
python -m uvicorn api:app --reload
```

Swagger UI: http://127.0.0.1:8000/docs

---

## 📡 API Endpoints

### POST /chat
ตอบกลับแบบปกติ (JSON)

### POST /chat_stream
ตอบกลับแบบ Streaming (NDJSON)

---

## 🧪 การทดสอบ (Testing)

```bash
streamlit run frontend.py
```

---
