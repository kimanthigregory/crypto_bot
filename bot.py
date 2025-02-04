import asyncio
import logging
import os
import aiohttp
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

# Load environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CRYPTO_NEWS_API_KEY = os.getenv("CRYPTO_NEWS_API_KEY")
API_URL = "https://api.coingecko.com/api/v3"

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing in environment variables!")
if not CRYPTO_NEWS_API_KEY:
    raise ValueError("CRYPTO_NEWS_API_KEY is missing in environment variables!")

CRYPTO_NEWS_URL = f"https://cryptopanic.com/api/v1/posts/?auth_token={CRYPTO_NEWS_API_KEY}&filter=trending"

# Configure logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)


async def fetch_crypto_news():
    """Fetch cryptocurrency news from CryptoPanic API."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(CRYPTO_NEWS_URL) as response:
                if response.status == 200:
                    data = await response.json()
                    articles = data.get("results", [])

                    if not articles:
                        return ["No recent news found."]

                    news_list = [f"{article['title']} - {article['url']}" for article in articles[:5]]
                    return news_list
                else:
                    return [f"Error fetching news: {response.status}"]
    except Exception as e:
        logging.error(f"Error fetching news: {e}")
        return ["Error fetching news. Try again later."]


async def crypto_news(update: Update, context: CallbackContext) -> None:
    """Send the latest cryptocurrency news to Telegram."""
    news = await fetch_crypto_news()  # Ensure it is called as an awaitable coroutine
    news_message = "\n\n".join(news)
    await update.message.reply_text(f"Latest Crypto News:\n\n{news_message}")


async def start(update: Update, context: CallbackContext) -> None:
    """Send a welcome message."""
    await update.message.reply_text(
        "Hello! I can provide real-time crypto updates. Use /price <coin> to check prices, or /crypto_news to get the latest crypto news."
    )


async def get_price(update: Update, context: CallbackContext) -> None:
    """Fetch and return the price of a cryptocurrency."""
    if not context.args:
        await update.message.reply_text("Please provide a cryptocurrency symbol. Example: /price bitcoin")
        return

    coin = context.args[0].lower()
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/simple/price?ids={coin}&vs_currencies=usd") as response:
            if response.status == 200:
                data = await response.json()
                if coin in data:
                    price = data[coin]["usd"]
                    await update.message.reply_text(f"The current price of {coin.capitalize()} is ${price}")
                else:
                    await update.message.reply_text("Invalid cryptocurrency name. Try again.")
            else:
                await update.message.reply_text("Error fetching data. Try again later.")


def run_bot():
    """Set up and run the bot in a separate thread with an explicit event loop."""
    asyncio.set_event_loop(asyncio.new_event_loop())  # Create and set a new event loop
    loop = asyncio.get_event_loop()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", get_price))
    app.add_handler(CommandHandler("crypto_news", crypto_news))

    loop.run_until_complete(app.run_polling())


# Flask App
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"


if __name__ == "__main__":
    # Run the bot in a separate thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # Start Flask
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
