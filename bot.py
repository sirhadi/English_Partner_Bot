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

#======== تایع نقل قول ============
def generate_quote_post() -> str:
    time_context = get_time_context()
    
    # دسته‌بندی‌های بسیار متنوع برای نقل‌قول
    categories = [
        "Philosophy & Deep Thinking", "Science & Astronomy", "Literature & Writing", 
        "Leadership & Courage", "Art & Creativity", "Mindfulness & Peace", 
        "Perseverance & Resilience", "Technology & Future", "Friendship & Human Nature",
        "Habits & Time Management", "Success & Ambition"
    ]
    
    chosen_category = random.choice(categories)
    time_seed = datetime.now().strftime("%Y%m%d%H%M%S%f")

    prompt = f"""
You are an inspiring English teacher creating a Telegram post featuring a famous quote.
- Category: {chosen_category}
- Current time context: {time_context}
- Unique Request Hash: {time_seed}

Select a meaningful quote strictly from the field of "{chosen_category}". Avoid clichés if possible.

Generate the post following this EXACT layout:
🐣<b>Quote of the Day</b>

<blockquote><b>"English quote here"</b>
— <i>Author Name</i></blockquote>

<b>ترجمه</b> 🇮🇷 
<blockquote>"Persian translation here"</blockquote>

✍️ <b>نکته زبانی (Vocabulary & Structure):</b>
🔹 Explain 1-2 interesting vocabulary words, idioms, or grammar structures used in this quote (in Persian).

🤔 <b>What do you think?</b>
[An open-ended question in English about the quote's theme]
🟣 [ترجمه فارسی سوال]

CRITICAL RULES:
1. STRICT SCRIPT RULE: All Persian text MUST be written strictly using the standard Persian alphabet.
2. Formatting: Use <b> for bold, <i> for italics, and <blockquote> and </blockquote> for Telegram quote blocks. DO NOT use asterisks (*).
Output ONLY the final Telegram post text.
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system", 
                    "content": "You are a professional English-Persian translator. Generate Persian text strictly using standard Persian alphabet."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7, # دمای بالاتر برای تضمین تنوع زیاد
        )
        return clean_text(completion.choices[0].message.content.strip())
    except Exception as e:
        logger.error(f"Quote Error: {e}")
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
Generate a completely original, unique multiple-choice English grammar or vocabulary quiz question.
- Grammar/Vocabulary Focus: {chosen_topic}
- Sentence Context/Theme: {chosen_context}
- Unique Request Hash: {time_seed}

Return a valid JSON object ONLY (no extra text, no markdown code blocks). Exact structure:
{{
  "level": "سطح زبانی به فارسی همراه با سطح CEFR (مثلاً: سطح متوسط B1 یا سطح پیشرفته C1)",
  "question": "متن سوال چهارگزینه ای به انگلیسی (حتما یک جمله داستانی مرتبط با {chosen_context} باشد و از جملات تکراری کتابی استفاده نکن)",
  "options": ["گزینه اول", "گزینه دوم", "گزینه سوم", "گزینه چهارم"],
  "correct_option_index": 0,
  "explanation": "توضیح کوتاه پاسخ صحیح به فارسی"
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

# ================== Web Routes ==================
#مسیر 1 ارسال پست
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

# مسیر ۲: ارسال نقل‌قول روز
@app.route("/quote", methods=["GET", "POST"])
def trigger_quote():
    try:
        text = generate_quote_post()
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
            return "Quote sent!", 200
    except Exception as e:
        return f"Error: {e}", 500

# مسیر ۳: ارسال کوئیز به صورت نظرسنجی
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
