import os
import json
import random
import logging

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def load_all_vocab_data() -> list:
    all_items = []
    if not os.path.exists(DATA_DIR):
        logger.warning(f"پوشه {DATA_DIR} یافت نشد.")
        return all_items
        
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json"):
            file_path = os.path.join(DATA_DIR, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        all_items.extend(data)
            except Exception as e:
                logger.error(f"خطا در خواندن فایل {filename}: {e}")
                
    return all_items

def get_vocab_for_post() -> dict:
    """
    انتخاب یک واژه از فایل‌های JSON برای ساخت پست آموزشی
    """
    items = load_all_vocab_data()
    if not items:
        return None
        
    valid_items = [item for item in items if "vocabulary" in item]
    if not valid_items:
        return None
        
    chosen = random.choice(valid_items)
    vocab = chosen["vocabulary"]
    
    return {
        "word": vocab.get("word"),
        "phonetic": vocab.get("phonetic", ""),
        "part_of_speech": vocab.get("part_of_speech", ""),
        "translation_fa": vocab.get("translation_fa", ""),
        "definition_en": vocab.get("definition_en", ""),
        "examples": vocab.get("examples", []),
        "book": chosen.get("book", 3),
        "unit": chosen.get("unit", 1)
    }

def get_quiz_from_data() -> dict:
    """
    انتخاب یک کوییز از فایل‌های JSON
    """
    items = load_all_vocab_data()
    if not items:
        return None
        
    valid_items = [item for item in items if "quiz" in item and "vocabulary" in item]
    if not valid_items:
        return None
        
    chosen = random.choice(valid_items)
    quiz = chosen["quiz"]
    vocab = chosen["vocabulary"]
    book_num = chosen.get("book", 3)
    unit_num = chosen.get("unit", 1)
    
    return {
        "level": f"کتاب {book_num} - درس {unit_num} (کلمه: {vocab.get('word')})",
        "question": quiz.get("question"),
        "options": quiz.get("options"),
        "correct_option_index": quiz.get("correct_option_index", 0),
        "explanation": quiz.get("explanation", f"معنی: {vocab.get('translation_fa')}")
    }

def get_quote_from_data() -> dict:
    """
    انتخاب یک نقل‌قول از فایل‌های JSON موجود در پوشه data
    (چه از فایل اختصاصی quotes.json باشد یا کلید quote درون بقیه فایل‌ها)
    """
    items = load_all_vocab_data()
    if not items:
        return None
        
    valid_quotes = []
    for item in items:
        # پشتیبانی از ساختارهای مختلف ذخیره‌سازی نقل‌قول در JSON
        if "quote" in item:
            valid_quotes.append(item["quote"])
        elif "quote_text" in item:
            valid_quotes.append(item)
            
    if not valid_quotes:
        return None
        
    chosen = random.choice(valid_quotes)
    
    # خروجی استاندارد شده
    if isinstance(chosen, dict):
        return {
            "text": chosen.get("text") or chosen.get("quote_text"),
            "author": chosen.get("author", "Unknown"),
            "category": chosen.get("category", "Wisdom")
        }
    return None

def get_grammar_from_data() -> dict:
    """
    استخراج یک مبحث گرامری از فایل‌های JSON
    """
    items = load_all_vocab_data()
    if not items:
        return None
        
    valid_grammar = [item for item in items if "grammar" in item]
    if not valid_grammar:
        return None
        
    chosen = random.choice(valid_grammar)
    grammar = chosen["grammar"]
    
    return {
        "title": grammar.get("title", ""),
        "structure": grammar.get("structure", ""),
        "explanation_fa": grammar.get("explanation_fa", ""),
        "examples": grammar.get("examples", []),
        "book": chosen.get("book", 3),
        "unit": chosen.get("unit", 1)
    }

def get_grammar_from_data() -> dict:
    """
    استخراج یک مبحث گرامری از فایل‌های اختصاصی گرامر (مانند grammar_a1_a2.json)
    """
    if not os.path.exists(DATA_DIR):
        return None
        
    all_grammar_items = []
    
    for filename in os.listdir(DATA_DIR):
        # بررسی اختصاصی فایل‌های گرامر
        if filename.startswith("grammar_") and filename.endswith(".json"):
            file_path = os.path.join(DATA_DIR, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            # استخراج سطح از نام فایل (مثلاً grammar_a1_a2.json -> A1-A2)
                            level_from_filename = filename.replace("grammar_", "").replace(".json", "").upper().replace("_", "-")
                            
                            # اگر داخل خود JSON سطح بود از آن استفاده می‌کند، وگرنه از اسم فایل
                            item_level = item.get("level", level_from_filename)
                            grammar_obj = item.get("grammar", item)
                            
                            if "title" in grammar_obj or "structure" in grammar_obj:
                                all_grammar_items.append({
                                    "level": item_level,
                                    "title": grammar_obj.get("title", ""),
                                    "structure": grammar_obj.get("structure", ""),
                                    "explanation_fa": grammar_obj.get("explanation_fa", ""),
                                    "examples": grammar_obj.get("examples", [])
                                })
            except Exception as e:
                logger.error(f"خطا در خواندن فایل گرامر {filename}: {e}")
                
    if not all_grammar_items:
        return None
        
    return random.choice(all_grammar_items)
