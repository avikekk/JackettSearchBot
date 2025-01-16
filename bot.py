import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegraph_helper import TelegraphHelper
import requests
import xml.etree.ElementTree as ET
import math
from datetime import datetime
from ptp_checker import check_ptp

class TorrentSearchBot:
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
        jackett_search_url = self._get_jackett_search_url(query)

        try:
            response = requests.get(jackett_search_url)
            response.raise_for_status()

            if response.text.strip():
                # Parse results with Golden Popcorn filter
                all_results = self._parse_jackett_response_for_paste(response.content, golden_popcorn)

                # Check if there are any results before proceeding
                if not all_results:
                    update.message.reply_text('No Results' + (' (with GP)' if golden_popcorn else ''))
                    context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
                    return

                # Send results to Telegraph if available
                telegraph_url = self._send_results_to_telegraph(all_results)

                if not telegraph_url:
                    update.message.reply_text("Telegraph Error")
                    context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
                    return

                # Process limited results for inline display
                limited_results = self._parse_jackett_response(response.content, golden_popcorn)
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

    def _parse_jackett_response(self, response_content, golden_popcorn=False):
        root = ET.fromstring(response_content)
        results = []

        for item in root.findall(".//item"):
            title = item.find('title').text
            
            # Skip if Golden Popcorn filter is active and title doesn't contain it
            if golden_popcorn and "Golden Popcorn" not in title:
                continue
                
            size_bytes = int(item.find('size').text)
            size_readable = self._convert_size(size_bytes)
            pub_date = item.find('pubDate').text
            formatted_pub_date = self._format_pub_date(pub_date)

            result_text = (
                f'<b>Title:</b> <code>{title}</code>\n'
                f'<b>Age:</b> {formatted_pub_date}\n'
                f'<b>Size:</b> {size_readable}\n'
            )
            results.append(result_text)

        return results

    def _parse_jackett_response_for_paste(self, response_content, golden_popcorn=False):
        root = ET.fromstring(response_content)
        results = []

        for item in root.findall(".//item"):
            title = item.find('title').text
            
            # Skip if Golden Popcorn filter is active and title doesn't contain it
            if golden_popcorn and "Golden Popcorn" not in title:
                continue
                
            size_bytes = int(item.find('size').text)
            size_readable = self._convert_size(size_bytes)
            pub_date = item.find('pubDate').text
            formatted_pub_date = self._format_pub_date(pub_date)

            result_text = (
                f'Title: {title}\n'
                f'Age: {formatted_pub_date}\n'
                f'Size: {size_readable}\n'
            )
            results.append(result_text)

        return results

    def _get_jackett_search_url(self, query):
        if query.startswith("tt") and query[2:].isdigit():
            return f'{self.jackett_url}/api/v2.0/indexers/all/results/torznab/api?apikey={self.jackett_api_key}&imdbid={query}'
        else:
            query = requests.utils.quote(query)
            return f'{self.jackett_url}/api/v2.0/indexers/all/results/torznab/api?apikey={self.jackett_api_key}&t=search&q={query}'

    def _convert_size(self, size_bytes):
        if size_bytes == 0:
            return "0 B"
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"

    def _format_pub_date(self, pub_date):
        date_obj = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
        time_elapsed = datetime.now(date_obj.tzinfo) - date_obj

        if time_elapsed.days > 0:
            return f'{time_elapsed.days} d'
        else:
            hours, remainder = divmod(time_elapsed.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            if hours > 0:
                return f'{hours} h'
            elif minutes > 0:
                return f'{minutes} m'
            else:
                return f'{seconds} s'

    def _send_results_to_telegraph(self, results):
        formatted_results = "<br>".join([result.replace("\n", "<br>") for result in results])

        try:
            response = self.telegraph_helper.create_page(
                title="Search Results",
                html_content=formatted_results,
                author_name="TorrentSearchBot"
            )
            return response.get("url")
        except Exception as e:
            self.logger.error(f'Error Pasting to Telegraph: {str(e)}')
            return None

    def _is_authorized(self, user_id, chat_id):
        return chat_id in self.authorized_chat_ids or user_id == self.owner_id

    def run(self):
        self.updater.start_polling()
        self.updater.idle()