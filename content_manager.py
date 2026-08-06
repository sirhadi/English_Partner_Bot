import os
import re
import json
import random
import logging

# تنظیم لاگر برای ثبت گزارش‌ها و خطاهای سیستم
logger = logging.getLogger(__name__)

# تعیین مسیرهای پایه پروژه
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")        # پوشه قرارگیری فایل‌های JSON
STATE_FILE = os.path.join(BASE_DIR, "state.json") # فایل ذخیره آخرین وضعیت ارسال لغات (Index)

# آدرس‌دهی مطلق جهت جلوگیری از خطای آدرس در سرور Render
IDIOMS_FILE = os.path.join(BASE_DIR, "data", "idioms_master.json")

# آدرس‌دهی دقیق فایل نقل‌قول‌ها
QUOTES_FILE = os.path.join(BASE_DIR, "data", "quotes.json")

# ==============================================================================
# 📘 راهنمای تابع: load_all_book_words
# 🎯 هدف: خواندن و ادغام تمامی لغات از فایل‌های book_*.json بر اساس شماره کتاب
# 📥 ورودی: ندارد
# 📤 خروجی: لیست (list) شامل تمام لغات موجود در پوشه data
# 🔗 کاربرد: فراخوانی توسط تابع get_next_vocab_item برای استخراج لغت بعدی
# ==============================================================================
def load_all_book_words() -> list:
    all_words = []

    if not os.path.exists(DATA_DIR):
        logger.warning(f"پوشه {DATA_DIR} یافت نشد.")
        return all_words

    def extract_book_number(filename):
        match = re.search(r'book_(\d+)', filename)
        return int(match.group(1)) if match else 0

    book_files = [f for f in os.listdir(DATA_DIR) if f.startswith("book_") and f.endswith(".json")]
    book_files.sort(key=extract_book_number)

    for file_name in book_files:
        file_path = os.path.join(DATA_DIR, file_name)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                words = json.load(f)
                if isinstance(words, list):
                    all_words.extend(words)
        except Exception as e:
            logger.error(f"خطا در خواندن فایل {file_name}: {e}")

    logger.info(f"تعداد کل واژگان بارگذاری شده: {len(all_words)}")
    return all_words


# ==============================================================================
# 📘 راهنمای تابع: get_next_vocab_item
# 🎯 هدف: دریافت لغت بعدی به صورت منظم و ترتیبی + بروزرسانی ایندکس در state.json
# 📥 ورودی: ندارد
# 📤 خروجی: دیکشنری (dict) شامل مشخصات لغت (word, translation, definition, book, unit)
# 🔗 کاربرد: استفاده در مسیر /post_vocab سرور Flask
# ==============================================================================
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

    if current_index >= len(all_words):
        current_index = 0

    vocab_item = all_words[current_index]

    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"vocab_index": current_index + 1}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"خطا در به‌روزرسانی state.json: {e}")

    return vocab_item


# ==============================================================================
# 📘 راهنمای تابع: get_grammar_from_data
# 🎯 هدف: انتخاب تصادفی یک مبحث گرامری از فایل‌های grammar_*.json
# 📥 ورودی: ندارد
# 📤 خروجی: دیکشنری (dict) شامل topic و level گرامر
# 🔗 کاربرد: فراخوانی توسط مسیر /grammar_data
# ==============================================================================
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
                                all_grammar_topics.append({"level": level, "topic": topic})
                            elif isinstance(topic, dict):
                                all_grammar_topics.append({"level": level, "topic": topic.get("topic", "")})
            except Exception as e:
                logger.error(f"خطا در خواندن فایل گرامر {filename}: {e}")
                
    return random.choice(all_grammar_topics) if all_grammar_topics else None


# ==============================================================================
# 📘 راهنمای تابع: get_quote_from_data
# 🎯 هدف: استخراج یک نقل‌قول تصادفی از فایل‌های quote_*.json
# 📥 ورودی: ندارد
# 📤 خروجی: دیکشنری (dict) شامل متن نقل‌قول (text) و نویسنده (author)
# 🔗 کاربرد: فراخوانی توسط مسیر /quote
# ==============================================================================

# ==============================================================================
# 📘 راهنمای تابع: get_quote_from_data
# 🎯 هدف: خواندن فایل quotes.json و انتخاب تصادفی یک نقل‌قول
# 📥 ورودی: ندارد
# 📤 خروجی: متن نقل‌قول یا دیکشنری اطلاعات آن
# ==============================================================================
def get_quote_from_data():
    """
    خواندن فایل کلی نقل‌قول‌ها و انتخاب تصادفی یک مورد.
    """
    if not os.path.exists(QUOTES_FILE):
        logger.error(f"فایل نقل‌قول‌ها یافت نشد: {QUOTES_FILE}")
        return None

    try:
        with open(QUOTES_FILE, "r", encoding="utf-8") as f:
            quotes_list = json.load(f)

        if not quotes_list:
            logger.error("فایل quotes.json خالی است.")
            return None

        # انتخاب تصادفی یک نقل‌قول
        return random.choice(quotes_list)

    except Exception as e:
        logger.error(f"Error reading quotes file: {e}")
        return None


# ==============================================================================
# 📘 راهنمای تابع: get_idiom_from_data
# 🎯 هدف: خواندن فایل idioms_master.json و انتخاب تصادفی یک اصطلاح از لیست
# 📥 ورودی: ندارد
# 📤 خروجی: دیکشنری اطلاعات اصطلاح انتخاب‌شده (اصطلاح، معنی، مثال و...)
# 🔗 کاربرد: فراخوانی توسط مسیر /idiom
# ==============================================================================
# در فایل content_manager.py

def get_idiom_from_data() -> str:
    """
    خواندن فایل کلی اصطلاحات و انتخاب یک مورد به صورت کاملاً تصادفی.
    """
    if not os.path.exists(IDIOMS_FILE):
        raise FileNotFoundError(f"فایل اصطلاحات پیدا نشد: {IDIOMS_FILE}")

    with open(IDIOMS_FILE, "r", encoding="utf-8") as f:
        idioms_list = json.load(f)

    if not idioms_list:
        raise ValueError("فایل idioms_master.json خالی است.")

    # انتخاب تصادفی یک اصطلاح (رشته متنی) از بین تمام اعضای لیست
    return random.choice(idioms_list)
