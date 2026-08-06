import os
import re
import json
import random
import logging
import asyncio
import requests
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify, send_file
from groq import Groq

# فراخوانی توابع مدیریت محتوا
from content_manager import (
    get_next_vocab_item,
    get_grammar_from_data,
    get_quote_from_data,
    get_idiom_from_data,
    load_all_book_words
)
# آدرس‌دهی مطلق برای جلوگیری از خطای مسیر در سرور Render
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# ==============================================================================
# ⚙️ تنظیمات اولیه و متغیرهای محیطی
# ==============================================================================
BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID") or os.getenv("TELEGRAM_CHANNEL_ID") or "0"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# راه‌اندازی Groq Client
client = Groq(api_key=GROQ_API_KEY, timeout=20.0)
MODEL_NAME = "llama-3.3-70b-versatile"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

TOPICS = [
    "یک کلمه یا اصطلاح انگلیسی روزمره با معنی فارسی، مثال و تلفظ فونتیک آن",
    "یک نکته گرامری کوتاه و کاربردی انگلیسی با فرمول",
    "یک دیالوگ انگلیسی کوتاه دو نفره مناسب تمرین مکالمه و پارتنریابی",
    "یک اصطلاح idiom انگلیسی با معنی و مثال",
    "یک سوال جالب انگلیسی برای شروع مکالمه بین پارتنرهای زبانی به همراه مثال و ترجمه فارسی",
    "یک جوک یا عبارت طنز انگلیسی",
    "یک اصطلاح مبتدی، متوسط یا پیشرفته Idiom یا Phrasal Verb با معنی دقیق، مثال و مترادف",
    "یک ساختار گرامری سطح متوسط، متوسط به بالا و بالا تا C1 با فرمول ساخت اون ساختار گرامری و مثال کاربردی",
    "یک عبارت کاربردی برای بحث های آکادمیک و بیزینس Professional English",
    "یک اشتباه رایج زبان آموزان ایرانی در انگلیسی و شکل درست آن"
]


# ==============================================================================
# 📘 راهنمای تابع: clean_text
# 🎯 هدف: پاکسازی کاراکترهای مخرب، چینی یا روسی احتمالی در خروجی هوش مصنوعی
# 📥 ورودی: text (رشته متنی)
# 📤 خروجی: رشته متنی تمیز شده بدون کاراکترهای نامتعارف
# ==============================================================================
def clean_text(text: str) -> str:
    if not text:
        return text
    bad_chars_pattern = r'[\u0400-\u04FF\u4E00-\u9FFF\u3400-\u4DBF\u3000-\u303F]'
    return re.sub(bad_chars_pattern, '', text)


# ==============================================================================
# 📘 راهنمای تابع: get_time_context
# 🎯 هدف: محاسبه ساعت جاری به وقت تهران برای شخصی‌سازی سلام بر اساس زمان روز
# 📥 ورودی: ندارد
# 📤 خروجی: یکی از کلمات Morning / Afternoon / Evening / Night
# ==============================================================================
def get_time_context() -> str:
    tehran_time = datetime.now(timezone.utc) + timedelta(hours=3, minutes=30)
    hour = tehran_time.hour
    if 5 <= hour < 12:
        return "Morning"
    elif 12 <= hour < 17:
        return "Afternoon"
    elif 17 <= hour < 22:
        return "Evening"
    else:
        return "Night"


# ==============================================================================
# 📘 راهنمای تابع: process_telegram_update
# 🎯 هدف: پردازش پیام‌های دریافتی از تلگرام (پاسخ به دستورات مانند /start)
# 📥 ورودی: update_dict (دیکشنری اطلاعات وب‌هوک تلگرام)
# 📤 خروجی: ندارد (به صورت async کار می‌کند)
# ==============================================================================
async def process_telegram_update(update_dict: dict):
    try:
        if "message" in update_dict:
            message = update_dict["message"]
            chat_id = message.get("chat", {}).get("id")
            text = message.get("text", "")
            if text == "/start":
                send_telegram_message("سلام! ربات هوشمند آموزش انگلیسی فعال است.")
    except Exception as e:
        logger.error(f"Error processing update: {e}")

# =================================
#   انتخاب تصادفی یک لغت از فایل‌های book_*.json در پوشه data
#    و استخراج خودکار شماره کتاب از نام فایل.
# =================================
def get_random_vocab() -> dict:
    """
    انتخاب تصادفی یک لغت از فایل‌های book_*.json در پوشه data
    و استخراج خودکار شماره کتاب از نام فایل.
    """
    if not os.path.exists(DATA_DIR):
        raise FileNotFoundError(f"پوشه data پیدا نشد: {DATA_DIR}")

    book_files = [f for f in os.listdir(DATA_DIR) if f.startswith("book_") and f.endswith(".json")]
    if not book_files:
        raise FileNotFoundError("هیچ فایلی با نام book_*.json در پوشه data وجود ندارد.")

    # انتخاب تصادفی یک فایل کتاب
    selected_book = random.choice(book_files)
    file_path = os.path.join(DATA_DIR, selected_book)

    # استخراج شماره کتاب از نام فایل (مثلاً book_3.json -> 3)
    try:
        book_number = int(selected_book.replace("book_", "").replace(".json", ""))
    except ValueError:
        book_number = 1

    with open(file_path, "r", encoding="utf-8") as f:
        words = json.load(f)

    if not words:
        raise ValueError(f"فایل {selected_book} خالی است.")

    vocab_item = random.choice(words)

    # تنظیم شماره کتاب در واژه در صورتی که در JSON وجود نداشته باشد
    if isinstance(vocab_item, dict):
        if "book" not in vocab_item or not vocab_item["book"]:
            vocab_item["book"] = book_number

    return vocab_item

# ==============================================================================
# 📘 راهنمای تابع: generate_educational_post
# 🎯 هدف: تولید یک پست آموزشی عمومی انگلیسی با استفاده از مدل Groq
# 📥 ورودی: ندارد
# 📤 خروجی: متن کامل پست با فرمت HTML تلگرام
# 🔗 کاربرد: استفاده در مسیر /post
# ==============================================================================
def generate_educational_post() -> str:
    chosen_topic = random.choice(TOPICS)
    time_context = get_time_context()
    random_seed = random.randint(1000, 9999)
    
    prompt = f"""
You are a warm and expert English teacher creating a useful and beautifully formatted Telegram post for an Iranian Telegram group. The level is intermediate to advanced (B2-C1). Current time context: {time_context}.
Unique Request ID: {random_seed}

Topic: {chosen_topic}

Generate a complete educational post following this EXACT layout and emoji style:

🟢 <b>Level: B2-C1</b>

😍 <b>[Creative dynamic native English greeting loosely matching {time_context} + natural Persian translation]</b>
📌 <b>[Topic Title in English & Persian]</b>

🔴 <b>[Main Phrase / Word / Structure]</b> [phonetic pronunciation in brackets if applicable]
🔹 <b>معنی:</b> [Short explanation in Persian]

🟢 <b>مثال اول:</b>
📣 [English sentence with the target phrase wrapped in <b>tags</b>]
🔹 <b>ترجمه:</b> [Persian translation]

🟡 <b>مثال دوم:</b>
🔔 [English sentence with the target phrase wrapped in <b>tags</b>]
🔸 <b>ترجمه:</b> [Persian translation]

👨‍🏫 <b>نقل‌قول / نکته طلایی:</b>
"A short English quote related to learning or life"
💬 <b>ترجمه:</b> "ترجمه فارسی نقل‌قول"

👩‍🏫 <b>حالا جواب این سوال و تو بده:</b>
[An engaging question in English related to the topic]
🟣 [ترجمه فارسی سوال برای شروع بحث در کامنت‌ها]

CRITICAL RULES:
1. ALL bold texts MUST be wrapped in <b> and </b> HTML tags. DO NOT use asterisks (*).
2. Give actual, practical teaching content with clear Persian translations on separate lines.
3. Output ONLY the final post text.
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return clean_text(completion.choices[0].message.content.strip())
    except Exception as e:
        logger.error(f"Post Error: {e}")
        return None


# ==============================================================================
# 📘 راهنمای تابع: generate_educational_post_vocab
# 🎯 هدف: ساخت پست کامل آموزشی اختصاصی برای یک لغت مشخص از کتاب‌ها
# 📥 ورودی: vocab_item (دیکشنری اطلاعات لغت یا رشته)
# 📤 خروجی: متن کامل پست با رعایت تگ‌های HTML
# 🔗 کاربرد: استفاده در مسیر /post_vocab
# ==============================================================================
#== ما دو تا تابع انتخاب تصادفی واژه داریم. که فکر کنم اگه این رو حذف کنیم مشکلی نباشه.
# چون تابع های پایین همه از vocab_item دارن استفاده می کنن

# ===============
def generate_educational_post_vocab(vocab_item) -> str:
    if not vocab_item:
        return None

    word = ""
    phonetic = ""
    translation = ""
    definition = ""
    book = 1
    unit = 1

    if isinstance(vocab_item, str):
        word = vocab_item.strip()
    elif isinstance(vocab_item, dict):
        word = vocab_item.get("word") or vocab_item.get("vocab") or vocab_item.get("text") or ""
        phonetic = vocab_item.get("phonetic") or vocab_item.get("pronunciation") or ""
        translation = vocab_item.get("translation_fa") or vocab_item.get("meaning") or ""
        definition = vocab_item.get("definition_en") or vocab_item.get("definition") or ""
        book = vocab_item.get("book", 1)
        unit = vocab_item.get("unit", 1)

    if not word:
        return None

    time_context = get_time_context()
    
    prompt = f"""
You are an expert English teacher creating a Telegram post to teach a specific word or phrase for Book {book}, Unit {unit}.

Target Word/Phrase: {word}
Phonetic: {phonetic if phonetic else "Provide accurate IPA phonetic pronunciation in brackets"}
Persian Meaning: {translation if translation else "Provide accurate fluent Persian translation"}
English Definition: {definition if definition else "Provide a short clear English definition"}

Format the post EXACTLY using HTML tags (NO asterisks *):

🟢 <b>4000 E. Words Book {book} - Unit {unit}</b>

😍 <b>[Greeting in Persian matching {time_context}]</b>
📌 <b>واژه / اصطلاح روز:</b>
🔴 <b>{word}</b> {phonetic if phonetic else ""}
🔹 <b>معنی:</b> {translation if translation else "[Persian translation]"}
📖 <b>Deffinition:\n</b> {definition if definition else "[English definition]"}

🟢 <b>مثال اول:</b>
📣 [English sentence using <b>{word}</b>]
🔹 <b>ترجمه:</b> [Persian translation]

🟡 <b>مثال دوم:</b>
🔔 [Another English sentence using <b>{word}</b>]
🔸 <b>ترجمه:</b> [Persian translation]

👩‍🏫 <b>حالا تو بگو:</b>
[An interactive question asking members to use <b>{word}</b> in a sentence]
🟣 [ترجمه سوال به فارسی]

CRITICAL RULES:
1. Use ONLY <b> tags for bold text. Do NOT use asterisks (*).
2. Write English and Persian on separate lines.
3. Complete any missing translations or definitions accurately.
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return clean_text(completion.choices[0].message.content.strip())
    except Exception as e:
        logger.error(f"Post Vocab Error: {e}")
        return None

# ==============================================================================
# 📘 راهنمای تابع: generate_quiz_data
# 🎯 هدف: تولید خودکار آزمون ۴ گزینه‌ای عمومی انگلیسی با هوش مصنوعی در سطوح و موضوعات مختلف
# 📥 ورودی: ندارد
# 📤 خروجی: دیکشنری شامل سوال، ۴ گزینه، مشخصه پاسخ صحیح و تحلیل فارسی
# 🔗 کاربرد: استفاده در مسیر /send_quiz جهت ارسال آزمون‌های عمومی و متنوع گرامری/اصطلاحات
# ==============================================================================
def generate_quiz_data() -> dict:
    """
    تولید یک آزمون عمومی ۴ گزینه‌ای هوشمند با انتخاب تصادفی سطح (A1 تا C1) 
    و موضوعات متنوع مانند گرامر، افعال مرکب، حروف اضافه و اصطلاحات.
    """
    # لیست موضوعات مختلف زبان برای تنوع در آزمون‌ها
    topics = [
        "English Grammar & Tenses",
        "Prepositions of Time and Place",
        "Phrasal Verbs & Idioms",
        "Common Collocations & Expressions",
        "Articles & Quantifiers",
        "Vocabulary in Context"
    ]
    
    # لیست سطوح زبان
    levels = [
        "مقدماتی (A1-A2)", 
        "متوسط (B1-B2)", 
        "پیشرفته (C1)"
    ]
    
    # انتخاب تصادفی یک موضوع و یک سطح در هر بار اجرای تابع
    selected_topic = random.choice(topics)
    selected_level = random.choice(levels)

    prompt = f"""
Create a high-quality English multiple-choice quiz question for Persian learners.

Topic: {selected_topic}
Level: {selected_level}

CRITICAL INSTRUCTIONS:
1. Return ONLY a valid JSON object. Do NOT include markdown blocks like ```json ... ``` or any other extra text.
2. Ensure the correct answer is NOT always in index 0. Shuffle the options conceptually or set correct_option_index correctly.
3. Write a helpful explanation in Persian.

JSON Format:
{{
  "level": "{selected_level} | {selected_topic}",
  "question": "Clear sentence with a blank (___) testing the topic.",
  "options": ["Option A", "Option B", "Option C", "Option D"],
  "correct_option_index": 0,
  "explanation": "توضیح کامل فارسی درباره علت درستی پاسخ و نکته گرامری یا معنایی آن"
}}
"""

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        raw_text = completion.choices[0].message.content.strip()

        # استخراج دقیق ساختار JSON جهت جلوگیری از خطای فرمت
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            clean_json_str = match.group(0)
            return json.loads(clean_json_str)
        else:
            logger.error(f"Quiz Data JSON extraction failed. Raw text: {raw_text}")
            return None

    except Exception as e:
        logger.error(f"Generate Quiz Data Error: {e}")
        return None

# ==============================================================================
# 📘 راهنمای تابع: generate_quiz_from_vocab_item
# 🎯 هدف: تولید آزمون ۴ گزینه‌ای مرتبط با لغتی که دقیقاً همان لحظه ارسال شده
# 📥 ورودی: vocab_item (اطلاعات واژه)
# 📤 خروجی: دیکشنری با فرمت مناسب ساخت نظرسنجی تلگرام (Poll)
# 🔗 کاربرد: استفاده همزمان در مسیر /quiz_vocab
# ==============================================================================
def generate_quiz_from_vocab_item(vocab_item) -> dict:
    """
    تولید آزمون ۴ گزینه‌ای مرتبط با واژه دریافتی
    """
    if not vocab_item:
        return None

    word = vocab_item.get("word") if isinstance(vocab_item, dict) else str(vocab_item)
    book = vocab_item.get("book", 1) if isinstance(vocab_item, dict) else 1
    unit = vocab_item.get("unit", 1) if isinstance(vocab_item, dict) else 1

    prompt = f"""
Create a Telegram quiz question to test this word: {word}
Book {book}, Unit {unit}

Return ONLY raw JSON (no code blocks):
{{
  "level": "📘4000 واژه جلد {book} - یونیت {unit}",
  "question": "Fill-in-the-blank sentence where '{word}' fits.",
  "options": ["{word}", "WrongOption1", "WrongOption2", "WrongOption3"],
  "correct_option_index": 0,
  "explanation": "توضیح پاسخ و معنی واژه {word} به فارسی"
}}
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        text = completion.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text(text))
    except Exception as e:
        logger.error(f"Quiz Vocab Error: {e}")
        return None

# ==============================================================================
# 📘 راهنمای تابع: generate_news_post
# 🎯 هدف: ساخت پست خبری انگلیسی با کلمات کلیدی و ترجمه مخفی (Spoiled Quote)
# 📥 ورودی: ندارد
# 📤 خروجی: متن کامل خبر به فرمت HTML
# 🔗 کاربرد: استفاده در مسیر /news
# ==============================================================================
def generate_news_post() -> str:
    time_seed = datetime.now().strftime("%Y%m%d%H%M%S")
    prompt = f"""
Write a short, simple, real-world style English news summary suitable for English learners (B2-C1 level).
Seed: {time_seed}

Format strictly using HTML:
📰 <b>English News Summary ([level])</b>

📌 <b>[Headline in English]</b>

[Write 3-4 simple sentences explaining the news story in English. Wrap 2-3 key words in <b> tags]

✍️ <b>کلمات کلیدی:</b>
🔹 <b>word1</b>: معنی فارسی
🔹 <b>word2</b>: معنی فارسی
🔹 <b>word3</b>: معنی فارسی

<b>ترجمه (برای باز شدن لمس کنید):</b>
<blockquote expandable>
[Full Persian translation here]
</blockquote>

CRITICAL RULES:
1. Wrap translation in <blockquote expandable> and </blockquote>.
2. Output ONLY the final post text.
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return clean_text(completion.choices[0].message.content.strip())
    except Exception as e:
        logger.error(f"News Error: {e}")
        return None


# ==============================================================================
# 📘 راهنمای تابع: generate_grammar_post_vocab
# 🎯 هدف: تولید پست آموزشی گرامر بر اساس موضوع دریافت شده از JSON
# 📥 ورودی: grammar_item (دیکشنری شامل topic و level)
# 📤 خروجی: متن آموزش گرامر شامل فرمول و مثال
# 🔗 کاربرد: استفاده در مسیر /grammar_data
# ==============================================================================
def generate_grammar_post_vocab(grammar_item) -> str:
    topic = grammar_item.get("topic", "Grammar Lesson") if isinstance(grammar_item, dict) else str(grammar_item)
    level = grammar_item.get("level", "B1-B2") if isinstance(grammar_item, dict) else "B1-B2"

    prompt = f"""
You are an English teacher. Create a educational post for Telegram about this topic:
Topic: {topic}
Level: {level}

Format strictly using HTML:
📚 <b>آموزش گرامر ({level})</b>

📌 <b>{topic}</b>

💡 <b>توضیح:</b>
[Clear explanation in Persian]

📝 <b>فرمول / ساختار:</b>
<code>[Structure formula]</code>

🟢 <b>مثال:</b>
📣 [English Example]
🔹 <b>ترجمه:</b> [Persian translation]
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return clean_text(completion.choices[0].message.content.strip())
    except Exception as e:
        logger.error(f"Grammar Vocab Error: {e}")
        return None


# ==============================================================================
# 📘 راهنمای تابع: generate_quote_post
# 🎯 هدف: تولید پست نقل‌قول (Quote of the Day) همراه با ترجمه و تحلیل به فارسی
# 📥 ورودی: quote_item (اختیاری - رشته یا دیکشنری شامل متن نقل‌قول و نویسنده)
# 📤 خروجی: متن آماده ارسال پست تلگرام
# 🔗 کاربرد: استفاده در مسیر /quote
# ==============================================================================
def generate_quote_post(quote_item=None) -> str:
    """
    تولید متن پست آموزشی/انگیزشی نقل‌قول روز با هوش مصنوعی.
    """
    if not quote_item:
        quote_item = get_quote_from_data()

    if not quote_item:
        logger.error("هیچ نقل‌قولی برای تولید پست دریافت نشد.")
        return None

    # استخراج متن و گوینده (چه فایل به صورت لیست متنی باشد چه دیکشنری)
    if isinstance(quote_item, dict):
        quote_str = quote_item.get("quote") or quote_item.get("text") or quote_item.get("statement") or ""
        author_str = quote_item.get("author") or quote_item.get("by") or "Unknown"
    elif isinstance(quote_item, str):
        quote_str = quote_item.strip()
        author_str = "Unknown"
    else:
        quote_str = str(quote_item)
        author_str = "Unknown"

    if not quote_str:
        return None

    prompt = f"""
Create an inspiring Telegram post for this English quote:
Quote: "{quote_str}"
Author: {author_str}

Format:
🐣 <b>نقل‌قول روز (Quote of the Day)</b>

💬 <i>"{quote_str}"</i>
✍️ <b>— {author_str}</b>

🔹 <b>ترجمه فارسی:</b> [Persian translation]
✨ <b>پیام کوتاه:</b> [A short inspiring 1-line thought in Persian]

CRITICAL RULES:
1. Use ONLY <b> and <i> tags. Do NOT use markdown asterisks (*).
2. Keep line breaks clean and layout professional.
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return clean_text(completion.choices[0].message.content.strip())
    except Exception as e:
        logger.error(f"Quote Error: {e}")
        return None

# ==============================================================================
# 📘 راهنمای تابع: generate_story_post
# 🎯 هدف: ساخت داستان کوتاه سطح متوسط همراه با ترجمه مخفی کشویی
# 📥 ورودی: ندارد
# 📤 خروجی: متن کامل داستان با فرمت HTML
# 🔗 کاربرد: استفاده در مسیر /story
# ==============================================================================
def generate_story_post() -> str:
    prompt = """
Write a short English story for B2-C1 learners (5-7 sentences).

Format strictly with HTML:
📖 <b>Short Story ([level])</b>
[blank line]
                                             
[Story text in English with 2-3 key words in <b> tags]

✍️ <b>واژگان:</b>
💙 <b>word1</b>: معنی
💚 <b>word2</b>: معنی
🧡 <b>word3</b>: معنی

<b>ترجمه داستان:</b>
<blockquote expandable>
[Full Persian translation here]
</blockquote>
  
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return clean_text(completion.choices[0].message.content.strip())
    except Exception as e:
        logger.error(f"Story Error: {e}")
        return None


# ==============================================================================
# 📘 راهنمای تابع: generate_idiom_post
# 🎯 هدف: آموزش یک اصطلاح (Idiom) کاربردی همراه با معنی و مثال
# 📥 ورودی: idiom_item (اختیاری - رشته یا دیکشنری اطلاعات اصطلاح)
# 📤 خروجی: متن آماده ارسال پست اصطلاحات
# 🔗 کاربرد: استفاده در مسیر /idiom
# ==============================================================================
def generate_idiom_post(idiom_item=None) -> str:
    """
    تولید متن پست آموزشی اصطلاح. 
    پشتیبانی از لیست اصطلاحات متنی ساده (String) و دیکشنری (Dict).
    """
    if not idiom_item:
        idiom_item = get_idiom_from_data()

    # تشخیص اینکه آیتم دریافتی متن ساده است یا دیکشنری
    if isinstance(idiom_item, str):
        idiom_str = idiom_item.strip()
    elif isinstance(idiom_item, dict):
        idiom_str = idiom_item.get("idiom") or idiom_item.get("phrase") or idiom_item.get("text") or ""
    else:
        idiom_str = str(idiom_item)

    # اگر به هر دلیلی مقدار خالی بود
    if not idiom_str:
        return None

    prompt = f"""
Teach this idiom for Telegram: {idiom_str}

Format:
📣 <b>اصطلاح روز (Idiom)</b>

🎯 <b>{idiom_str}</b>

🟩 <b>معنی:</b> [Persian meaning]
💬 <b>مثال:</b>
🟦 [English example]
🔷 <b>ترجمه:</b> [Persian translation]
🟧 [English example]
🔶 <b>ترجمه:</b> [Persian translation]

CRITICAL RULES:
1. Use ONLY <b> tags for bold text. Do NOT use asterisks (*).
2. Write English and Persian on separate lines.
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return clean_text(completion.choices[0].message.content.strip())
    except Exception as e:
        logger.error(f"Idiom Error: {e}")
        return None

# ==============================================================================
# 📘 راهنمای تابع: send_telegram_message
# 🎯 هدف: ارسال مستقیم یک متن به کانال/گروه تلگرام از طریق API تلگرام
# 📥 ورودی: text (متن خروجی توابع توليد محتوا)
# 📤 خروجی: True در صورت موفقیت، False در صورت بروز خطا
# ==============================================================================
def send_telegram_message(text: str) -> bool:
    if not text:
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": GROUP_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        return res.status_code == 200
    except Exception as e:
        logger.error(f"Error sending message to Telegram: {e}")
        return False


# ==============================================================================
# 📘 راهنمای تابع: send_telegram_poll
# 🎯 هدف: ارسال نظرسنجی ۴ گزینه‌ای رسمی تلگرام (Quiz Poll)
# 📥 ورودی: quiz_data (دیکشنری شامل question, options, correct_option_index, explanation)
# 📤 خروجی: True در صورت موفقیت، False در صورت بروز خطا
# ==============================================================================
def send_telegram_poll(quiz_data: dict) -> bool:
    if not quiz_data:
        return False
        
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPoll"
    payload = {
        "chat_id": GROUP_CHAT_ID,
        "question": f"🤔 {quiz_data.get('question')}\n({quiz_data.get('level')})",
        "options": json.dumps(quiz_data.get("options", [])),
        "type": "quiz",
        "correct_option_id": quiz_data.get("correct_option_index", 0),
        "explanation": quiz_data.get("explanation", ""),
        "explanation_parse_mode": "HTML",
        "is_anonymous": True
    }
    try:
        res = requests.post(url, data=payload, timeout=10)
        return res.status_code == 200
    except Exception as e:
        logger.error(f"Error sending poll to Telegram: {e}")
        return False


# ==============================================================================
# 🌐 مسیرها و اندپوینتهای Flask (Routes & Cron Jobs)
# ==============================================================================

# ==============================================================================
# 📘 راهنمای مسیر: / (Home)
# 🎯 هدف: تست فعال و زنده بودن سرور
# ==============================================================================
@app.route("/", methods=["GET"])
def home():
    return "English Partner Bot Server is Active!", 200


# ==============================================================================
# 📘 راهنمای مسیر: /send_vocab - post_vocab
# 🎯 هدف: دریافت یک واژه تصادفی از کتاب‌ها و ارسال پست آموزشی آن به تلگرام
# 📥 ورودی: درخواست GET یا POST
# 📤 خروجی: پاسخ JSON شامل وضعیت ارسال پست و نام واژه
# 🔗 کاربرد: زمان‌بندی مستقل برای ارسال پست‌های آموزشی لغت
# ==============================================================================
@app.route("/post_vocab", methods=["GET", "POST"])
def trigger_vocab():
    try:
        # دریافت یک واژه تصادفی از کتاب‌های موجود با تابع get_random_vocab
        vocab_item = get_random_vocab()
        
        # ساخت متن کامل پست آموزشی
        post_text = generate_educational_post_vocab(vocab_item)
        if not post_text:
            return jsonify({"status": "error", "message": "خطا در ساخت پست آموزشی"}), 500

        # ارسال به تلگرام
        msg_sent = send_telegram_message(post_text)

        return jsonify({
            "status": "ok", 
            "sent": msg_sent, 
            "word": vocab_item.get("word")
        }), 200

    except Exception as e:
        logger.error(f"Error in /send_vocab: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ==============================================================================
# 📘 راهنمای مسیر: /quiz_vocab
# 🎯 هدف: دریافت یک واژه تصادفی از کتاب‌ها و ساخت و ارسال آزمون ۴ گزینه‌ای مستقل
# 📥 ورودی: درخواست GET یا POST
# 📤 خروجی: پاسخ JSON شامل وضعیت ارسال نظرسنجی (Poll)
# 🔗 کاربرد: زمان‌بندی مستقل برای ارسال آزمون‌های ۴ گزینه‌ای
# ==============================================================================
@app.route("/quiz_vocab", methods=["GET", "POST"])
def trigger_quiz():
    try:
        # دریافت یک واژه تصادفی کاملاً مستقل از کتاب‌ها
        vocab_item = get_random_vocab()

        # ساخت آزمون ۴ گزینه‌ای بر اساس واژه انتخاب‌شده
        quiz_data = generate_quiz_from_vocab_item(vocab_item)
        if not quiz_data:
            return jsonify({"status": "error", "message": "خطا در ساخت داده‌های آزمون"}), 500

        # ارسال آزمون تلگرامی به گروه/کانال
        poll_sent = send_telegram_poll(quiz_data)

        return jsonify({
            "status": "ok", 
            "sent": poll_sent, 
            "word": vocab_item.get("word")
        }), 200

    except Exception as e:
        logger.error(f"Error in /quiz_vocab: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ==============================================================================
# 📘 راهنمای مسیر: /send_general_post
# 🎯 هدف: ساخت و ارسال یک پست عمومی آموزشی در تلگرام
# ==============================================================================
@app.route("/post", methods=["GET", "POST"])
def trigger_general_post():
    post_text = generate_educational_post()
    sent = send_telegram_message(post_text)
    return jsonify({"status": "ok", "sent": sent}), 200


# ==============================================================================
# 📘 راهنمای مسیر: /quiz
# 🎯 هدف: ساخت و ارسال کوییز عمومی ۴ گزینه‌ای
# ==============================================================================
@app.route("/quiz", methods=["GET", "POST"])
def trigger_ai_quiz():
    quiz_data = generate_quiz_data()
    sent = send_telegram_poll(quiz_data)
    return jsonify({"status": "ok", "sent": sent}), 200


# ==============================================================================
# 📘 راهنمای مسیر: /story
# 🎯 هدف: ساخت و ارسال داستان کوتاه آموزشی
# ==============================================================================
@app.route("/story", methods=["GET", "POST"])
def trigger_story():
    post_text = generate_story_post()
    sent = send_telegram_message(post_text)
    return jsonify({"status": "ok", "sent": sent}), 200


# ==============================================================================
# 📘 راهنمای مسیر: /quote
# 🎯 هدف: ساخت و ارسال نقل‌قول روزانه
# ==============================================================================
@app.route("/quote", methods=["GET", "POST"])
def trigger_quote():
    try:
        post_text = generate_quote_post()
        if not post_text:
            return jsonify({"status": "error", "message": "خطا در ساخت پست نقل‌قول"}), 500

        msg_sent = send_telegram_message(post_text)

        return jsonify({
            "status": "ok", 
            "sent": msg_sent
        }), 200

    except Exception as e:
        logger.error(f"Error in /send_quote: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ==============================================================================
# 📘 راهنمای مسیر: /news
# 🎯 هدف: ساخت و ارسال خبر روز انگلیسی همراه با ترجمه مخفی
# ==============================================================================
@app.route("/news", methods=["GET", "POST"])
def trigger_news():
    try:
        text = generate_news_post()
        if text and send_telegram_message(text):
            return "News sent!", 200
        return "Failed to send news", 500
    except Exception as e:
        logger.error(f"Route /news Error: {e}")
        return f"Error: {e}", 500


# ==============================================================================
# 📘 راهنمای مسیر: /grammar_data
# 🎯 هدف: ساخت و ارسال پست گرامر بر اساس موضوعات داخل JSON
# ==============================================================================
@app.route("/grammar_data", methods=["GET", "POST"])
def trigger_grammar_vocab():
    try:
        grammar_item = get_grammar_from_data()
        if not grammar_item:
            return "No JSON grammar data found", 404
            
        text = generate_grammar_post_vocab(grammar_item)
        if text and send_telegram_message(text):
            return "Grammar Vocab sent!", 200
        return "Failed to send grammar post", 500
    except Exception as e:
        logger.error(f"Route /grammar_data Error: {e}")
        return f"Error: {e}", 500


# ==============================================================================
# 📘 راهنمای مسیر: /idiom
# 🎯 هدف: ساخت و ارسال پست آموزش اصطلاحات انگلیسی
# ==============================================================================
@app.route("/idiom", methods=["GET", "POST"])
def trigger_idiom():
    try:
        idiom_item = get_idiom_from_data()
        if not idiom_item:
            return "No JSON idiom data found", 404
            
        text = generate_idiom_post(idiom_item)
        if text and send_telegram_message(text):
            return "Idiom post sent!", 200
        return "Failed to send idiom post", 500
    except Exception as e:
        logger.error(f"Route /idiom Error: {e}")
        return f"Error: {e}", 500


import os
import re
import json
from flask import request, send_file

# مطمئن شوید متغیر BASE_DIR در بالای فایل bot.py تعریف شده باشد:
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ==============================================================================
# 📘 راهنمای مسیر: /build_book
# 🎯 هدف: ساخت خودکار فایل‌های JSON لغات کتاب (Paul Nation) توسط هوش مصنوعی
# 📥 پارامترها (Query String): book (۱ تا ۶), start_unit (۱ تا ۳۰)
# ==============================================================================
@app.route("/build_book", methods=["GET"])
def build_book_route():
    book_num = request.args.get("book", default=3, type=int)
    start_unit = request.args.get("start_unit", default=1, type=int)

    if book_num < 1 or book_num > 6:
        return "شماره کتاب باید بین ۱ تا ۶ باشد.", 400

    data_dir = os.path.join(BASE_DIR, "data")
    os.makedirs(data_dir, exist_ok=True)
    file_path = os.path.join(data_dir, f"book_{book_num}.json")

    existing_words = []
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                existing_words = json.load(f)
        except Exception:
            existing_words = []

    prompt = f"""
You are an expert lexical database creator for Paul Nation's "4000 Essential English Words" (Latest Edition).
Generate all target words for Book {book_num}, Unit {start_unit}.

Return ONLY a valid JSON array of objects with this EXACT structure (no markdown fences, no extra text):
[
  {{
    "word": "target word",
    "phonetic": "/IPA pronunciation/",
    "translation_fa": "ترجمه دقیق فارسی",
    "definition_en": "Short clear English definition from the book",
    "book": {book_num},
    "unit": {start_unit}
  }}
]
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=4000
        )
        raw_res = completion.choices[0].message.content.strip()

        # استخراج هوشمند و مقاوم آرایه JSON حتی در صورت وجود متن اضافه
        match = re.search(r'\[.*\]', raw_res, re.DOTALL)
        if match:
            cleaned_res = match.group(0)
        else:
            cleaned_res = raw_res.replace("```json", "").replace("```", "").strip()

        new_words = json.loads(cleaned_res, strict=False)

        if isinstance(new_words, list):
            # حذف لغات قبلی همین درس برای جلوگیری از تکرار و بروزرسانی داده‌ها
            existing_words = [w for w in existing_words if not (isinstance(w, dict) and w.get("unit") == start_unit)]
            existing_words.extend(new_words)

            # ذخیره فوری و آنی فایل روی دیسک
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(existing_words, f, ensure_ascii=False, indent=2)

            next_unit = start_unit + 1
            download_url = f"/download_book?book={book_num}"

            msg = f"<h3>✅ درس {start_unit} از کتاب {book_num} با موفقیت ساخته و ذخیره شد.</h3>"
            msg += f"<p>تعداد کل واژگان ذخیره‌شده تا اکنون: <b>{len(existing_words)}</b></p>"
            msg += f"<p>📥 <a href='{download_url}' target='_blank'><b>[برای دانلود مستقیم فایل JSON تا این لحظه اینجا کلیک کنید]</b></a></p>"
            msg += "<hr>"

            if start_unit < 30:
                next_url = f"/build_book?book={book_num}&start_unit={next_unit}"
                msg += f"<p>👉 <a href='{next_url}'><b>برای ساخت درس بعدی (درس {next_unit}) اینجا کلیک کنید</b></a></p>"
            else:
                msg += f"<h2>🎉 ساخت کتاب {book_num} کامل شد!</h2>"
                msg += f"<p>📥 <a href='{download_url}'><b>برای دانلود فایل JSON نهایی و کامل کتاب {book_num} اینجا کلیک کنید</b></a></p>"

            return msg, 200

    except Exception as e:
        logger.error(f"Error generating unit {start_unit}: {e}")
        return f"خطا در ساخت درس {start_unit}: {e}", 500

    return "خطای نامشخص", 500


# ==============================================================================
# 📘 راهنمای مسیر: /download_book
# 🎯 هدف: لینک دانلود مستقیم فایل JSON ساخته‌شده در هر مرحله
# ==============================================================================
@app.route("/download_book", methods=["GET"])
def download_book_route():
    book_num = request.args.get("book", default=3, type=int)
    file_path = os.path.join(BASE_DIR, "data", f"book_{book_num}.json")
    
    if os.path.exists(file_path):
        return send_file(
            file_path,
            mimetype="application/json",
            as_attachment=True,
            download_name=f"book_{book_num}.json"
        )
    return f"فایل book_{book_num}.json هنوز وجود ندارد یا پیدا نشد.", 404
    
# ==============================================================================
# 📘 راهنمای مسیر: /<BOT_TOKEN>
# 🎯 هدف: اندپوینت دریافت رویدادها و وب‌هوک تلگرام
# ==============================================================================
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        update_dict = request.get_json(force=True)
        asyncio.run(process_telegram_update(update_dict))
        return "ok", 200
    except Exception as e:
        logger.error(f"Webhook Error: {e}")
        return "error", 200


# ==============================================================================
# 🚀 اجرای برنامه اصلی
# ==============================================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
