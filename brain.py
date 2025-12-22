import os
from dotenv import load_dotenv
from supabase import create_client, Client
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 1. โหลด Config
load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

print("⏳ กำลังเตรียมระบบ... (โหลด Embedding Model)")
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")

# 2. ตั้งค่า LLM (Typhoon ผ่าน Ollama)
# ถ้าเครื่องช้า ให้ลองเปลี่ยน model เป็น 'gemma2' หรือ 'llama3' ดูครับ
llm = ChatOllama(model="llama3.1", temperature=0.3)

# 3. ฟังก์ชันค้นหากฎหมาย (Retrieval) - ใช้ Logic เดิมที่แม่นแล้ว
def retrieve_data(query_text):
    print(f"   🔍 กำลังค้นหากฎหมายเรื่อง: {query_text}...")
    query_vector = embeddings.embed_query(query_text)
    
    # เรียกใช้ Function v2 ที่เราสร้างแก้ Error ไว้
    params = {
        "query_embedding": query_vector,
        "match_threshold": 0.4, # ปรับตามความเหมาะสม
        "match_count": 5        # ส่งให้ AI อ่านสัก 5 มาตรากำลังดี
    }
    response = supabase.rpc("match_sections_v2", params).execute()
    return response.data

# 4. ฟังก์ชันตอบคำถาม (Generation)
def generate_answer(question):
    # 4.1 ค้นหาข้อมูลมาก่อน
    retrieved_docs = retrieve_data(question)
    
    if not retrieved_docs:
        return "ขออภัยครับ ไม่พบกฎหมายที่เกี่ยวข้องกับเรื่องนี้ในฐานข้อมูล"

    # 4.2 แปลงข้อมูลที่เจอเป็น Text ก้อนเดียว (Context)
    context_text = ""
    for doc in retrieved_docs:
        sec_num = doc.get('section_number', '?')
        text = doc.get('text_original', '')
        context_text += f"- มาตรา {sec_num}: {text}\n\n"

    print("   🤖 AI กำลังอ่านกฎหมายและเรียบเรียงคำตอบ...")

    # 4.3 สร้าง Prompt (คำสั่ง)
    template = """
    คุณคือทนายความผู้เชี่ยวชาญกฎหมายแรงงานไทย หน้าที่ของคุณคือตอบคำถามโดยอ้างอิงจาก "ข้อมูลกฎหมาย" ที่กำหนดให้เท่านั้น 
    
    ข้อมูลกฎหมาย:
    {context}
    
    คำถามจากผู้ใช้: {question}
    
    คำแนะนำการตอบ:
    1. ตอบให้กระชับ เข้าใจง่าย ภาษาเป็นธรรมชาติ
    2. ต้องระบุเลขมาตราที่ใช้อ้างอิงให้ชัดเจน (เช่น "ตามมาตรา 32...")
    3. ถ้าข้อมูลกฎหมายที่ให้ไปไม่พอที่จะตอบ ให้บอกตรงๆ ว่า "ข้อมูลไม่เพียงพอ" อย่าแต่งเรื่องเอง
    
    คำตอบ:
    """
    
    prompt = PromptTemplate(template=template, input_variables=["context", "question"])
    
    # 4.4 สร้าง Chain และรัน
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"context": context_text, "question": question})
    
    return answer

# --- ส่วนทดสอบ ---
if __name__ == "__main__":
    print("\n⚖️  ทนาย AI พร้อมให้คำปรึกษาแล้วครับ!")
    print("-----------------------------------")
    
    while True:
        user_input = input("\n🗣️  ถามมาได้เลยครับ (พิมพ์ 'ออก' เพื่อจบ): ")
        if user_input.strip() in ['ออก', 'exit', 'quit']:
            print("👋 ขอบคุณที่ใช้บริการครับ")
            break
            
        if user_input.strip():
            final_answer = generate_answer(user_input)
            print(f"\n💡 คำตอบ:\n{final_answer}")
            print("-" * 50)