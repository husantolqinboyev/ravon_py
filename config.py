# config.py
import os
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()

# Bot va API sozlamalari - faqat .env dan olish
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# OpenRouter sozlamalari
OPENROUTER_URL = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1/chat/completions")
MODEL_NAME = os.getenv("MODEL_NAME", "google/gemini-3-flash-preview")

# Kanal sozlamalari
REQUIRED_CHANNEL = os.getenv("REQUIRED_CHANNEL", "@englishwithSanatbek")
REQUIRED_CHANNEL_ID = int(os.getenv("REQUIRED_CHANNEL_ID", "-1003014655042"))

# Ma'lumotlar bazasi nomi
DB_NAME = os.getenv("DB_NAME", "ravon_ai.db")

# Admin va O'qituvchi IDlari
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "6613269992").split(",") if x.strip()]
TEACHER_IDS = [int(x.strip()) for x in os.getenv("TEACHER_IDS", "5775880996").split(",") if x.strip()]

# Render ping URL
PING_URL = os.getenv("PING_URL", "https://ravon-py.onrender.com/ping")

# Ma'lumotlar bazasi yo'li (Render uchun)
DB_PATH = os.path.join(os.getcwd(), DB_NAME)

# Debug: API keylarni tekshirish
print(f"Config loaded:")
print(f"BOT_TOKEN: {'✅' if BOT_TOKEN else '❌ Missing'}")
print(f"OPENROUTER_API_KEY: {'✅' if OPENROUTER_API_KEY else '❌ Missing'}")
print(f"MODEL_NAME: {MODEL_NAME}")
print(f"REQUIRED_CHANNEL: {REQUIRED_CHANNEL}")
