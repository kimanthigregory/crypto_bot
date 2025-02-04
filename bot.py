import logging
import os
import aiohttp
import asyncio
from quart import Quart
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

# Create a Quart app
app = Quart(__name__)

# Create a Telegram bot application
bot_app = Application.builder().token(TOKEN).build()

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
    await update.message.reply_text("Hello! I can provide real-time crypto updates. Use /price <coin> to check prices, or /crypto_news to get the latest crypto news.")

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

# Set up a function to run the bot and Quart app together
async def run_bot():
    """Run the bot and the Quart web server."""
    # Start the bot polling in the background
    await bot_app.initialize()
    bot_task = asyncio.create_task(bot_app.run_polling())

    # Start the Quart app in the same event loop
    await app.run_task()

    # Wait for both tasks to finish
    await bot_task

@app.before_serving
async def startup():
    """Start both the bot and the web server."""
    # Use asyncio.create_task to start the bot in the background
    asyncio.create_task(run_bot())

@app.route("/")
async def home():
    return "Bot is running!"

if __name__ == "__main__":
    # Run Quart app and bot in the same event loop
    asyncio.run(run_bot())
