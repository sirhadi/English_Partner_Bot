import os
import json
import random
import logging

logger = logging.getLogger(__name__)

# تعریف مسیرهای مطلق برای جلوگیری از خطای عدم یافتن پوشه در سرور
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATE_FILE = os.path.join(BASE_DIR, "state.json")


# ------------------------------------------------------------------------------
# 🔹 FUNCTION: load_all_book_words
# توضیح: خواندن تمام لغات از تمامی فایل‌های book_*.json در پوشه data
# ------------------------------------------------------------------------------
def load_all_book_words() -> list:
    all_words = []

    if not os.path.exists(DATA_DIR):
        logger.warning(f"پوشه {DATA_DIR} یافت نشد.")
        return all_words

    # مرتب‌سازی تمام فایل‌های کتاب (book_1.json, book_2.json, book_3.json و ...)
    book_files = sorted([f for f in os.listdir(DATA_DIR) if f.startswith("book_") and f.endswith(".json")])

    for file_name in book_files:
        file_path = os.path.join(DATA_DIR, file_name)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                words = json.load(f)
                if isinstance(words, list):
                    all_words.extend(words)
        except Exception as e:
            logger.error(f"خطا در خواندن فایل {file_name}: {e}")

    logger.info(f"تعداد کل واژگان بارگذاری شده از تمامی کتاب‌ها: {len(all_words)}")
    return all_words


# ------------------------------------------------------------------------------
# 🔹 FUNCTION: get_next_vocab_item
# توضیح: دریافت لغت بعدی به صورت ترتیبی بر اساس اندیس ذخیره‌شده در state.json
# ------------------------------------------------------------------------------
def get_next_vocab_item() -> dict:
    all_words = load_all_book_words()
    if not all_words:
        logger.error("هیچ لغتی در فایل‌های کتاب پیدا نشد.")
        return None

    current_index = 0
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
                current_index = state.get("vocab_index", 0)
        except Exception:
            current_index = 0

    # در صورت رسیدن به انتهای لیست، بازنشانی به کلمه اول
    if current_index >= len(all_words):
        current_index = 0

    vocab_item = all_words[current_index]

    # بروزرسانی اندیس برای فراخوانی بعدی
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"vocab_index": current_index + 1}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"خطا در به‌روزرسانی state.json: {e}")

    return vocab_item


# ------------------------------------------------------------------------------
# 🔹 FUNCTION: get_grammar_from_data
# توضیح: خواندن یک موضوع گرامری تصادفی از فایل‌های grammar_*.json
# ------------------------------------------------------------------------------
def get_grammar_from_data() -> dict:
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


# ------------------------------------------------------------------------------
# 🔹 FUNCTION: get_quote_from_data
# توضیح: خواندن یک نقل‌قول تصادفی از فایل‌های quote_*.json
# ------------------------------------------------------------------------------
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
                logger.error(f"خطا در خواندن نقل‌قول {filename}: {e}")
    return None


# ------------------------------------------------------------------------------
# 🔹 FUNCTION: get_idiom_from_data
# توضیح: خواندن یک اصطلاح تصادفی از فایل idioms_master.json
# ------------------------------------------------------------------------------
def get_idiom_from_data() -> dict:
    file_path = os.path.join(DATA_DIR, "idioms_master.json")
    if not os.path.exists(file_path):
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            idioms = json.load(f)
            if idioms and isinstance(idioms, list):
                return random.choice(idioms)
    except Exception as e:
        logger.error(f"خطا در بارگذاری اصطلاحات: {e}")
    return None
