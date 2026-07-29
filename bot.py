import os
import random
import logging
import asyncio
import json
import urllib.request
from flask import Flask, request
from telegram import Update, Bot
from groq import Groq

# ================== تنظیمات ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID", "0")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

client = Groq(api_key=GROQ_API_KEY)
MODEL_NAME = "llama-3.3-70b-versatile"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ================== هوش مصنوعی: ساخت پست آموزشی ==================
def generate_educational_post() -> str:
        topics = [
        "یک کلمه یا اصطلاح انگلیسی روزمره با معنی فارسی، مثال و تلفظ فونتیک آن",
        "یک نکته گرامری کوتاه و کاربردی انگلیسی",
        "یک دیالوگ انگلیسی کوتاه دو نفره مناسب تمرین مکالمه و پارتنریابی",
        "یک اصطلاح idiom انگلیسی با معنی و مثال",
        "یک سوال جالب انگلیسی برای شروع مکالمه بین پارتنرهای زبانی به همراه مثال و ترجمه فارسی",
        "یک کوئیز انگلیسی برای سطح زبانی متوسط و پیشرفته",
        "یک جوک یا عبارت طنز انگلیسی",
        "یک اصطلاح پیشرفته Advanced Idiom یا Phrasal Verb با معنی دقیق، مثال و مترادف",
        "یک ساختار گرامری سطح بالا C1 با فرمول و مثال کاربردی",
        "یک عبارت کاربردی برای بحث های آکادمیک و بیزینس Professional English",
        "یک اشتباه رایج زبان آموزان ایرانی در انگلیسی و شکل درست آن"
        ]
    chosen_topic = random.choice(topics)
    
    prompt = f"""
You are an expert English teacher for an upper-intermediate and advanced (B2-C1) level group. 
Create an educational post in Persian and English based on this topic: {chosen_topic}.

Rules:
1. Level: Upper-Intermediate to Advanced (B2-C1).
2. Formatting: Use standard Markdown (wrap bold texts with **).
3. Emojis: Use max one clean emoji per line. Do not stack emojis.
4. Structure:
   - 🌟 **Topic Title**
   - 📖 **Explanation & Context**
   - 💡 **Famous Quote:** A short inspiring quote by a famous figure.
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
        logger.error(f"خطای گروق در ساخت پست: {e}")
        return None

# ================== هوش مصنوعی: ساخت سوال کوئیز (به صورت ساختاریافته) ==================
def generate_quiz_data() -> dict:
    prompt = """
Generate a multiple-choice English grammar or vocabulary quiz question suitable for B2-C1 levels.
You must return a valid JSON object ONLY (no extra text, no markdown code blocks like ```json) with this exact structure:
{
  "question": "متن سوال چهارگزینه ای به انگلیسی یا فارسی",
  "options": ["گزینه اول", "گزینه دوم", "گزینه سوم", "گزینه چهارم"],
  "correct_option_index": 0,
  "explanation": "توضیح کوتاه پاسخ صحیح به فارسی"
}
Note: "correct_option_index" must be an integer from 0 to 3 indicating the correct choice.
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        text = completion.choices[0].message.content.strip()
        # پاکسازی اضافی برای جلوگیری از خطای فرمت
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        logger.error(f"خطای ساخت کوئیز: {e}")
        return None

# ================== پردازش پیام‌های تلگرام ==================
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
            text="سلام! من ربات گروه پارتنر‌یابی و یادگیری زبان انگلیسی هستم 🌟"
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
        
        # پاسخ به کاربر با هوش مصنوعی
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": f"به عنوان دستیار آموزش زبان به این پیام کوتاه جواب بده: {user_clean_text}"}],
            temperature=0.7,
        )
        answer = completion.choices[0].message.content.strip()
        await bot.send_message(
            chat_id=chat_id,
            text=answer,
            reply_to_message_id=update.message.message_id,
            parse_mode="Markdown"
        )

# ================== روترهای وب‌سرویس (Flask) ==================

@app.route("/", methods=["GET"])
def health():
    return "Bot is alive!", 200

# مسیر ۱: ارسال پست آموزشی (می‌تونید یه کرون‌جاب جدا براش بذارید)
@app.route("/post", methods=["GET", "POST"])
def trigger_post():
    try:
        text = generate_educational_post()
        if not text:
            return "Failed to generate post", 500
        
        url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){BOT_TOKEN}/sendMessage"
        payload = json.dumps({
            "chat_id": GROUP_CHAT_ID, 
            "text": text,
            "parse_mode": "Markdown"
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            return "Post sent successfully!", 200
    except Exception as e:
        return f"Error: {e}", 500

# مسیر ۲: ارسال کوئیز به صورت نظرسنجی واقعی (میتونید یک کرون‌جاب جدا براش روی این لینک تنظیم کنید)
@app.route("/quiz", methods=["GET", "POST"])
def trigger_quiz():
    try:
        quiz_data = generate_quiz_data()
        if not quiz_data:
            return "Failed to generate quiz", 500
        
        # استفاده از متد sendPoll تلگرام برای ساخت نظرسنجی واقعی
        url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){BOT_TOKEN}/sendPoll"
        
        payload = json.dumps({
            "chat_id": GROUP_CHAT_ID,
            "question": f"🎯 کوئیز سطح پیشرفته:\n{quiz_data['question']}",
            "options": quiz_data['options'],
            "type": "quiz",
            "correct_option_id": quiz_data['correct_option_index'],
            "explanation": quiz_data['explanation']
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            return "Quiz poll sent successfully!", 200
    except Exception as e:
        logger.error(f"خطا در ارسال کوئیز: {e}")
        return f"Error: {e}", 500

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        update_dict = request.get_json(force=True)
        asyncio.run(process_telegram_update(update_dict))
        return "ok", 200
    except Exception as e:
        return "error", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
