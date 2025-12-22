import os
from typing import List, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client, Client

# LangChain Imports
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

#pythainlp
from pythainlp.util import normalize          # สำหรับจัดระเบียบสระ/วรรณยุกต์
from pythainlp.tokenize import word_tokenize  # สำหรับตัดคำ

# 1. โหลดตัวแปรจาก .env (กุญแจต่างๆ)
load_dotenv()

# 2. ตั้งค่า Supabase (ฐานข้อมูล)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 3. ตั้งค่า AI (Typhoon API)
# ใช้ ChatOpenAI แต่ชี้ไปที่ Server ของ Typhoon
llm = ChatOpenAI(
    base_url=os.getenv("TYPHOON_BASE_URL"), # https://api.opentyphoon.ai/v1
    api_key=os.getenv("TYPHOON_API_KEY"),
    model="typhoon-v2.5-30b-a3b-instruct",      # โมเดลตัวเก่งสุด
    temperature=0.3,                         # ความคิดสร้างสรรค์ต่ำหน่อย เพื่อความแม่นยำทางกฎหมาย
    max_tokens=4096                          # เพิ่มพื้นที่ให้ AI ตอบยาวๆ ได้ ไม่ error
)

# 4. ตั้งค่า Embedding (ตัวแปลงข้อความเป็นตัวเลข)
# ใช้ BGE-M3 เหมือนเดิม เพราะเก่งภาษาไทย
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")

# 5. เริ่มต้นแอป FastAPI
app = FastAPI()

# --- Data Models (รูปแบบข้อมูลที่รับ-ส่ง) ---

class ChatRequest(BaseModel):
    question: str
    history: List[Dict[str, str]] = []  # รับประวัติการคุยมาด้วย (Context Awareness)

class ChatResponse(BaseModel):
    answer: str
    sources: List[str]                  # ส่งรายการมาตราที่อ้างอิงกลับไป (Citation)

# --- Helper Functions (ฟังก์ชันช่วยทำงาน) ---

def preprocess_thai_text(text: str) -> str:
    """
    ฟังก์ชันทำความสะอาดภาษาไทย (Text Preprocessing) ตาม Proposal
    1. Normalize: แก้ปัญหาสระลอย วรรณยุกต์ซ้อน
    2. Tokenize: ตัดคำและคั่นด้วยช่องว่าง เพื่อให้ Embedding Model จับใจความได้แม่นขึ้น
    """
    # 1. จัดระเบียบตัวอักษร (เช่น สระอำ หรือวรรณยุกต์ที่พิมพ์ผิดลำดับ)
    clean_text = normalize(text)
    
    # 2. ตัดคำแล้วเชื่อมด้วยช่องว่าง (เช่น "ลากิจได้กี่วัน" -> "ลากิจ ได้ กี่ วัน")
    # การทำแบบนี้ช่วยให้โมเดล BGE-M3 เข้าใจขอบเขตคำได้ชัดเจนขึ้น
    words = word_tokenize(clean_text, engine="newmm", keep_whitespace=False)
    
    return " ".join(words)

def retrieve_data(question: str):
    """ฟังก์ชันค้นหากฎหมายจาก Supabase"""
    print(f"   🔍 กำลังค้นหาข้อมูลสำหรับ: {question}")
    
    # 1. แปลงคำถามเป็น Vector
    query_vector = embeddings.embed_query(question)
    
    # 2. ยิงไปถาม Supabase (ใช้ฟังก์ชัน match_sections_v2 ที่เราสร้างใน SQL)
    response = supabase.rpc(
        "match_sections_v2",
        {
            "query_embedding": query_vector,
            "match_threshold": 0.5, # ความเหมือนขั้นต่ำ 50%
            "match_count": 5        # เอามา 5 อันดับแรก
        }
    ).execute()
    
    return response.data

def rewrite_question(question: str, history: List[Dict[str, str]]) -> str:
    """ฟังก์ชัน Context Awareness: แปลงคำถามกว้างๆ ให้ชัดเจนขึ้นโดยดูประวัติ"""
    
    # ถ้าไม่มีประวัติเก่า ก็ใช้คำถามเดิมเลย
    if not history:
        return question
    
    print("   🔄 กำลังเรียบเรียงคำถามใหม่ (Query Rewriting)...")
    
    # แปลง History List ให้เป็นข้อความ String
    history_text = ""
    for msg in history[-4:]: # ดูย้อนหลังแค่ 2-3 คู่ล่าสุดพอ (ประหยัด Token)
        role = "User" if msg['role'] == 'user' else "AI"
        history_text += f"{role}: {msg['content']}\n"
    
    # Prompt สั่งให้ AI เขียนคำถามใหม่ (Standalone Question)
    rewrite_template = """
    จากบทสนทนาต่อไปนี้:
    {chat_history}
    
    และคำถามล่าสุด: "{question}"
    
    จงเขียน "คำถามใหม่" ให้เป็นประโยคที่สมบูรณ์และเข้าใจได้ด้วยตัวเอง (Standalone Question) 
    โดยรวมบริบทจากประวัติการสนทนาเข้าไปด้วย เพื่อให้สามารถนำไปค้นหาในฐานข้อมูลกฎหมายได้แม่นยำ
    (ตอบเฉพาะประโยคคำถามใหม่เท่านั้น ไม่ต้องเกริ่นนำ ไม่ต้องใส่เครื่องหมายคำพูด)
    
    คำถามใหม่:
    """
    
    try:
        prompt = PromptTemplate(template=rewrite_template, input_variables=["chat_history", "question"])
        chain = prompt | llm | StrOutputParser()
        
        # สั่ง AI ทำงาน
        new_question = chain.invoke({"chat_history": history_text, "question": question})
        
        print(f"   ✨ คำถามใหม่ที่ได้: {new_question}")
        return new_question.strip()
        
    except Exception as e:
        print(f"   ❌ Error rewriting: {e}")
        return question # ถ้า error ให้ใช้คำถามเดิมไปก่อน

# --- Main API Endpoint ---

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # --- [NEW] Step 0: Text Preprocessing (PyThaiNLP) ---
        # ตรงตาม Proposal เรื่องการทำความสะอาดและจัดการภาษาธรรมชาติ [cite: 45, 201]
        processed_question = preprocess_thai_text(request.question)
        print(f"   🧹 Cleaned Input: {processed_question}") # เช็ค Log ดูว่ามันตัดคำให้ไหม
        
        # Step 1: Context Awareness (Query Rewriting)
        # เช็คประวัติ แล้วเขียนคำถามใหม่ให้ชัดเจน
        search_query = rewrite_question(request.question, request.history)
        
        # Step 2: Retrieval (ค้นหาข้อมูลจากคำถามใหม่)
        retrieved_docs = retrieve_data(search_query)
        
        # ถ้าหาไม่เจอเลย
        if not retrieved_docs:
            return ChatResponse(answer="ขออภัยครับ ไม่พบข้อมูลกฎหมายที่เกี่ยวข้องกับเรื่องนี้ในฐานข้อมูล", sources=[])

        # Step 3: Prepare Context (เตรียมข้อมูลใส่ Prompt)
        # --- Step 3: Prepare Context (เตรียมข้อมูลใส่ Prompt) ---
        context_text = ""
        sources_set = set() # ใช้ set เพื่อกันซ้ำ
        
        for doc in retrieved_docs:
            sec_num = doc.get('section_number', '?')
            text = doc.get('text_original', '')
            # เก็บเนื้อหาไว้ตอบ (ยังคงเอามาทั้งหมดเพื่อให้ AI อ่าน)
            context_text += f"- มาตรา {sec_num}: {text}\n\n"
            # เก็บเลขมาตราลง set (ถ้ามีอยู่แล้ว มันจะไม่เพิ่มซ้ำ)
            sources_set.add(f"มาตรา {sec_num}")
        # แปลงกลับเป็น list และเรียงลำดับให้สวยงาม (เช่น มาตรา 9, 76, 118)
        # ใช้ lambda เพื่อดึงเลขมาเรียง (ป้องกันการเรียงแบบ string เช่น 1, 10, 2)
        try:
            sources_list = sorted(list(sources_set), key=lambda x: int(x.split()[-1]) if x.split()[-1].isdigit() else 9999)
        except:
            sources_list = sorted(list(sources_set)) # ถ้าเรียงไม่ได้ก็เรียงตามตัวอักษรปกติ

        # Step 4: Generation (ให้ AI ตอบ)
        template = """
        คุณคือทนายความผู้เชี่ยวชาญกฎหมายแรงงานไทย (Thai Labour Law Expert)
        หน้าที่ของคุณคือให้คำปรึกษาแก่ลูกจ้างอย่างถูกต้อง สุภาพ และเข้าใจง่าย
        
        ข้อมูลกฎหมายที่อ้างอิง:
        {context}
        
        คำถาม: {question}
        
        คำแนะนำในการตอบ:
        1. ตอบคำถามโดยอ้างอิงจาก "ข้อมูลกฎหมาย" ที่ให้ไปเท่านั้น
        2. ถ้าข้อมูลไม่เพียงพอ ให้บอกตรงๆ ว่าไม่ทราบ
        3. อ้างอิงเลขมาตราเสมอเมื่อกล่าวถึงข้อกฎหมาย
        4. สรุปใจความสำคัญให้เข้าใจง่ายสำหรับคนทั่วไป
        
        คำตอบ:
        """
        
        prompt = PromptTemplate(template=template, input_variables=["context", "question"])
        chain = prompt | llm | StrOutputParser()
        
        # ส่ง search_query (ที่แก้แล้ว) + context ไปให้ AI
        ai_answer = chain.invoke({"context": context_text, "question": search_query})
        
        # Step 5: Return Result (ส่งคำตอบ + แหล่งอ้างอิงกลับไป)
        return ChatResponse(answer=ai_answer, sources=sources_list)

    except Exception as e:
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# วิธีรัน: python -m uvicorn api:app --reload