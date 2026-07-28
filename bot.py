import os
import random
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ChatMemberHandler, filters, ContextTypes
import google.generativeai as genai

# ================== تنظیمات ==================
BOT_TOKEN = os.getenv("6756204974:AAG_FOKPBLfwcTHK3rpRrBKcatYNRx90SKE")
GROUP_CHAT_ID = int(os.getenv("-1002093824468"))
GEMINI_API_KEY = os.getenv("AQ.Ab8RN6Iw27-MBG19f5UA63NDQLxU_NPGYnK4hcNHiLRZHwYxzg")
WEBHOOK_URL = os.getenv("https://english-partner-bot.onrender.com")  # مثلاً https://your-app.onrender.com

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

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

async def generate_educational_post() -> str:
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
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"خطا در تولید محتوا: {e}")
        return "امروز یه مشکل فنی پیش اومد 😔 فردا دوباره مطالب آموزشی میاد!"

async def post_educational():
    try:
        text = await generate_educational_post()
        await application.bot.send_message(chat_id=GROUP_CHAT_ID, text=text)
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
        response = model.generate_content(prompt)
        answer = response.text.strip()
        await update.message.reply_text(answer)
    except Exception as e:
        logger.error(f"خطا در جواب: {e}")
        await update.message.reply_text("متأسفانه الان نتونستم جواب بدم 😔 کمی بعد دوباره امتحان کن.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! من ربات گروه پارتنر‌یابی و یادگیری زبان انگلیسی هستم 🌟\n"
        "می‌تونی ازم سوال بپرسی یا تو گروه منشنم کنی."
    )

# ثبت هندلرها
application.add_handler(CommandHandler("start", start))
application.add_handler(ChatMemberHandler(welcome_new_member, ChatMemberHandler.CHAT_MEMBER))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route("/", methods=["GET"])
def health():
    return "Bot is alive!", 200

@app.route("/post", methods=["GET", "POST"])
async def trigger_post():
    # برای امنیت ساده می‌تونی یه secret اضافه کنی
    success = await post_educational()
    return ("Posted!" if success else "Failed"), 200 if success else 500

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "ok", 200

if __name__ == "__main__":
    # تنظیم webhook موقع استارت
    import asyncio
    async def setup():
        await application.bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")
        logger.info(f"Webhook set to {WEBHOOK_URL}/{BOT_TOKEN}")
    
    asyncio.get_event_loop().run_until_complete(setup())
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
