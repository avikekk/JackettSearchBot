import os
import logging
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ParseMode
from telegraph_helper import TelegraphHelper
import requests
from ptp_checker import check_ptp
from jackett import (
    get_jackett_search_url,
    parse_jackett_response,
    parse_jackett_response_for_paste
)

class JackettSearchBot:
    def __init__(self):
        load_dotenv('config.env')
        self.token = os.getenv('TELEGRAM_TOKEN')
        self.api_id = int(os.getenv('API_ID'))
        self.api_hash = os.getenv('API_HASH')
        self.jackett_api_key = os.getenv('JACKETT_API_KEY')
        self.jackett_url = os.getenv('JACKETT_URL')
        self.default_max_results = int(os.getenv('MAX_RESULTS', 10))
        self.authorized_chat_ids = [
            int(chat_id) for chat_id in os.getenv('AUTHORIZED_CHAT_IDS', '').split(',')
            if chat_id
        ]
        self.owner_id = int(os.getenv('OWNER_ID', 0))

        self.telegraph_helper = TelegraphHelper()

        logging.basicConfig(
            format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            level=logging.INFO,
            handlers=[logging.StreamHandler()]
        )
        self.logger = logging.getLogger("JackettSearchBot")
        self.logger.info("JackettSearchBot initialized.")

        self.app = Client(
            "jackett_bot",
            api_id=self.api_id,
            api_hash=self.api_hash,
            bot_token=self.token
        )

        self._register_handlers()

    def _register_handlers(self):
        @self.app.on_message(filters.command("start"))
        async def start_handler(client, message):
            await self.start(message)

        @self.app.on_message(filters.command("release"))
        async def search_handler(client, message):
            await self.search(message)

        @self.app.on_message(filters.command("check"))
        async def check_handler(client, message):
            await check_ptp(message)
    
    async def start(self, message: Message):
        user_id = message.from_user.id
        chat_id = message.chat.id


        if self._is_authorized(user_id, chat_id):
            await message.reply_text("Bot Started")
        else:
            await message.reply_text("Not Authorized")

    async def search(self, message: Message):
        user_id = message.from_user.id
        chat_id = message.chat.id

        if not self._is_authorized(user_id, chat_id):
            await message.reply_text("Not Authorized")
            return

        # Extract query arguments from message text
        command_parts = message.text.split()[1:]  # Skip the command itself
        if not command_parts:
            await message.reply_text("Please Provide Query or IMDb ID/URL")
            return

        # Check for Golden Popcorn flag
        golden_popcorn = False
        if '-gp' in command_parts:
            golden_popcorn = True
            command_parts.remove('-gp')
        
        query = ' '.join(command_parts)
        sent_message = await message.reply_text("Please Wait, Searching...")
        jackett_search_url = get_jackett_search_url(
            self.jackett_url,
            self.jackett_api_key,
            query
        )

        try:
            response = requests.get(jackett_search_url)
            response.raise_for_status()

            if response.text.strip():
                # Parse results with Golden Popcorn filter
                all_results = parse_jackett_response_for_paste(response.content, golden_popcorn)

                # Check if there are any results before proceeding
                if not all_results:
                    await message.reply_text('No Results' + (' (with GP)' if golden_popcorn else ''))
                    await sent_message.delete()
                    return

                # Send results to Telegraph if available
                telegraph_url = self.telegraph_helper.send_results_to_telegraph(all_results)

                if not telegraph_url:
                    await message.reply_text("Telegraph Error")
                    await sent_message.delete()
                    return

                # Process limited results for inline display
                limited_results = parse_jackett_response(response.content, golden_popcorn) 
                total_results = len(limited_results)
                limited_results_text = '\n'.join(limited_results[:self.default_max_results])
                remaining_results = total_results - self.default_max_results

                if remaining_results > 0:
                    more_results_text = f"\n+ {remaining_results} <b>More Results..</b>"
                    limited_results_text += more_results_text

                header = "▫️<b><u>SEARCH RESULTS" + (" (GP)" if golden_popcorn else "") + "</u></b>\n\n"
                final_message_text = header + limited_results_text
                keyboard = [[InlineKeyboardButton("RESULTS", url=telegraph_url)]]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await message.reply_text(
                    final_message_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
                await sent_message.delete()
            else:
                await message.reply_text('No Results')

        except requests.exceptions.HTTPError as http_err:
            self.logger.error(f'HTTP Error Occurred: {http_err}')
            await message.reply_text(f'HTTP Error Occurred')
        except Exception as e:
            self.logger.exception(f'Unexpected Error Occurred: {str(e)}')
            await message.reply_text('Unexpected Error Occurred')

    def _is_authorized(self, user_id, chat_id):
        return chat_id in self.authorized_chat_ids or user_id == self.owner_id

    def run(self):
        self.logger.info("Bot is running...")
        self.app.run()
