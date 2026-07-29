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
GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # کلید گروق که تازه گرفتید
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# کلاینت گروق (با سرعت فوق‌العاده بالا)
client = Groq(api_key=GROQ_API_KEY)
MODEL_NAME = "llama-3.3-70b-versatile"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

TOPICS = [
    "یک کلمه یا اصطلاح انگلیسی روزمره با معنی فارسی، مثال و تلفظ اون به صورت فونتیک",
    "یک نکته گرامری کوتاه و کاربردی انگلیسی",
    "یک دیالوگ انگلیسی کوتاه ۲ نفره مناسب تمرین مکالمه یا پارتنر‌یابی",
    "یک اصطلاح (idiom) انگلیسی با معنی و مثال",
    "یک سوال جالب انگلیسی برای شروع مکالمه بین پارتنرهای زبانی به همراه مثال انگلیسی و با ترجمه فارسی",
      " یک کوئیز انگلیسی واسه سطح زبانی متوسط و پیشرفته",
      "یک جوک یا عبارت طنز انگلیسی",
    "یک اصطلاح پیشرفته (Advanced Idiom یا Phrasal Verb) با معنی دقیق، مثال و مترادف",
        "یک ساختار گرامری سطح بالا (C1) با فرمول و مثال کاربردی",
        "یک عبارت کاربردی برای بحث‌های آکادمیک یا بیزینس (Professional English)",
      "یک دیالوگ یا جمله قصار انگلیسی با ذکر نام فیلم یا اون شخص مشهور که میتونی از این سایت (https://quotes.toscrape.com) اون رو برداری",
    "یک اشتباه رایج زبان‌آموزان ایرانی در انگلیسی و شکل درست آن",
]

# ================== توابع هوش مصنوعی (Groq) ==================

def generate_educational_post() -> str:
post_types = [
    "یک کلمه یا اصطلاح انگلیسی روزمره با معنی فارسی، مثال و تلفظ اون به صورت فونتیک",
    "یک نکته گرامری کوتاه و کاربردی انگلیسی",
    "یک دیالوگ انگلیسی کوتاه ۲ نفره مناسب تمرین مکالمه یا پارتنر‌یابی",
    "یک اصطلاح (idiom) انگلیسی با معنی و مثال",
    "یک سوال جالب انگلیسی برای شروع مکالمه بین پارتنرهای زبانی به همراه مثال انگلیسی و با ترجمه فارسی",
      " یک کوئیز انگلیسی واسه سطح زبانی متوسط و پیشرفته",
      "یک جوک یا عبارت طنز انگلیسی",
    "یک اصطلاح پیشرفته (Advanced Idiom یا Phrasal Verb) با معنی دقیق، مثال و مترادف",
        "یک ساختار گرامری سطح بالا (C1) با فرمول و مثال کاربردی",
        "یک عبارت کاربردی برای بحث‌های آکادمیک یا بیزینس (Professional English)",
    "یک اشتباه رایج زبان‌آموزان ایرانی در انگلیسی و شکل درست آن",
    ]
    chosen_topic = random.choice(post_types)
    
    prompt = f"""
You are an expert, professional English teacher for an upper-intermediate and advanced (B2-C1) level partner-learning group. 
Create an engaging, clean, and well-structured educational post in Persian and English based on this topic: {chosen_topic}.

You MUST strictly follow these rules:
1. **Target Audience:** The language level must strictly be **Upper-Intermediate to Advanced (B2-C1)**. Avoid basic words like "hello", "good", "happy". Use sophisticated vocabulary.
2. **Formatting & Bold Text:** Use standard Telegram Markdown. To make text bold, wrap it strictly with double asterisks like **this**. Do NOT use HTML tags like <b>.
3. **Emojis:** Use emojis neatly and cleanly. Maximum ONE relevant emoji per line or section heading. Never stack multiple emojis together.
4. **Structure of the Post:** Your output must include these exact sections with clear spacing:
   - 🌟 **Topic Title** (Bold the title)
   - 📖 **Explanation & Context** (Explain the advanced concept clearly)
   - 💡 **Famous Quote:** Include a short, inspiring quote by a famous figure that uses or relates to Advanced Quiz or Topic Title.
   - 🎯 **Advanced Quiz:** A multiple-choice or fill-in-the-blank question suitable for B2-C1 levels to test members.

Output ONLY the final post text in Persian/English mix. Do not add introductory or conversational filler text.

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
        return f"❌ خطای گروق:\n{str(e)}"

def generate_reply(user_text: str) -> str:
    prompt = f"""
تو یک دستیار دوستانه، صبور و مفید برای گروه یادگیری زبان انگلیسی و پارتنر‌یابی هستی.
به پیام کاربر به زبان فارسی یا انگلیسی (هرکدام مناسب‌تره) جواب بده.
کوتاه، مفید و تشویق‌کننده باش. پیام کاربر: {user_text}
"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"خطای گروق در پاسخ به کاربر: {e}")
        return f"❌ خطای گروق در پاسخ:\n{str(e)}"

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
    return "Bot is alive and powered by Groq!", 200

@app.route("/post", methods=["GET", "POST"])
def trigger_post():
    try:
        text = generate_educational_post()
        
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
