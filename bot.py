import logging
import os
import aiohttp
from quart import Quart
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
import asyncio

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


async def run_bot():
    """Set up and run the bot."""
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", get_price))
    app.add_handler(CommandHandler("crypto_news", crypto_news))

    await app.run_polling()


# Initialize Quart app
quart_app = Quart(__name__)

@quart_app.route("/")
async def home():
    return "Bot is running!"


# Start the bot and Quart app in the same event loop
async def start_app():
    # Run the Telegram bot in the background
    asyncio.create_task(run_bot())
    
    # Run Quart app
    await quart_app.run_task(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))


if __name__ == "__main__":
    # Create the event loop and run the app
    asyncio.run(start_app())
