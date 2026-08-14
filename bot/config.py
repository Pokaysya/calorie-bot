import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/calorie_bot.db')
WEBAPP_URL = os.getenv('WEBAPP_URL', '')
PORT = int(os.getenv('PORT', 8080))
ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', '').split(','))) if os.getenv('ADMIN_IDS') else []
