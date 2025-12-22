import os
import time
from dotenv import load_dotenv
from supabase import create_client, Client
from langchain_huggingface import HuggingFaceEmbeddings

# 1. โหลดค่ากุญแจจากไฟล์ .env
load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("❌ Error: ไม่พบ SUPABASE_URL หรือ SUPABASE_KEY ในไฟล์ .env")
    exit(1)

# เชื่อมต่อ Supabase
supabase: Client = create_client(url, key)

print("⏳ กำลังโหลด Model (BAAI/bge-m3)... ครั้งแรกจะนานหน่อยนะครับ")
# ใช้ Model ตัวเทพสำหรับภาษาไทย
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")

def process_batch():
    # 2. ดึงข้อมูลที่ 'ยังไม่มี' embedding (ทีละ 10 แถว)
    try:
        response = supabase.table('act_sections') \
            .select('id, text_original, section_number') \
            .is_('embedding', 'null') \
            .limit(10) \
            .execute()
        
        rows = response.data
    except Exception as e:
        print(f"❌ Error การดึงข้อมูล: {e}")
        return False

    if not rows:
        print("\n🎉 ไชโย! ทำครบทุกมาตราแล้วครับ")
        return False

    print(f"\n📦 เจอ {len(rows)} มาตราที่ต้องทำ... กำลังประมวลผล")

    # 3. วนลูปแปลงร่าง
    for row in rows:
        text = row['text_original']
        section_num = row['section_number']
        row_id = row['id']
        
        if not text or text.strip() == "":
            print(f"⚠️ มาตรา {section_num} ว่างเปล่า -> ข้าม")
            continue
            
        try:
            # แปลงข้อความเป็น Vector
            vector = embeddings.embed_query(text)
            
            # อัปเดตกลับลง DB
            supabase.table('act_sections') \
                .update({'embedding': vector}) \
                .eq('id', row_id) \
                .execute()
            
            print(f"  ✅ บันทึกมาตรา {section_num} สำเร็จ")
            
        except Exception as e:
            print(f"  ❌ พลาดที่มาตรา {section_num}: {e}")

    return True

if __name__ == "__main__":
    print("🚀 เริ่มต้นกระบวนการ Embedding...")
    while True:
        has_more = process_batch()
        if not has_more:
            break
        # พักหายใจนิดนึง กัน Database สำลัก
        time.sleep(0.5)