import requests
import json
import time
import pyshorteners
import os
from datetime import datetime
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# Google News API key
API_KEY = "8724843704da412698fa529a6aa777bc"

# Telegram bot token
BOT_TOKEN = "7461272183:AAFH-_dJYbcHwLGJ5HJiPcnNDGDcua4ucKw"

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

# Function to fetch news headlines from Google News API for a given topic
def fetch_news(topic):
    url = f"https://newsapi.org/v2/everything?q={topic}&apiKey={API_KEY}"
    response = requests.get(url)
    data = response.json()
    articles = data.get('articles', [])
    headlines = []
    for article in articles:
        title = article.get('title', 'N/A')
        source = article.get('url', 'N/A')
        headlines.append({'title': title, 'source': source})
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
        print("No chat IDs found.")
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
        print("No new headlines found.")
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
            print(f"Failed to send message to {chat_id}: {e}")

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
            print(f"News sent at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            time.sleep(10800)  # Sleep for 3 hours (3 hours * 60 minutes * 60 seconds)
        except Exception as e:
            print(f"Error: {e}")
            continue

    updater.idle()

if __name__ == "__main__":
    main()
