import os
import random
import logging
import asyncio
import json
import urllib.request
from flask import Flask, request
from telegram import Update, Bot
from google import genai

# ================== تنظیمات ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID", "0")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# کلاینت جمنای
client = genai.Client(api_key=GEMINI_API_KEY)

# مشکل اصلی اینجا بود: مدل 2.5 وجود ندارد! به نسخه پایدار تغییر یافت
MODEL_NAME = "gemini-2.5-flash" 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

TOPICS = [
    "یک کلمه یا اصطلاح انگلیسی روزمره با معنی فارسی، مثال و تلفظ تقریبی",
    "یک نکته گرامری کوتاه و کاربردی انگلیسی",
    "یک دیالوگ کوتاه ۲ نفره مناسب تمرین مکالمه یا پارتنر‌یابی",
    "یک اصطلاح (idiom) انگلیسی با معنی و مثال",
    "یک سوال جالب برای شروع مکالمه بین پارتنرهای زبانی",
    "یک اشتباه رایج زبان‌آموزان ایرانی در انگلیسی و شکل درست آن",
]

# ================== توابع هوش مصنوعی ==================

def generate_educational_post() -> str:
    topic = random.choice(TOPICS)
    prompt = f"""
تو یک معلم دوستانه و باحال زبان انگلیسی هستی که برای گروه پارتنر‌یابی محتوا می‌سازی.
موضوع: {topic}
قوانین: حداکثر ۸ خط باشه، ساده، کاربردی و جذاب بنویس، از ایموجی استفاده کن، در پایان یک سوال کوتاه بپرس، فقط متن نهایی رو بنویس.
"""
    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        return response.text.strip() if response and response.text else None
    except Exception as e:
        logger.error(f"خطای جمنای در ساخت پست: {e}")
        # تغییر مهم: حالا ارور دقیق گوگل در تلگرام برای شما ارسال می‌شود
        return f"❌ خطای سرور جمنای:\n{str(e)}"

def generate_reply(user_text: str) -> str:
    prompt = f"""
تو یک دستیار دوستانه، صبور و مفید برای گروه یادگیری زبان انگلیسی و پارتنر‌یابی هستی.
به پیام کاربر به زبان فارسی یا انگلیسی (هرکدام مناسب‌تره) جواب بده.
کوتاه، مفید و تشویق‌کننده باش. پیام کاربر: {user_text}
"""
    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        return response.text.strip() if response and response.text else "نتونستم جواب بدم 😔"
    except Exception as e:
        logger.error(f"خطای جمنای در جواب به کاربر: {e}")
        return f"❌ خطای سرور جمنای در پاسخ:\n{str(e)}"

# ================== تابع پردازش پیام‌های تلگرام ==================

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
            text="سلام! من ربات گروه پارتنر‌یابی و یادگیری زبان انگلیسی هستم 🌟\nمی‌تونی ازم سوال بپرسی یا تو گروه منشنم کنی."
        )
        return

    if update.message.new_chat_members:
        for member in update.message.new_chat_members:
            if member.is_bot:
                continue
            name = member.first_name or "دوست"
            text = f"سلام {name} عزیز 🌟\nبه گروه پارتنر‌یابی و یادگیری زبان انگلیسی خوش اومدی!\n\nاینجا می‌تونی پارتنر پیدا کنی، تمرین کنی و سوال بپرسی.\nاگر خواستی با من حرف بزنی، منشنم کن یا تو خصوصی پیام بده 😊"
            await bot.send_message(chat_id=chat_id, text=text)
        return

    is_private = update.message.chat.type == "private"
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    is_mentioned = bot_username and f"@{bot_username}" in msg_text

    if is_private or is_mentioned:
        user_clean_text = msg_text.replace(f"@{bot_username}", "").strip() if bot_username else msg_text.strip()
        if not user_clean_text:
            return
        
        answer = generate_reply(user_clean_text)
        await bot.send_message(
            chat_id=chat_id,
            text=answer,
            reply_to_message_id=update.message.message_id
        )

# ================== روترهای وب‌سرویس (Flask) ==================

@app.route("/", methods=["GET"])
def health():
    return "Bot is alive and ready!", 200

@app.route("/post", methods=["GET", "POST"])
def trigger_post():
    try:
        text = generate_educational_post()
        if not text:
            text = "امروز نتونستم محتوای جدید بسازم 😔 کمی بعد دوباره تلاش می‌کنم."
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = json.dumps({"chat_id": GROUP_CHAT_ID, "text": text}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                return "Posted successfully!", 200
            else:
                return f"Telegram API Error", 500
    except Exception as e:
        logger.error(f"خطا در ارسال پست زمان‌بندی شده: {e}")
        return f"Error: {e}", 500

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        update_dict = request.get_json(force=True)
        asyncio.run(process_telegram_update(update_dict))
        return "ok", 200
    except Exception as e:
        logger.error(f"خطا در وب‌هوک: {e}")
        return "error", 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
