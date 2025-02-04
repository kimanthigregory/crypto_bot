import logging
import os
import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from quart import Quart, request, jsonify

# Load environment variables
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CRYPTO_NEWS_API_KEY = os.environ.get("CRYPTO_NEWS_API_KEY")
API_URL = "https://api.coingecko.com/api/v3"
PORT = int(os.environ.get("PORT", 5000))  # Render uses port 5000

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing in environment variables!")
if not CRYPTO_NEWS_API_KEY:
    raise ValueError("CRYPTO_NEWS_API_KEY is missing in environment variables!")

CRYPTO_NEWS_URL = f"https://cryptopanic.com/api/v1/posts/?auth_token={CRYPTO_NEWS_API_KEY}&filter=trending"

# Configure logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# Initialize Quart app
app = Quart(__name__)

# Initialize the Telegram bot
bot_app = Application.builder().token(TOKEN).build()

# Command handler functions

async def start(update: Update, context: CallbackContext):
    """Start command handler."""
    await update.message.reply("Hello! I'm your Crypto Bot! Use /price to get the current price of a coin, or /crypto_news for the latest crypto news.")

async def get_price(update: Update, context: CallbackContext):
    """Get the price of a cryptocurrency."""
    if len(context.args) == 0:
        await update.message.reply("Please specify a cryptocurrency (e.g., /price bitcoin).")
        return

    coin = context.args[0].lower()
    url = f"{API_URL}/simple/price?ids={coin}&vs_currencies=usd"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            if coin in data:
                price = data[coin]["usd"]
                await update.message.reply(f"The current price of {coin.capitalize()} is ${price}.")
            else:
                await update.message.reply(f"Sorry, I couldn't find the price for {coin.capitalize()}.")

async def crypto_news(update: Update, context: CallbackContext):
    """Get the latest cryptocurrency news."""
    async with aiohttp.ClientSession() as session:
        async with session.get(CRYPTO_NEWS_URL) as response:
            data = await response.json()
            posts = data.get("results", [])
            if not posts:
                await update.message.reply("Sorry, I couldn't fetch any cryptocurrency news at the moment.")
                return

            news_message = "Here are the latest crypto news:\n"
            for post in posts[:5]:  # Limit to top 5 news
                title = post.get("title", "No title")
                url = post.get("url", "#")
                news_message += f"- {title} ({url})\n"
            
            await update.message.reply(news_message)


async def process_telegram_update(update_data):
    """Process incoming Telegram update."""
    try:
        update = Update.de_json(update_data, bot=bot_app.bot)  # Use bot_app.bot
        logging.info(f"Received update: {update}")  # Log the update
        await bot_app.process_update(update)  # Process the update
        return jsonify({"status": "ok"})
    except Exception as e:
        logging.error(f"Error processing update: {e}")
        return jsonify({"status": "error"})


@app.route("/", methods=["POST"])
async def webhook():
    """Handle incoming webhook requests from Telegram."""
    update_data = await request.get_json()
    return await process_telegram_update(update_data)


@app.route("/set_webhook", methods=["GET"])
async def set_webhook():
    """Set the webhook URL for the Telegram bot."""
    webhook_url = f"https://{request.host}/"  # Construct webhook URL dynamically using request.host
    try:
        await bot_app.bot.set_webhook(webhook_url)  # Use bot_app.bot and await
        return jsonify({"status": "webhook set"})
    except Exception as e:
        logging.error(f"Error setting webhook: {e}")
        return jsonify({"status": "error setting webhook"})


def main():
    """Set up the bot and Flask app."""
    # Add command handlers to the Telegram bot
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("price", get_price))
    bot_app.add_handler(CommandHandler("crypto_news", crypto_news))

    # Run the Quart app (async support)
    app.run(host="0.0.0.0", port=PORT)  # Use host 0.0.0.0 for Render


if __name__ == "__main__":
    main()
