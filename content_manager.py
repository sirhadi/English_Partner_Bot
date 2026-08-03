import os
import json
import random
import logging

logger = logging.getLogger(__name__)

# مسیر مطلق پوشه data
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


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
