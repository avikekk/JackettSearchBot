import requests
from pyrogram.types import Message

async def check_ptp(message: Message):
    try:
        response = requests.get("https://passthepopcorn.me", timeout=5)
        response.raise_for_status()
        await message.reply_text("chal raha hai")
    except (requests.RequestException, requests.Timeout):
        await message.reply_text("gaya bhai")
