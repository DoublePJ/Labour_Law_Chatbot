import os
from dotenv import load_dotenv
from supabase import create_client, Client
from langchain_huggingface import HuggingFaceEmbeddings

# 1. โหลดค่า Config
load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("❌ Error: ไม่พบค่า Config ในไฟล์ .env")
    exit()

# เชื่อมต่อ Supabase
supabase: Client = create_client(url, key)

print("⏳ กำลังโหลด Model ค้นหา (BAAI/bge-m3)...")
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")

def search_law(query_text):
    print(f"\n🔍 กำลังค้นหา: '{query_text}'")
    
    # 2. แปลงคำถามของเราเป็น Vector
    query_vector = embeddings.embed_query(query_text)
    
    # 3. ส่งไปถาม Supabase (เรียกใช้ Function match_act_sections ที่เราสร้างไว้)
    params = {
        "query_embedding": query_vector,
        "match_threshold": 0.4, # ความเหมือนขั้นต่ำ (ปรับลดลงได้ถ้าหาไม่เจอ)
        "match_count": 3        # เอามาแค่ 3 อันดับแรก
    }
    
    try:
        response = supabase.rpc("match_sections_v2", params).execute()
        
        # 4. แสดงผลลัพธ์
        if not response.data:
            print("❌ ไม่พบกฎหมายที่เกี่ยวข้องเลย (ลองเปลี่ยนคำค้นหาดูครับ)")
            return

        print(f"✅ เจอ {len(response.data)} มาตราที่เกี่ยวข้อง:\n")
        for i, item in enumerate(response.data):
            similarity = item.get('similarity', 0)
            sec_num = item.get('section_number', '?')
            content = item.get('text_original', '')
            
            print(f"--- อันดับ {i+1} (ความมั่นใจ {similarity:.1%}) ---")
            print(f"📜 มาตรา {sec_num}")
            print(f"เนื้อหา: {content[:200]}...") # ตัดมาโชว์แค่สั้นๆ
            print("-" * 50)
            
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")

if __name__ == "__main__":
    print("\n🤖 ระบบค้นหากฎหมายแรงงานพร้อมทำงานแล้ว!")
    while True:
        user_input = input("\n🗣️ พิมพ์คำถามกฎหมาย (หรือพิมพ์ 'ออก' เพื่อจบ): ")
        if user_input.strip() in ['ออก', 'exit', 'quit']:
            print("👋 บ๊ายบาย")
            break
        
        if user_input.strip():
            search_law(user_input)