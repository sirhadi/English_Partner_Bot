import os
import random
import logging
import asyncio
import json
import urllib.request
from flask import Flask, request
from telegram import Update, Bot
from groq import Groq
import re
from datetime import datetime, timezone, timedelta
import xml.etree.ElementTree as ET
from content_manager import (
    get_quiz_from_data,
    get_vocab_for_post,
    get_quote_from_data,
    get_grammar_from_data
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

#=========== حذف حروف عجیب و غریب =========
def clean_text(text: str) -> str:
    if not text:
        return text
    # الگوی منظم برای شناسایی حروف سیریلیک (روسی) و حروف چینی/ژاپنی/کره‌ای
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
# 1. پست آموزشی عمومی با هوش مصنوعی

def generate_educational_post() -> str:
    chosen_topic = random.choice(TOPICS)
    time_context = get_time_context()
    random_seed = random.randint(1000, 9999) # برای شکستن حافظه پنهان و جلوگیری از تکرار
    
    prompt = f"""
# You are a warm, friendly, and expert English teacher creating a beautifully formatted Telegram post for an upper-intermediate/advanced (B2-C1) Iranian group.
You are a warm and expert English teacher creating a usefull and beautifully formatted Telegram post for an Iranian Telegran group. the level of this group is from intermediate to advance (B2-C1). Current time of day context: {time_context}.
Unique Request ID: {random_seed} (Generate completely original content).

Topic: {chosen_topic}


Generate a Telegram post with this structure:
# Generate a complete educational post following this EXACT layout and emoji style:

-add the level with an emoji in the first line in <b> and </b> html tag (for example: <b>🟢level: A2</b>)
-add a blank line for clear view.

😍 <b>[Use a highly creative, unique, and dynamic native English greeting (e.g., "Mornings!", "Howdy folks!", "What's cracking, team?", "Hope you're having a blast!", "Hey language enthusiasts!", "How's it going?") loosely matching {time_context} + natural Persian translation]</b>
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
1. Formatting: ALL bold texts MUST be wrapped in <b> and </b> HTML tags. DO NOT use asterisks (*).
2. Content: Give actual, practical, bite-sized teaching content with clear Persian translations.
3. Keep it visually engaging, friendly, and well-spaced.
4. Level: Intermediate to Upper-Intermediate to Advanced (A1-C1).
5. other ruls:
    - do not mix persian and english text together. write them in seprate lines for being readable.
   - write the translation
   - after each section let a blank line (to be clearly redable).
   - use other colorful icons for their translation
   - never use other alphabet letters except Persian and English letters.
Output ONLY the final post text.
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

#تابع آموزشی به کمک واژگان فایل وکب. این کد رو میشه داخل همین تابع آموزشی بالا نوشت و بقیه قوانینش یکسانه. ولی واسه راحتی من جداگانه مینویسم

# 2. پست آموزشی بر اساس کلمه مشخص JSON
def generate_educational_post_vocab(vocab_item: dict) -> str:
    time_context = get_time_context()
    word = vocab_item.get("word")
    phonetic = vocab_item.get("phonetic", "")
    translation = vocab_item.get("translation_fa", "")
    definition = vocab_item.get("definition_en", "")
    book = vocab_item.get("book", 3)
    unit = vocab_item.get("unit", 1)
    
    prompt = f"""
You are an expert English teacher creating a Telegram post to teach a specific word from Book {book}, Unit {unit}:

Target Word: {word}
Phonetic: {phonetic}
Persian Meaning: {translation}
English Definition: {definition}

Format the post EXACTLY using HTML tags (NO asterisks *):

<b>🟢 Book {book} - Unit {unit}</b>

😍 <b>[Greeting in Persian matching {time_context}]</b>
📌 <b>واژه روز: {word}</b>

🔴 <b>{word}</b> {phonetic}
🔹 <b>معنی:</b> {translation}
📖 <b>تعریف انگلیسی:</b> {definition}

🟢 <b>مثال اول:</b>
📣 [English sentence with <b>{word}</b>]
🔹 <b>ترجمه:</b> [Persian translation]

🟡 <b>مثال دوم:</b>
🔔 [Another English sentence with <b>{word}</b>]
🔸 <b>ترجمه:</b> [Persian translation]

👩‍🏫 <b>حالا تو بگو:</b>
[An interactive question asking members to use <b>{word}</b> in a sentence]
🟣 [ترجمه سوال به فارسی]
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


#======== تایع نقل قول ============
# ۱. نقل‌قول بر اساس دیتای JSON + قالب‌بندی با هوش مصنوعی
def generate_quote_post_vocab(quote_item: dict) -> str:
    time_context = get_time_context()
    quote_text = quote_item.get("text")
    author = quote_item.get("author", "Unknown")
    category = quote_item.get("category", "Wisdom")
    
    prompt = f"""
You are an inspiring English teacher creating a Telegram post featuring a quote.

Use this EXACT English quote from our database:
Quote: "{quote_text}"
Author: {author}
Category: {category}

Generate the post following this EXACT layout using standard HTML tags:

🐣 <b>Quote of the Day</b>

<blockquote><b>"{quote_text}"</b>
— <i>{author}</i></blockquote>

<b>ترجمه</b>🇮🇷 
<blockquote>[Fluent Persian translation of the quote]</blockquote>

✍️ <b>نکته زبانی:</b>
🔹 Explain 1-2 interesting vocabulary words, idioms, or grammar structures used in this quote (in Persian).

🤔 <b>What do you think?</b>
[An open-ended question in English about the quote's theme]
🟣 [ترجمه فارسی سوال]

CRITICAL RULES:
1. Use <b> for bold, <i> for italics, and <blockquote> and </blockquote> for Telegram quote blocks. DO NOT use asterisks (*).
2. Write English and Persian on separate lines for readability.
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
        
#============= تابع کوئیز ===============
def generate_quiz_data() -> dict:
    # انتخاب یک موضوع گرامری یا لغوی تصادفی برای جلوگیری از سوال تکراری
    topics = [
        "Phrasal Verbs", "Conditionals (1st, 2nd, 3rd, or Mixed)", "Advanced Prepositions", 
        "Synonyms and Antonyms", "Inversion in English", "Idioms & Expressions", 
        "Passive Voice", "Relative Clauses", "Past Modal Verbs (must have, should have)", 
        "Collocations", "Reported Speech", "Subject-Verb Agreement", "Vocabulary from 4000 Words or 1100 words"
    ]
    # افزودن زمینه داستانی تصادفی برای تنوع ۱۰۰٪ جملات
    contexts = [
        "Business & Job Interview", "Travel & Airport", "Daily Casual Conversation", 
        "University & Academic", "Technology & AI", "Sports & Fitness", "Movies & Entertainment"
    ]
    
    chosen_topic = random.choice(topics)
    chosen_context = random.choice(contexts)
    # استفاده از دقیق‌ترین زمان ممکن (حتی میلی‌ثانیه) به عنوان کد یکتا
    time_seed = datetime.now().strftime("%Y%m%d%H%M%S%f")

    prompt = f"""
Generate a completely original, unique multiple-choice English grammar quiz or vocabulary quiz question.
- be careful to let a blank (or ....... or ----- or ther things) in your qustion for answer.
- Grammar/Vocabulary Focus: {chosen_topic}
- Sentence Context/Theme: {chosen_context}
- Unique Request Hash: {time_seed}

Return a valid JSON object ONLY (no extra text, no markdown code blocks). Exact structure:
{{
  "level": "سطح زبانی به فارسی همراه با سطح CEFR (مثلاً: سطح متوسط B1 یا سطح پیشرفته C1)",
  "question": "متن سوال چهارگزینه ای به انگلیسی (حتما یک جمله داستانی مرتبط با {chosen_context} باشد و از جملات تکراری کتابی استفاده نکن)",
  "options": ["گزینه اول", "گزینه دوم", "گزینه سوم", "گزینه چهارم"],
  "correct_option_index": 0,
  "explanation": "توضیح پاسخ صحیح به فارسی"
}}
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,  # برای هیچ‌وقت تکراری نشدن سوالات
        )
        text = completion.choices[0].message.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        text = clean_text(text)
        return json.loads(text)
    except Exception as e:
        logger.error(f"Quiz Error: {e}")
        return None

# ================== 2. Short Story Functions ==================
def generate_story_post() -> str:
    levels = ["A2 (Elementary)", "B1 (Intermediate)", "B2 (Upper-Intermediate)", "C2 (Advance)"]
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

# ================== 3. World News Functions ==================
def fetch_latest_world_news_rss() -> list:
    """دریافت آخرین تیترهای خبری جهان از فید RSS بی‌بی‌سی"""
    rss_url = "http://feeds.bbci.co.uk/news/world/rss.xml"
    news_items = []
    try:
        req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            
            for item in root.findall('./channel/item')[:3]:  # ۳ خبر برتر
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

# ================== Grammar Functions ==================
def generate_grammar_post_vocab(grammar_item: dict) -> str:
    level = grammar_item.get("level", "A1-A2")
    title = grammar_item.get("title", "")
    structure = grammar_item.get("structure", "")
    explanation = grammar_item.get("explanation_fa", "")
    examples = grammar_item.get("examples", [])
    
    examples_text = "\n".join([f"• {ex}" for ex in examples])
    
    prompt = f"""
You are an expert English teacher creating an engaging, simple grammar lesson post for Telegram.

Target Level: {level}
Grammar Topic: {title}
Structure/Formula: {structure}
Persian Explanation: {explanation}
Raw Examples: {examples_text}

Format the post EXACTLY using standard HTML tags (NO asterisks *):

📘 <b>Grammar Lesson ({level})</b>
📌 <b>موضوع: {title}</b>

🔹 <b>ساختار / فرمول:</b>
<code>{structure}</code>

💡 <b>توضیح به زبان ساده:</b>
{explanation}

🟢 <b>مثال‌های کاربردی:</b>
[Reformatted examples with the grammar target wrapped in <b> tags + Persian translation for each example]

✍️ <b>تمرین کوتاه:</b>
[Write 1 short sentence with a blank for members to complete in group comments]
🟣 [ترجمه فارسی سوال تمرین]

CRITICAL RULES:
1. ALL bold tags must be <b> and </b>. Use <code> for formulas.
2. Separate English and Persian text clearly into separate lines.
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
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": GROUP_CHAT_ID, "text": text, "parse_mode": "HTML"}).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=15):
        return True

# ================== Web Routes ==================
## مسیر ۱: پست عمومی هوش مصنوعی
@app.route("/", methods=["GET"])
def health():
    return "Bot is alive!", 200

@app.route("/post", methods=["GET", "POST"])
def trigger_post():
    try:
        text = generate_educational_post()
        if not text:
            return "Failed", 500
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = json.dumps({
            "chat_id": GROUP_CHAT_ID, 
            "text": text,
            "parse_mode": "HTML"
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=15):
            return "Post sent!", 200
    except Exception as e:
        return f"Error: {e}", 500
        
# مسیر ۲: پست آموزشی بر اساس JSON کتاب
@app.route("/post_vocab", methods=["GET", "POST"])
def trigger_post_vocab():
    vocab_item = get_vocab_for_post()
    if not vocab_item:
        return "No JSON data found", 404
    text = generate_educational_post_vocab(vocab_item)
    if text and send_telegram_message(text):
        return "Post Vocab sent!", 200
    return "Failed", 500

#========== مسیر نقل قول ===========
# مسیر  3نقل‌قول مستخرج از فایل‌های JSON
@app.route("/quote", methods=["GET", "POST"])
def trigger_quote_vocab():
    quote_item = get_quote_from_data()
    if not quote_item:
        return "No JSON quote data found", 404
        
    text = generate_quote_post_vocab(quote_item)
    if text and send_telegram_message(text):
        return "Quote sent!", 200
    return "Failed", 500
    
#======= مسیر کوئیز =========
# مسیر 4: ارسال کوئیز به صورت نظرسنجی
@app.route("/quiz", methods=["GET", "POST"])
def trigger_quiz():
    try:
        quiz_data = generate_quiz_data()
        if not quiz_data:
            return "Failed", 500
        
        # دریافت سطح زبانی تعیین‌شده از هوش مصنوعی
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
        return f"Error: {e}", 500

# مسیر ۵: کوییز مستخرج از JSON کتاب
@app.route("/quiz_vocab", methods=["GET", "POST"])
def trigger_quiz_vocab():
    quiz_data = get_quiz_from_data()
    if not quiz_data:
        return "No JSON quiz data found", 404
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPoll"
    payload = json.dumps({
        "chat_id": GROUP_CHAT_ID,
        "question": f"🎯 کوئیز ({quiz_data['level']}):\n{quiz_data['question']}",
        "options": quiz_data['options'],
        "type": "quiz",
        "correct_option_id": quiz_data['correct_option_index'],
        "explanation": quiz_data['explanation']
    }).encode('utf-8')
    
    req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=15):
        return "Quiz Vocab sent!", 200

#========= مسیر داستان- این مسیرها رو زیر خود توابع هم میشه نوشت و مشکلی نداره
@app.route("/story", methods=["GET", "POST"])
def trigger_story():
    text = generate_story_post()
    if text and send_telegram_message(text):
        return "Story sent!", 200
    return "Failed", 500

# مسیر اخبار========
app.route("/news", methods=["GET", "POST"])
def trigger_news():
    text = generate_news_post()
    if text and send_telegram_message(text):
        return "News sent!", 200
    return "Failed", 500

#======= مسیر گرامر
@app.route("/grammar_vocab", methods=["GET", "POST"])
def trigger_grammar_vocab():
    grammar_item = get_grammar_from_data()
    if not grammar_item:
        return "No JSON grammar data found", 404
        
    text = generate_grammar_post_vocab(grammar_item)
    if text and send_telegram_message(text):
        return "Grammar Vocab sent!", 200
    return "Failed", 500
    
#======================
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        update_dict = request.get_json(force=True)
        asyncio.run(process_telegram_update(update_dict))
        return "ok", 200
    except Exception:
        return "error", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
