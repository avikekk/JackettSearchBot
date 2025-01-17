import requests
from telegram import Update
from telegram.ext import CallbackContext

def check_ptp(update: Update, context: CallbackContext):
    try:
        response = requests.get("https://passthepopcorn.me", timeout=5)
        response.raise_for_status()
        update.message.reply_text("chal raha hai")
    except (requests.RequestException, requests.Timeout):
        update.message.reply_text("gaya bhai")
