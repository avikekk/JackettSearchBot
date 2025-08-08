## Installation

1. Clone this repository
2. Install the required dependencies:
```bash
pip install pyrogram python-dotenv requests
```

3. Create a `config.env` file with the following variables:
```env
TELEGRAM_TOKEN=your_telegram_bot_token
API_ID=your_telegram_api_id
API_HASH=your_telegram_api_hash
JACKETT_API_KEY=your_jackett_api_key
JACKETT_URL=your_jackett_url
MAX_RESULTS=10
AUTHORIZED_CHAT_IDS=id1,id2,id3
OWNER_ID=your_telegram_id
```

## Usage

### Bot Commands

- `/start` - Start the bot (only works for authorized users)
- `/release [query]` - Search for releases
  - Use `-gp` flag to filter for Golden Popcorn releases
  - Example: `/release Inception -gp`
- `/check` - Check PTP information

### Running the Bot

```bash
python main.py
```

## Project Structure

- `bot.py` - Main bot implementation with Telegram handlers
- `jackett.py` - Jackett API integration functions
- `ptp_checker.py` - PTP checking functionality
- `telegraph_helper.py` - Telegraph integration for result display
- `main.py` - Entry point of the application
- `config.env` - Configuration file
