import os
import random
import logging
import asyncio
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, ChatMemberHandler, filters, ContextTypes
from google import genai

# ================== تنظیمات ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID", "0"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# کلاینت جدید جمنای
client = genai.Client(api_key=GEMINI_API_KEY)
MODEL_NAME = "gemini-2.5-flash"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
application = Application.builder().token(BOT_TOKEN).build()

TOPICS = [
    "یک کلمه یا اصطلاح انگلیسی روزمره با معنی فارسی، مثال و تلفظ تقریبی",
    "یک نکته گرامری کوتاه و کاربردی انگلیسی",
    "یک دیالوگ کوتاه ۲ نفره مناسب تمرین مکالمه یا پارتنر‌یابی",
    "یک اصطلاح (idiom) انگلیسی با معنی و مثال",
    "یک سوال جالب برای شروع مکالمه بین پارتنرهای زبانی",
    "یک اشتباه رایج زبان‌آموزان ایرانی در انگلیسی و شکل درست آن",
]

def generate_educational_post() -> str:
    topic = random.choice(TOPICS)
    prompt = f"""
تو یک معلم دوستانه و باحال زبان انگلیسی هستی که برای گروه پارتنر‌یابی محتوا می‌سازی.
موضوع: {topic}

قوانین:
- حداکثر ۸ خط باشه
- ساده، کاربردی و جذاب بنویس
- از ایموجی استفاده کن
- در پایان یک سوال کوتاه بپرس تا اعضا جواب بدن
- فقط متن نهایی رو بنویس، هیچ توضیح اضافه‌ای نده
"""
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"خطای Gemini: {type(e).__name__} - {e}")
        return None

async def send_educational_post():
    try:
        text = generate_educational_post()
        if not text:
            text = "امروز نتونستم محتوای جدید بسازم 😔 کمی بعد دوباره تلاش می‌کنم."
        
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(chat_id=GROUP_CHAT_ID, text=text)
        logger.info("پست آموزشی ارسال شد")
        return True
    except Exception as e:
        logger.error(f"خطا در ارسال پست: {e}")
        return False

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.chat_member.new_chat_members:
        if member.is_bot:
            continue
        name = member.first_name or "دوست"
        text = (
            f"سلام {name} عزیز 🌟\n"
            f"به گروه پارتنر‌یابی و یادگیری زبان انگلیسی خوش اومدی!\n\n"
            f"اینجا می‌تونی پارتنر پیدا کنی، تمرین کنی و سوال بپرسی.\n"
            f"اگر خواستی با من حرف بزنی، منشنم کن یا تو خصوصی پیام بده 😊"
        )
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    is_private = update.effective_chat.type == "private"
    bot_username = context.bot.username
    is_mentioned = bot_username and f"@{bot_username}" in update.message.text

    if not (is_private or is_mentioned):
        return

    user_text = update.message.text.replace(f"@{bot_username}", "").strip()
    if not user_text:
        return

    prompt = f"""
تو یک دستیار دوستانه، صبور و مفید برای گروه یادگیری زبان انگلیسی و پارتنر‌یابی هستی.
به پیام کاربر به زبان فارسی یا انگلیسی (هرکدام مناسب‌تره) جواب بده.
کوتاه، مفید و تشویق‌کننده باش.

پیام کاربر: {user_text}
"""
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        answer = response.text.strip()
        await update.message.reply_text(answer)
    except Exception as e:
        logger.error(f"خطا در جواب Gemini: {e}")
        await update.message.reply_text("متأسفانه الان نتونستم جواب بدم 😔 کمی بعد دوباره امتحان کن.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! من ربات گروه پارتنر‌یابی و یادگیری زبان انگلیسی هستم 🌟\n"
        "می‌تونی ازم سوال بپرسی یا تو گروه منشنم کنی."
    )

application.add_handler(CommandHandler("start", start))
application.add_handler(ChatMemberHandler(welcome_new_member, ChatMemberHandler.CHAT_MEMBER))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route("/", methods=["GET"])
def health():
    return "Bot is alive!", 200

@app.route("/post", methods=["GET", "POST"])
def trigger_post():
    try:
        success = asyncio.run(send_educational_post())
        return ("Posted successfully!" if success else "Failed"), 200 if success else 500
    except Exception as e:
        logger.error(f"خطا در /post: {e}")
        return f"Error: {str(e)}", 500

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        asyncio.run(application.process_update(update))
        return "ok", 200
    except Exception as e:
        logger.error(f"خطا در webhook: {e}")
        return "error", 500

def setup_webhook():
    try:
        bot = Bot(token=BOT_TOKEN)
        asyncio.run(bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}"))
        logger.info("Webhook تنظیم شد")
    except Exception as e:
        logger.error(f"خطا در تنظیم webhook: {e}")

if WEBHOOK_URL and BOT_TOKEN:
    setup_webhook()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
