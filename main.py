import requests
import json
import time
import pyshorteners
import os
from datetime import datetime
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, CallbackContext
import logging

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
API_KEY = os.getenv("GOOGLE_NEWS_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Path to the file where chat IDs will be stored
CHAT_ID_FILE = "chat_ids.txt"

# Path to the file where sent URLs will be stored
SENT_URLS_FILE = "sent_urls.txt"

# List of topics to fetch news for
topics = [
    "Artificial Intelligence",
    "Machine Learning",
    "Blockchain",
    "Cryptocurrency",
    "Startup",
    "Business",
    "Startup funding",
    "Jobs",
    "IT Jobs",
    "Tech news"
]

# Initialize requests session with retry strategy
session = requests.Session()
retry = Retry(connect=3, backoff_factor=0.5)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)

# Function to fetch news headlines from Google News API for a given topic
def fetch_news(topic):
    url = f"https://newsapi.org/v2/everything?q={topic}&apiKey={API_KEY}"
    response = session.get(url)
    if response.status_code == 429:
        logger.warning("Rate limit exceeded, sleeping for a while.")
        time.sleep(60)  # Sleep for 1 minute if rate limit is exceeded
        return []
    data = response.json()
    articles = data.get('articles', [])
    headlines = [{'title': article.get('title', 'N/A'), 'source': article.get('url', 'N/A')} for article in articles]
    return headlines

# Function to shorten URLs
def shorten_url(url):
    s = pyshorteners.Shortener()
    return s.tinyurl.short(url)

# Function to load chat IDs from file
def load_chat_ids():
    if not os.path.exists(CHAT_ID_FILE):
        return []
    with open(CHAT_ID_FILE, 'r') as file:
        chat_ids = file.read().splitlines()
    return list(set(chat_ids))  # Remove duplicates

# Function to save chat ID to file
def save_chat_id(chat_id):
    chat_ids = load_chat_ids()
    if chat_id not in chat_ids:
        chat_ids.append(chat_id)
        with open(CHAT_ID_FILE, 'a') as file:
            file.write(f"{chat_id}\n")

# Function to load sent URLs from file
def load_sent_urls():
    if not os.path.exists(SENT_URLS_FILE):
        return []
    with open(SENT_URLS_FILE, 'r') as file:
        sent_urls = file.read().splitlines()
    return set(sent_urls)  # Use a set for faster lookup

# Function to save sent URLs to file
def save_sent_urls(urls):
    with open(SENT_URLS_FILE, 'a') as file:
        for url in urls:
            file.write(f"{url}\n")

# Function to send news headlines to Telegram
def send_news_to_telegram(chat_id=None):
    bot = Bot(token=BOT_TOKEN)
    chat_ids = load_chat_ids()
    sent_urls = load_sent_urls()
    if not chat_ids and not chat_id:
        logger.info("No chat IDs found.")
        return

    headlines = []

    # Collect headlines from each topic
    for topic in topics:
        fetched_headlines = fetch_news(topic)
        for headline in fetched_headlines:
            if len(headlines) >= 5:
                break
            if headline['source'] not in sent_urls:
                headlines.append(headline)

    # Ensure only 5 headlines are sent
    headlines = headlines[:5]

    if not headlines:
        logger.info("No new headlines found.")
        return

    message = ""
    new_sent_urls = []

    for idx, headline in enumerate(headlines, 1):
        short_url = shorten_url(headline['source'])
        message += f"*{idx}. {headline['title']}*\nLINK: {short_url}\n\n"
        new_sent_urls.append(headline['source'])

    # Send news to a specific chat ID if provided, otherwise send to all stored chat IDs
    target_chat_ids = [chat_id] if chat_id else chat_ids
    for chat_id in target_chat_ids:
        try:
            bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")

    # Save the new sent URLs to the file
    save_sent_urls(new_sent_urls)

# Command handler to start the bot and save chat IDs
def start(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)
    save_chat_id(chat_id)
    update.message.reply_text("You will now receive tech news updates every 3 hours.")
    send_news_to_telegram(chat_id)  # Send news immediately after starting

# Main function
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))

    updater.start_polling()

    while True:
        try:
            send_news_to_telegram()
            logger.info(f"News sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            time.sleep(10800)  # Sleep for 3 hours (3 hours * 60 minutes * 60 seconds)
        except Exception as e:
            logger.error(f"Unhandled error: {e}", exc_info=True)
            time.sleep(60)  # Sleep for 1 minute before retrying

    updater.idle()

if __name__ == "__main__":
    main()
