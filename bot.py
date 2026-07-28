import os
import random
import logging
from datetime import time
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    filters,
    ContextTypes,
)
import google.generativeai as genai

# ================== تنظیمات ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))  # مثال: -1001234567890
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")  # یا gemini-1.5-flash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

async def post_educational(context: ContextTypes.DEFAULT_TYPE):
    try:
        text = await generate_educational_post()
        await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=text)
        logger.info("پست آموزشی ارسال شد")
    except Exception as e:
        logger.error(f"خطا در ارسال پست: {e}")

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

def main():
    if not all([BOT_TOKEN, GROUP_CHAT_ID, GEMINI_API_KEY]):
        raise ValueError("یکی از متغیرهای محیطی تنظیم نشده!")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatMemberHandler(welcome_new_member, ChatMemberHandler.CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # پست آموزشی در ساعات مشخص (به وقت سرور — معمولاً UTC)
    # برای ایران تقریباً ۳.۵ ساعت جلوتر حساب کن
    job_queue = app.job_queue
    for hour in [5, 9, 13, 17]:  # معادل تقریبی ۸:۳۰، ۱۲:۳۰، ۱۶:۳۰، ۲۰:۳۰ ایران
        job_queue.run_daily(post_educational, time=time(hour=hour, minute=30))

    logger.info("ربات شروع به کار کرد...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
