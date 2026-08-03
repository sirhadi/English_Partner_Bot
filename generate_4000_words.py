import os
import json
import time
from groq import Groq

# دریافت کلید API از متغیرهای محیطی یا وارد کردن مستقیم
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "YOUR_GROQ_API_KEY_HERE")

client = Groq(api_key=GROQ_API_KEY)
MODEL_NAME = "llama-3.3-70b-versatile"

# ساخت پوشه data در صورت عدم وجود
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def generate_unit_words(book_num: int, unit_num: int) -> list:
    """دریافت واژگان یک درس مشخص از هوش مصنوعی در قالب لیست JSON"""
    print(f"⏳ در حال تولید واژگان کتاب {book_num} - درس {unit_num}...")
    
    prompt = f"""
You are a precise data generator for the famous English vocabulary book series "4000 Essential English Words" by Paul Nation.

Target: Book {book_num}, Unit {unit_num} (Generate all target words for this specific unit, usually 20 words).

Return ONLY a valid JSON array of objects (no markdown blocks, no commentary).
Each object MUST follow this exact structure:
{{
  "word": "target_word",
  "phonetic": "/phonetic_pronunciation/",
  "translation_fa": "معنی دقیق فارسی",
  "definition_en": "Clear short English definition from the book",
  "book": {book_num},
  "unit": {unit_num}
}}

CRITICAL: Return ONLY raw JSON starting with '[' and ending with ']'.
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        
        response_text = completion.choices[0].message.content.strip()
        # پاکسازی تگ‌های احتمالی Markdown
        cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
        
        words_data = json.loads(cleaned_text)
        if isinstance(words_data, list):
            print(f"✅ با موفقیت {len(words_data)} واژه برای درس {unit_num} تولید شد.")
            return words_data
    except Exception as e:
        print(f"❌ خطا در ساخت درس {unit_num} از کتاب {book_num}: {e}")
    
    return []

def build_book_json(book_num: int, start_unit: int = 1, end_unit: int = 30):
    """ساخت یا به‌روزرسانی فایل JSON برای یک کتاب کامل (از درس ۱ تا ۳۰)"""
    file_path = os.path.join(DATA_DIR, f"book_{book_num}.json")
    
    existing_words = []
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                existing_words = json.load(f)
        except Exception:
            existing_words = []

    all_words = existing_words

    for unit in range(start_unit, end_unit + 1):
        # جلوگیری از تولید تکراری اگر درس از قبل موجود باشد
        already_exists = any(item.get("unit") == unit for item in all_words if isinstance(item, dict))
        if already_exists:
            print(f"ℹ️ کتاب {book_num} - درس {unit} قبلاً ساخته شده، رد می‌شود.")
            continue

        unit_words = generate_unit_words(book_num, unit)
        if unit_words:
            all_words.extend(unit_words)
            
            # ذخیره لحظه‌ای در فایل تا در صورت قطع ارتباط داده‌ها از دست نروند
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(all_words, f, ensure_ascii=False, indent=2)
            print(f"💾 فایل {file_path} به‌روزرسانی شد.")
            
        # تاخیر کوتاه برای جلوگیری از محدودیت Rate Limit در API
        time.sleep(2)

    print(f"\n🎉 ساخت کتاب {book_num} به پایان رسید! مجموع واژگان ذخیره‌شده: {len(all_words)}\n")

if __name__ == "__main__":
    print("🚀 شروع فرآیند ساخت فایل‌های دیتا برای ۴۰۰۰ واژه...\n")
    
    # نمونه: ساخت کتاب ۱ (درس ۱ تا ۳۰)
    # می‌توانید عدد کتاب را تغییر دهید یا حلقه برای کتاب‌های ۱ تا ۶ بگذارید
    book_to_generate = 1 
    
    build_book_json(book_num=book_to_generate, start_unit=1, end_unit=30)
