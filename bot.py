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

client = Groq(api_key=GROQ_API_KEY)
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
    "یک کوئیز انگلیسی برای سطح زبانی متوسط و پیشرفته",
    "یک جوک یا عبارت طنز انگلیسی",
    "یک اصطلاح پیشرفته Advanced Idiom یا Phrasal Verb با معنی دقیق، مثال و مترادف",
    "یک ساختار گرامری سطح بالا C1 با فرمول و مثال کاربردی",
    "یک ساختار گرامری سطح بالا B2 با فرمول و مثال کاربردی",
    "یک عبارت کاربردی برای بحث های آکادمیک و بیزینس Professional English",
    "یک اشتباه رایج زبان آموزان ایرانی در انگلیسی و شکل درست آن"
]

# ================== AI Functions ==================
def generate_educational_post() -> str:
    chosen_topic = random.choice(TOPICS)
    
    prompt = f"""
You are an expert English teacher for an intermediate and an upper-intermediate and advanced (B2-C1) level group. 
Create an educational post in Persian and English by using 1100 Essential Words and 4000 Essential Words based on this topic: {chosen_topic}.

Rules:
1. Level: Intermediate to Upper-Intermediate to Advanced (A1-C1).
2. Formatting: Use HTML tags for bold text. Wrap bold texts strictly with <b> and </b>. Do not use asterisks (*).
3. Emojis: Use max one clean emoji per line. Do not stack emojis.
4. Structure:
   - 🌟 <b>Topic Title</b>
   - 📖 <b>Explanation & Context</b>
   - 💡 <b>Famous Quote:</b> in the next line write A short inspiring quote by a famous figure related to Topic Title.
   - write the translation
   - after each section let a blank line (to be clearly redable).
   - use other colorful icons for their translation
   - add the level with an emoji in the first line in <b> and </b> html tag (for example: <b>🟢level A2- Intermediate</b>)
   - never use Chinese or Japanese letters in the text
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

def generate_quiz_data() -> dict:
    prompt = """
Generate a multiple-choice English grammar or vocabulary quiz question suitable for levels A2 to C1, add the level with an emoji in the first line in <b> and </b> html tag (for example: <b>🟢level A2- Intermediate</b>).
Return a valid JSON object ONLY (no extra text, no markdown code blocks). Exact structure:
{
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
            temperature=0.5,
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
        with urllib.request.urlopen(req):
            return "Post sent!", 200
    except Exception as e:
        return f"Error: {e}", 500

@app.route("/quiz", methods=["GET", "POST"])
def trigger_quiz():
    try:
        quiz_data = generate_quiz_data()
        if not quiz_data:
            return "Failed", 500
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPoll"
        payload = json.dumps({
            "chat_id": GROUP_CHAT_ID,
            "question": f"🎯 کوئیز سطح پیشرفته:\n{quiz_data['question']}",
            "options": quiz_data['options'],
            "type": "quiz",
            "correct_option_id": quiz_data['correct_option_index'],
            "explanation": quiz_data['explanation']
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req):
            return "Quiz sent!", 200
    except Exception as e:
        return f"Error: {e}", 500

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
