import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext
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
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )
        self.logger = logging.getLogger(__name__)

        self.updater = Updater(self.token)
        self.dp = self.updater.dispatcher
        self._register_handlers()

    def _register_handlers(self):
        self.dp.add_handler(CommandHandler("start", self.start))
        self.dp.add_handler(CommandHandler("release", self.search))
        self.dp.add_handler(CommandHandler("check", check_ptp))
    
    def start(self, update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        chat_id = update.message.chat_id

        self.logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Authorized IDs: {self.authorized_chat_ids}")

        if self._is_authorized(user_id, chat_id):
            update.message.reply_text("Bot Started")
        else:
            update.message.reply_text("Not Authorized")

    def search(self, update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        chat_id = update.message.chat_id

        if not self._is_authorized(user_id, chat_id):
            update.message.reply_text("Not Authorized")
            return

        query_args = context.args
        if not query_args:
            update.message.reply_text("Please Provide Query or IMDb ID/URL")
            return

        # Check for Golden Popcorn flag
        golden_popcorn = False
        if '-gp' in query_args:
            golden_popcorn = True
            query_args.remove('-gp')
        
        query = ' '.join(query_args)
        message = update.message.reply_text("Please Wait, Searching...")
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
                    update.message.reply_text('No Results' + (' (with GP)' if golden_popcorn else ''))
                    context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
                    return

                # Send results to Telegraph if available
                telegraph_url = self.telegraph_helper.send_results_to_telegraph(all_results)

                if not telegraph_url:
                    update.message.reply_text("Telegraph Error")
                    context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
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

                update.message.reply_text(
                    final_message_text,
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
                context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
            else:
                update.message.reply_text('No Results')

        except requests.exceptions.HTTPError as http_err:
            self.logger.error(f'HTTP Error Occurred: {http_err}')
            update.message.reply_text(f'HTTP Error Occurred')
        except Exception as e:
            self.logger.exception(f'Unexpected Error Occurred: {str(e)}')
            update.message.reply_text('Unexpected Error Occurred')

    def _is_authorized(self, user_id, chat_id):
        return chat_id in self.authorized_chat_ids or user_id == self.owner_id

    def run(self):
        self.updater.start_polling()
        self.updater.idle()
