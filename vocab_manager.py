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
