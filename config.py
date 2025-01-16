import os
from dotenv import load_dotenv

load_dotenv('config.env')

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
JACKETT_API_KEY = os.getenv('JACKETT_API_KEY')
JACKETT_URL = os.getenv('JACKETT_URL')
MAX_RESULTS = int(os.getenv('MAX_RESULTS', 10))
AUTHORIZED_CHAT_IDS = [
    int(chat_id) for chat_id in os.getenv('AUTHORIZED_CHAT_IDS', '').split(',')
    if chat_id
]
OWNER_ID = int(os.getenv('OWNER_ID', 0))