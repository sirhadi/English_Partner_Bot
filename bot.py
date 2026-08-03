import os
import random
import logging
import asyncio
import json
import urllib.request
import urllib.error
from flask import Flask, request
from telegram import Update, Bot
from groq import Groq
import re
from datetime import datetime, timezone, timedelta
import xml.etree.ElementTree as ET
from content_manager import (
    get_vocab_for_post,
    get_quote_from_data,
    get_grammar_from_data,
    get_idiom_from_data
)

# ================== Settings ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID", "0")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

client = Groq(api_key=GROQ_API_KEY, timeout=20.0)
MODEL_NAME = "llama-3.3-70b-versatile"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

#=========== حذف حروف غیرمجاز =========
def clean_text(text: str) -> str:
    if not text:
        return text
    bad_chars_pattern = r'[\u0400-\u04FF\u4E00-\u9FFF\u3400-\u4DBF\u3000-\u303F]'
    return re.sub(bad_chars_pattern, '', text)

#=========== تابع زمان به وقت تهران ==========
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

TOPICS = [
    "یک کلمه یا اصطلاح انگلیسی روزمره با معنی فارسی، مثال و تلفظ فونتیک آن",
    "یک نکته گرامری کوتاه و کاربردی انگلیسی با فرمول ",
    "یک دیالوگ انگلیسی کوتاه دو نفره مناسب تمرین مکالمه و پارتنریابی",
    "یک اصطلاح idiom انگلیسی با معنی و مثال",
    "یک سوال جالب انگلیسی برای شروع مکالمه بین پارتنرهای زبانی به همراه مثال و ترجمه فارسی",
    "یک جوک یا عبارت طنز انگلیسی",
    "یک اصطلاح مبتدی، متوسط یا پیشرفته Idiom یا Phrasal Verb با معنی دقیق، مثال و مترادف",
    "یک ساختار گرامری سطح متوسط، متوسط به بالا و بالا تا C1 با فرمول ساخت اون ساختار گرامری و مثال کاربردی",
    "یک عبارت کاربردی برای بحث های آکادمیک و بیزینس Professional English",
    "یک اشتباه رایج زبان آموزان ایرانی در انگلیسی و شکل درست آن"
]

# ================== AI Functions ==================
def generate_educational_post() -> str:
    chosen_topic = random.choice(TOPICS)
    time_context = get_time_context()
    random_seed = random.randint(1000, 9999)
    
    prompt = f"""
You are a warm and expert English teacher creating a useful and beautifully formatted Telegram post for an Iranian Telegram group. The level is intermediate to advanced (B2-C1). Current time context: {time_context}.
Unique Request ID: {random_seed}

Topic: {chosen_topic}

Generate a complete educational post following this EXACT layout and emoji style:

<b>🟢 Level: B2-C1</b>

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

##============== تابع آموزشی =========================
def generate_educational_post_vocab(vocab_item) -> str:
    if not vocab_item:
        logger.error("vocab_item is empty!")
        return None

    word = ""
    phonetic = ""
    translation = ""
    definition = ""
    book = 1
    unit = 1

    # پشتیبانی همزمان از String و Dict
    if isinstance(vocab_item, str):
        word = vocab_item.strip()
    elif isinstance(vocab_item, dict):
        word = vocab_item.get("word") or vocab_item.get("vocab") or vocab_item.get("text") or vocab_item.get("phrase") or ""
        phonetic = vocab_item.get("phonetic") or vocab_item.get("pronunciation") or ""
        translation = vocab_item.get("translation_fa") or vocab_item.get("meaning") or vocab_item.get("translation") or ""
        definition = vocab_item.get("definition_en") or vocab_item.get("definition") or ""
        book = vocab_item.get("book", 1)
        unit = vocab_item.get("unit", 1)
    else:
        logger.error(f"Unexpected vocab_item structure: {type(vocab_item)}")
        return None

    if not word:
        logger.error("Extracted word is empty!")
        return None

    time_context = get_time_context()
    
    prompt = f"""
You are an expert English teacher creating a Telegram post to teach a specific word or phrase for Book {book}, Unit {unit}.

Target Word/Phrase: {word}
Phonetic: {phonetic if phonetic else "Provide accurate IPA phonetic pronunciation in brackets"}
Persian Meaning: {translation if translation else "Provide accurate fluent Persian translation"}
English Definition: {definition if definition else "Provide a short clear English definition"}

Format the post EXACTLY using HTML tags (NO asterisks *):

<b>🟢 Book {book} - Unit {unit}</b>

😍 <b>[Greeting in Persian matching {time_context}]</b>
📌 <b>واژه / اصطلاح روز: {word}</b>

🔴 <b>{word}</b> {phonetic if phonetic else ""}
🔹 <b>معنی:</b> {translation if translation else "[Persian translation]"}
📖 <b>تعریف انگلیسی:</b> {definition if definition else "[English definition]"}

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


#============ تابع کوئیز =================
def generate_quiz_from_vocab_item(vocab_item) -> dict:
    if not vocab_item:
        return None

    word = ""
    translation = ""
    book = 1
    unit = 1

    if isinstance(vocab_item, str):
        word = vocab_item.strip()
    elif isinstance(vocab_item, dict):
        word = vocab_item.get("word") or vocab_item.get("vocab") or vocab_item.get("text") or ""
        translation = vocab_item.get("translation_fa") or vocab_item.get("meaning") or ""
        book = vocab_item.get("book", 1)
        unit = vocab_item.get("unit", 1)
    else:
        return None

    if not word:
        return None

    prompt = f"""
Create a Telegram multiple-choice quiz question to test this word/phrase:
Word/Phrase: {word}
Persian Meaning: {translation if translation else "Auto-generate accurate Persian meaning"}

Return ONLY a raw JSON object with this EXACT structure (no markdown, no code blocks):
{{
  "level": "کتاب {book} - درس {unit}",
  "question": "A fill-in-the-blank English sentence where '{word}' fits correctly.",
  "options": ["{word}", "WrongOption1", "WrongOption2", "WrongOption3"],
  "correct_option_index": 0,
  "explanation": "توضیح پاسخ و معنی اصطلاح/واژه {word} به فارسی"
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
        logger.error(f"Quiz Generation Error: {e}")
        return None


#============ تابع نقل قول ==========================
def generate_quote_post_vocab(quote_item) -> str:
    if not quote_item:
        logger.error("Quote item is empty!")
        return None

    if isinstance(quote_item, str):
        quote_text = quote_item
        author = "Unknown"
        category = "Wisdom"
    elif isinstance(quote_item, dict):
        quote_text = quote_item.get("text") or quote_item.get("quote") or quote_item.get("content") or ""
        author = quote_item.get("author") or quote_item.get("by") or "Unknown"
        category = quote_item.get("category") or "Wisdom"
    else:
        logger.error(f"Unexpected quote_item structure: {type(quote_item)}")
        return None

    if not quote_text.strip():
        logger.error("Extracted quote_text is empty!")
        return None
    
    prompt = f"""
You are an inspiring English teacher creating a Telegram post featuring a quote.

Use this EXACT English quote:
Quote: "{quote_text}"
Author: {author}
Category: {category}

Generate the post following this EXACT layout using standard HTML tags:

🐣 <b>Quote of the Day</b>

<blockquote><b>"{quote_text}"</b>
— <i>{author}</i></blockquote>

🇮🇷 <b>ترجمه:</b>
<blockquote>[Fluent Persian translation of the quote]</blockquote>

✍️ <b>نکته زبانی:</b>
🔹 Explain 1-2 interesting vocabulary words, idioms, or grammar structures used in this quote in Persian.

🤔 <b>What do you think?</b>
[An open-ended question in English about the quote's theme]
🟣 [ترجمه فارسی سوال]

CRITICAL RULES:
1. Use <b> for bold, <i> for italics, and <blockquote> and </blockquote> for quote blocks. DO NOT use asterisks (*).
2. Separate English and Persian text onto distinct lines.
Output ONLY the final Telegram post text.
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a professional English-Persian translator."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        )
        return clean_text(completion.choices[0].message.content.strip())
    except Exception as e:
        logger.error(f"Quote Vocab Error: {e}")
        return None

def generate_quiz_data() -> dict:
    topics = [
        "Phrasal Verbs", "Conditionals (1st, 2nd, 3rd, or Mixed)", "Advanced Prepositions", 
        "Synonyms and Antonyms", "Inversion in English", "Idioms & Expressions", 
        "Passive Voice", "Relative Clauses", "Past Modal Verbs (must have, should have)", 
        "Collocations", "Reported Speech", "Subject-Verb Agreement", "Vocabulary"
    ]
    contexts = [
        "Business & Job Interview", "Travel & Airport", "Daily Casual Conversation", 
        "University & Academic", "Technology & AI", "Sports & Fitness", "Movies & Entertainment"
    ]
    
    chosen_topic = random.choice(topics)
    chosen_context = random.choice(contexts)
    time_seed = datetime.now().strftime("%Y%m%d%H%M%S%f")

    prompt = f"""
Generate a completely original, unique multiple-choice English grammar or vocabulary quiz question.
- Grammar/Vocabulary Focus: {chosen_topic}
- Sentence Context/Theme: {chosen_context}
- Unique Request Hash: {time_seed}

Return a valid JSON object ONLY (no extra text, no markdown code blocks). Exact structure:
{{
  "level": "سطح زبانی به فارسی همراه با سطح CEFR",
  "question": "متن سوال چهارگزینه ای به انگلیسی همراه با جای خالی '___'",
  "options": ["گزینه اول", "گزینه دوم", "گزینه سوم", "گزینه چهارم"],
  "correct_option_index": 0,
  "explanation": "توضیح پاسخ صحیح به فارسی"
}}
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        text = completion.choices[0].message.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text(text))
    except Exception as e:
        logger.error(f"Quiz Error: {e}")
        return None

#=================== تابع کوئیز ====================
def generate_quiz_from_vocab_item(vocab_item: dict) -> dict:
    if not vocab_item or not isinstance(vocab_item, dict):
        return None

    word = vocab_item.get("word") or vocab_item.get("vocab") or ""
    translation = vocab_item.get("translation_fa") or vocab_item.get("meaning") or ""
    definition = vocab_item.get("definition_en") or vocab_item.get("definition") or ""
    book = vocab_item.get("book", 1)
    unit = vocab_item.get("unit", 1)

    prompt = f"""
Create a Telegram multiple-choice quiz question to test this word:
Word: {word}
Persian Meaning: {translation}
Definition: {definition}

Return ONLY a raw JSON object with this EXACT structure (no markdown, no code blocks):
{{
  "level": "کتاب {book} - درس {unit}",
  "question": "A fill-in-the-blank English sentence where '{word}' fits correctly.",
  "options": ["{word}", "WrongOption1", "WrongOption2", "WrongOption3"],
  "correct_option_index": 0,
  "explanation": "توضیح پاسخ و معنی کلمه {word} به فارسی"
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
        logger.error(f"Quiz Generation Error: {e}")
        return None

#====================== تابع داستان ===================
def generate_story_post() -> str:
    levels = ["A2 (Elementary)", "B1 (Intermediate)", "B2 (Upper-Intermediate)", "C1 (Advanced)"]
    chosen_level = random.choice(levels)
    time_seed = datetime.now().strftime("%Y%m%d%H%M%S%f")

    prompt = f"""
Write an original, short, engaging English story for language learners.
- Level: {chosen_level}
- Length: 6 to 8 sentences.
- Seed: {time_seed}

Format the post EXACTLY using HTML tags (NO asterisks *):

📖 <b>Short Story ({chosen_level})</b>

[Write the English story here. Wrap 3-4 key/advanced vocabulary words in <b> tags]

✍️ <b>واژگان کلیدی:</b>
🔹 <b>word1</b>: معنی فارسی
🔹 <b>word2</b>: معنی فارسی
🔹 <b>word3</b>: معنی فارسی

🇮🇷 <b>ترجمه داستان (برای خواندن لمس کنید):</b>
<blockquote expandable>
[Full fluent Persian translation of the story here]
</blockquote>

CRITICAL RULES:
1. Wrap the Persian translation strictly inside <blockquote expandable> and </blockquote>.
2. Output ONLY the final Telegram post text.
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
        
#==================== تابع اخبار ===============================
def fetch_latest_world_news_rss() -> list:
    rss_url = "http://feeds.bbci.co.uk/news/world/rss.xml"
    news_items = []
    try:
        req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            
            for item in root.findall('./channel/item')[:3]:
                title = item.find('title').text if item.find('title') is not None else ""
                desc = item.find('description').text if item.find('description') is not None else ""
                news_items.append({"title": title, "summary": desc})
    except Exception as e:
        logger.error(f"RSS Fetch Error: {e}")
    return news_items

def generate_news_post() -> str:
    news_list = fetch_latest_world_news_rss()
    if not news_list:
        return None

    raw_news_text = "\n\n".join([f"News {i+1}:\nTitle: {n['title']}\nSummary: {n['summary']}" for i, n in enumerate(news_list)])

    prompt = f"""
You are an English news reporter and teacher. Turn these 3 recent world news items into an educational Telegram post:

{raw_news_text}

Format the post EXACTLY using standard HTML tags:

🌍 <b>World News Brief / اخبار مهم جهان</b>

1️⃣ <b>[Headline 1 in English]</b>
[Short 1-2 sentence simplified English summary]
<blockquote expandable>
🇮🇷 <b>ترجمه:</b> [Persian translation of news 1]
</blockquote>

2️⃣ <b>[Headline 2 in English]</b>
[Short 1-2 sentence simplified English summary]
<blockquote expandable>
🇮🇷 <b>ترجمه:</b> [Persian translation of news 2]
</blockquote>

3️⃣ <b>[Headline 3 in English]</b>
[Short 1-2 sentence simplified English summary]
<blockquote expandable>
🇮🇷 <b>ترجمه:</b> [Persian translation of news 3]
</blockquote>

🔑 <b>Key News Vocabulary / کلمات کلیدی خبری:</b>
🔹 <b>word1</b>: معنی فارسی
🔹 <b>word2</b>: معنی فارسی

CRITICAL RULES:
1. Always put Persian translations inside <blockquote expandable>...</blockquote> tags.
2. DO NOT use asterisks (*). Use ONLY <b> tags for bold text.
Output ONLY final Telegram post text.
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        return clean_text(completion.choices[0].message.content.strip())
    except Exception as e:
        logger.error(f"News Generation Error: {e}")
        return None

#================= تابع گرامر ======================
def generate_grammar_post_vocab(grammar_item: dict) -> str:
    if not grammar_item or not isinstance(grammar_item, dict):
        return None

    level = grammar_item.get("level", "A1-A2")
    topic = grammar_item.get("topic") or grammar_item.get("title") or ""
    
    prompt = f"""
You are an expert English teacher creating an engaging Telegram lesson.

Target Grammar Topic: {topic}
Target Level: {level}

Format the post EXACTLY using standard HTML tags (NO asterisks *):

📘 <b>Grammar Lesson ({level})</b>
📌 <b>موضوع: {topic}</b>

🔹 <b>ساختار / فرمول:</b>
<code>[Write the main formula/structure here]</code>

💡 <b>توضیح به زبان ساده (فارسی):</b>
[Explain when and how to use this grammar structure clearly in Persian]

🟢 <b>مثال‌های کاربردی:</b>
• [Example sentence 1 with target grammar wrapped in <b> tags]
🔹 <b>ترجمه:</b> [Persian translation]
• [Example sentence 2 with target grammar wrapped in <b> tags]
🔹 <b>ترجمه:</b> [Persian translation]

✍️ <b>تمرین کوتاه:</b>
[Write 1 short completion sentence with a blank for members]
🟣 [ترجمه سوال به فارسی]

CRITICAL RULES:
1. ALL bold tags must be <b> and </b>. Use <code> for formulas.
2. Separate English and Persian text clearly onto new lines.
3. Output ONLY final Telegram post text.
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

#=========== تابع اصطلاحات ======================
def generate_idiom_post(idiom_item) -> str:
    if not idiom_item:
        logger.error("idiom_item is empty!")
        return None

    idiom_text = ""
    if isinstance(idiom_item, str):
        idiom_text = idiom_item.strip()
    elif isinstance(idiom_item, dict):
        idiom_text = idiom_item.get("idiom") or idiom_item.get("phrase") or idiom_item.get("text") or ""
    
    if not idiom_text:
        logger.error("Extracted idiom_text is empty!")
        return None

    time_context = get_time_context()

    prompt = f"""
You are an expert, encouraging English teacher creating a high-quality Telegram post to teach a popular English idiom.

Target Idiom: "{idiom_text}"

Generate the post following this EXACT layout using standard HTML tags (NO asterisks *):

🎭 <b>اصطلاح روز (Idiom of the Day)</b>

😍 <b>[Greeting in Persian matching {time_context}]</b>
📌 <b>اصطلاح: {idiom_text}</b>

🔴 <b>"{idiom_text}"</b>
🔹 <b>معنی و مفهوم:</b> [Clear Persian explanation and equivalent Persian idiom if applicable]

🟢 <b>مثال اول:</b>
📣 [Natural English sentence using <b>{idiom_text}</b>]
🔹 <b>ترجمه:</b> [Persian translation]

🟡 <b>مثال دوم:</b>
🔔 [Another English sentence using <b>{idiom_text}</b>]
🔸 <b>ترجمه:</b> [Persian translation]

💡 <b>نکته کاربردی:</b>
[A brief tip in Persian on when or how to use this idiom natively]

👩‍🏫 <b>حالا تو بگو:</b>
[An engaging question in English asking members to write a sentence with <b>{idiom_text}</b>]
🟣 [ترجمه سوال به فارسی]

CRITICAL RULES:
1. Use ONLY <b> tags for bold text. DO NOT use asterisks (*).
2. Write English and Persian on separate lines.
3. Output ONLY the final Telegram post text.
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
        
# ================== Telegram Processing ==================
async def process_telegram_update(update_dict: dict):
    bot = Bot(token=BOT_TOKEN)
    update = Update.de_json(update_dict, bot)

    if not update.message:
        return

    chat_id = update.message.chat.id
    msg_text = update.message.text or ""

    if msg_text.startswith("/start"):
        await bot.send_message(
            chat_id=chat_id,
            text="سلام! من ربات گروه پارتنریابی و یادگیری زبان انگلیسی هستم 🌟"
        )
        return

    is_private = update.message.chat.type == "private"
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    is_mentioned = bot_username and f"@{bot_username}" in msg_text

    if is_private or is_mentioned:
        user_clean_text = msg_text.replace(f"@{bot_username}", "").strip() if bot_username else msg_text.strip()
        if not user_clean_text:
            return
        
        try:
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": f"به عنوان دستیار آموزش زبان به این پیام کوتاه جواب بده: {user_clean_text}"}],
                temperature=0.7,
            )
            answer = completion.choices[0].message.content.strip()
            await bot.send_message(
                chat_id=chat_id,
                text=answer,
                reply_to_message_id=update.message.message_id
            )
        except Exception as e:
            logger.error(f"Reply Error: {e}")

# ================== Helper Telegram Sender ==================
def send_telegram_message(text: str) -> bool:
    """ارسال امن پیام به تلگرام با قابلیت Fallback در صورت اشکال تگ‌های HTML"""
    if not text or not text.strip():
        logger.error("send_telegram_message was called with empty text.")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": GROUP_CHAT_ID, "text": text, "parse_mode": "HTML"}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req, timeout=15):
            return True
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        logger.error(f"Telegram HTML Send Error (HTTP {e.code}): {error_body}")
        
        # اگر تلگرام به تگ HTML ایراد گرفت، تلاش مجدد بدون HTML انجام می‌شود
        try:
            payload_plain = json.dumps({"chat_id": GROUP_CHAT_ID, "text": text}).encode('utf-8')
            req_plain = urllib.request.Request(url, data=payload_plain, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req_plain, timeout=15):
                return True
        except Exception as e2:
            logger.error(f"Telegram Fallback Plain Text Error: {e2}")
            return False
    except Exception as e:
        logger.error(f"Telegram Network Error: {e}")
        return False

# ================== Web Routes ==================
@app.route("/", methods=["GET"])
def health():
    return "Bot is alive!", 200

@app.route("/post", methods=["GET", "POST"])
def trigger_post():
    try:
        text = generate_educational_post()
        if text and send_telegram_message(text):
            return "Post sent!", 200
        return "Failed to generate or send post", 500
    except Exception as e:
        logger.error(f"Route /post Error: {e}")
        return f"Error: {e}", 500

@app.route("/post_vocab", methods=["GET", "POST"])
def trigger_post_vocab():
    try:
        vocab_item = get_vocab_for_post()
        if not vocab_item:
            return "No JSON data found in content_manager", 404
        
        text = generate_educational_post_vocab(vocab_item)
        if text and send_telegram_message(text):
            return "Post Vocab sent!", 200
        return "Failed to send Vocab post", 500
    except Exception as e:
        logger.error(f"Route /post_vocab Error: {e}")
        return f"Error: {e}", 500

@app.route("/quote", methods=["GET", "POST"])
def trigger_quote_vocab():
    try:
        quote_item = get_quote_from_data()
        if not quote_item:
            return "No JSON quote data found", 404
            
        text = generate_quote_post_vocab(quote_item)
        if text and send_telegram_message(text):
            return "Quote sent!", 200
        return "Failed to send quote post", 500
    except Exception as e:
        logger.error(f"Route /quote Error: {e}")
        return f"Error: {e}", 500

@app.route("/quiz", methods=["GET", "POST"])
def trigger_quiz():
    try:
        quiz_data = generate_quiz_data()
        if not quiz_data:
            return "Failed to generate quiz data", 500
        
        quiz_level = quiz_data.get("level", "متوسط / پیشرفته")
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPoll"
        payload = json.dumps({
            "chat_id": GROUP_CHAT_ID,
            "question": f"🎯 کوئیز ({quiz_level}):\n{quiz_data['question']}",
            "options": quiz_data['options'],
            "type": "quiz",
            "correct_option_id": quiz_data['correct_option_index'],
            "explanation": quiz_data['explanation']
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=15):
            return "Quiz sent!", 200
    except Exception as e:
        logger.error(f"Route /quiz Error: {e}")
        return f"Error: {e}", 500

@app.route("/quiz_vocab", methods=["GET", "POST"])
def trigger_quiz_vocab():
    try:
        vocab_item = get_vocab_for_post()
        if not vocab_item:
            return "No JSON vocab data found", 404
            
        quiz_data = generate_quiz_from_vocab_item(vocab_item)
        if not quiz_data:
            return "Failed to generate quiz from vocab", 500
            
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPoll"
        payload = json.dumps({
            "chat_id": GROUP_CHAT_ID,
            "question": f"🎯 کوئیز واژگان ({quiz_data.get('level')}):\n{quiz_data['question']}",
            "options": quiz_data['options'],
            "type": "quiz",
            "correct_option_id": quiz_data['correct_option_index'],
            "explanation": quiz_data['explanation']
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=15):
            return "Quiz Vocab sent!", 200
    except Exception as e:
        logger.error(f"Route /quiz_vocab Error: {e}")
        return f"Error: {e}", 500

@app.route("/story", methods=["GET", "POST"])
def trigger_story():
    try:
        text = generate_story_post()
        if text and send_telegram_message(text):
            return "Story sent!", 200
        return "Failed to send story", 500
    except Exception as e:
        logger.error(f"Route /story Error: {e}")
        return f"Error: {e}", 500

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

#================== تلگرام روتز ==================

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        update_dict = request.get_json(force=True)
        asyncio.run(process_telegram_update(update_dict))
        return "ok", 200
    except Exception as e:
        logger.error(f"Webhook Error: {e}")
        return "error", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
