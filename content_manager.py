import os
import json
import random
import logging

logger = logging.getLogger(__name__)

# مسیر مطلق پوشه data
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# ------------------------------------------------------------------------------
# 🔹 FUNCTION: load_all_book_words
# توضیح: خواندن تمام لغات از تمامی فایل‌های book_*.json در پوشه data
# ------------------------------------------------------------------------------
def load_all_book_words() -> list:
    data_dir = "data"
    all_words = []

    if not os.path.exists(data_dir):
        logger.warning(f"پوشه {data_dir} یافت نشد.")
        return all_words

    # لیست کردن و مرتب‌سازی تمام فایل‌های کتاب (book_1.json, book_2.json, book_3.json و ...)
    book_files = sorted([f for f in os.listdir(data_dir) if f.startswith("book_") and f.endswith(".json")])

    for file_name in book_files:
        file_path = os.path.join(data_dir, file_name)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                words = json.load(f)
                if isinstance(words, list):
                    all_words.extend(words)
        except Exception as e:
            logger.error(f"خطا در خواندن {file_name}: {e}")

    logger.info(f"تعداد کل واژگان بارگذاری شده از تمامی کتاب‌ها: {len(all_words)}")
    return all_words


# ------------------------------------------------------------------------------
# 🔹 FUNCTION: get_next_vocab_item
# توضیح: دریافت لغت بعدی بر اساس اندیس ذخیره‌شده یا انتخاب تصادفی
# ------------------------------------------------------------------------------
def get_next_vocab_item() -> dict:
    all_words = load_all_book_words()
    if not all_words:
        logger.error("هیچ لغتی در فایل‌های کتاب پیدا نشد.")
        return None

    # خواندن وضعیت اندیس از فایل state.json
    state_file = "state.json"
    current_index = 0
    
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
                current_index = state.get("vocab_index", 0)
        except Exception:
            current_index = 0

    # بررسی فراتر نرفتن اندیس از تعداد کل لغات
    if current_index >= len(all_words):
        current_index = 0

    vocab_item = all_words[current_index]

    # به‌روزرسانی اندیس برای ارسال بعدی
    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump({"vocab_index": current_index + 1}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"خطا در به‌روزرسانی state.json: {e}")

    return vocab_item

# ================== ۱. استخراج گرامر ==================
def get_grammar_from_data() -> dict:
    """
    خواندن مباحث گرامری از فایل‌های grammar_*.json
    فرمت فایل‌ها: ["Present Simple (...)", "Present Continuous (...)"]
    """
    if not os.path.exists(DATA_DIR):
        return None
        
    all_grammar_topics = []
    
    for filename in os.listdir(DATA_DIR):
        if filename.startswith("grammar_") and filename.endswith(".json"):
            file_path = os.path.join(DATA_DIR, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        # استخراج سطح از نام فایل (مثلاً grammar_a1_a2.json -> A1-A2)
                        level = filename.replace("grammar_", "").replace(".json", "").upper().replace("_", "-")
                        for topic in data:
                            if isinstance(topic, str):
                                all_grammar_topics.append({
                                    "level": level,
                                    "topic": topic
                                })
            except Exception as e:
                logger.error(f"خطا در خواندن فایل گرامر {filename}: {e}")
                
    if not all_grammar_topics:
        return None
        
    return random.choice(all_grammar_topics)


# ================== ۲. استخراج واژگان کتاب‌ها ==================
def load_all_vocab_data() -> list:
    """خواندن تمام فایل‌های کلمات (book_1.json, book_2.json و...)"""
    all_words = []
    if not os.path.exists(DATA_DIR):
        return all_words
        
    for filename in os.listdir(DATA_DIR):
        # خواندن فایل‌هایی که مربوط به گرامر و نقل‌قول نیستند
        if filename.endswith(".json") and not filename.startswith("grammar_") and not filename.startswith("quote"):
            file_path = os.path.join(DATA_DIR, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_words.extend(data)
            except Exception as e:
                logger.error(f"خطا در خواندن فایل {filename}: {e}")
                
    return all_words

def get_vocab_for_post() -> dict:
    """انتخاب یک کلمه از دیتابیس کلمات برای پست آموزشی یا کوییز"""
    words = load_all_vocab_data()
    if not words:
        return None
    return random.choice(words)


# ================== ۳. استخراج نقل‌قول ==================
def get_quote_from_data() -> dict:
    if not os.path.exists(DATA_DIR):
        return None
        
    for filename in os.listdir(DATA_DIR):
        if filename.startswith("quote") and filename.endswith(".json"):
            file_path = os.path.join(DATA_DIR, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        chosen = random.choice(data)
                        if isinstance(chosen, dict):
                            return chosen
                        elif isinstance(chosen, str):
                            return {"text": chosen, "author": "Unknown"}
            except Exception as e:
                logger.error(f"خطا در خواندن نقل‌قول: {e}")
    return None

#================== استخراج اصطلاحات =============
def get_idiom_from_data():
    try:
        file_path = os.path.join("data", "idioms_master.json")
        if not os.path.exists(file_path):
            # اگر در پوشه اصلی بود
            file_path = "idioms_master.json"

        with open(file_path, "r", encoding="utf-8") as f:
            idioms = json.load(f)
            if idioms and isinstance(idioms, list):
                return random.choice(idioms)
    except Exception as e:
        print(f"Error loading idiom: {e}")
    return None
