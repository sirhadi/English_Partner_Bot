import os
import random
import logging
import asyncio
import json
import urllib.request
from flask import Flask, request
from telegram import Update, Bot
from groq import Groq

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

TOPICS = [
    "یک کلمه یا اصطلاح انگلیسی روزمره با معنی فارسی، مثال و تلفظ فونتیک آن",
    "یک نکته گرامری کوتاه و کاربردی انگلیسی",
    "یک دیالوگ انگلیسی کوتاه دو نفره مناسب تمرین مکالمه و پارتنریابی",
    "یک اصطلاح idiom انگلیسی با معنی و مثال",
    "یک سوال جالب انگلیسی برای شروع مکالمه بین پارتنرهای زبانی به همراه مثال و ترجمه فارسی",
    "یک جوک یا عبارت طنز انگلیسی",
    "یک اصطلاح مبتدی، متوسط یا پیشرفته Idiom یا Phrasal Verb با معنی دقیق، مثال و مترادف",
    "یک ساختار گرامری سطح متوسط، متوسط به بالا و بالا تا C1 با فرمول و مثال کاربردی",
    "یک عبارت کاربردی برای بحث های آکادمیک و بیزینس Professional English",
    "یک اشتباه رایج زبان آموزان ایرانی در انگلیسی و شکل درست آن"
]

# ================== AI Functions ==================
def generate_educational_post() -> str:
    chosen_topic = random.choice(TOPICS)
    
    prompt = f"""
You are a warm, friendly, and expert English teacher creating a beautifully formatted Telegram post for an upper-intermediate/advanced (B2-C1) Iranian group.

Topic: {chosen_topic}

Generate a complete educational post following this EXACT layout and emoji style:

-add the level with an emoji in the first line in <b> and </b> html tag (for example: <b>🟢level: A2</b>)
-add a blank line for clear view.

🌟 <b>Good day learners!</b> and other famous phrases.

📌 <b>[Topic Title in English & Persian]</b>

🔴 <b>[Main Phrase / Word / Structure]</b> [phonetic pronunciation in brackets if applicable]
🔹 <b>معنی:</b> [Short explanation in Persian]

🟢 <b>مثال اول:</b>
📣 [English sentence with the target phrase wrapped in <b>tags</b>]
🔹 <b>ترجمه:</b> [Persian translation]

🟡 <b>مثال دوم:</b>
🔔 [English sentence with the target phrase wrapped in <b>tags</b>]
🔸 <b>ترجمه:</b> [Persian translation]

💡 <b>نقل‌قول انگیزشی / نکته طلایی:</b>
"A short English quote related to learning or life"
💬 <b>ترجمه:</b> "ترجمه فارسی نقل‌قول"

🔵 <b>سوال برای چت و تمرین در گروه:</b>
❓ [An engaging question in English related to the topic]
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
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Post Error: {e}")
        return None

#======== تایع نقل قول ============
def generate_quote_post() -> str:
    prompt = """
You are an inspiring English teacher creating a beautifully formatted Telegram post featuring a famous quote for English learners (B2-C1 level).

Generate a quote post following this EXACT layout:

🌟 <b> نقل‌قول روز | Quote of the Day</b>

<blockquote>"English quote here"
— <i>Author Name</i></blockquote>

🇮🇷 <b>ترجمه فارسی:</b>
<blockquote>"Persian translation here"</blockquote>

💡 <b>نکته زبانی (Vocabulary & Structure):</b>
🔹 Explain 1-2 interesting vocabulary words, idioms, or grammar structures used in this quote (in Persian).

❓ <b>نظر شما چیه؟ | What do you think?</b>
[An open-ended question in English about the quote's theme]
🟣 [ترجمه فارسی سوال]

CRITICAL RULES:
1. STRICT SCRIPT RULE: All Persian text MUST be written strictly using the standard Persian alphabet. Absolutely NO Russian, Cyrillic, Chinese, or foreign scripts/characters allowed in Persian sentences.
2. Formatting: Use <b> for bold, <i> for italics, and <blockquote> and </blockquote> for Telegram quote blocks. DO NOT use asterisks (*).
3. Select inspiring, memorable quotes from famous figures (scientists, thinkers, authors, leaders).
Output ONLY the final Telegram post text.
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system", 
                    "content": "You are a professional English-Persian translator. You MUST generate Persian text using standard Persian alphabet ONLY. Never use Cyrillic, Russian, or Chinese characters."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.4,  # درجه خلاقیت کمتر برای جلوگیری از خطای توکن‌های روسی
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Quote Error: {e}")
        return None
        
#============= تابع کوئیز ===============
def generate_quiz_data() -> dict:
    prompt = """
Generate a multiple-choice English grammar or vocabulary quiz question suitable for various proficiency levels (Intermediate B1, Upper-Intermediate B2, or Advanced C1).
Return a valid JSON object ONLY (no extra text, no markdown code blocks). Exact structure:
{
  "level": "سطح زبانی به فارسی همراه با سطح CEFR (مثلاً: سطح متوسط B1 یا سطح پیشرفته C1)",
  "question": "متن سوال چهارگزینه ای به انگلیسی",
  "options": ["گزینه اول", "گزینه دوم", "گزینه سوم", "گزینه چهارم"],
  "correct_option_index": 0,
  "explanation": "توضیح کوتاه پاسخ صحیح به فارسی"
}
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        text = completion.choices[0].message.content.strip()
        text = text.replace("```json", "").replace("```", "").strip()
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
