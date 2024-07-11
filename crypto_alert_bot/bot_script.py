import os
import logging
import asyncio
import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import datetime, timedelta
from database import add_token, get_user_tokens, update_token_check, remove_token, get_user_token_count

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the bot token from environment variable
TOKEN = os.environ.get('7287078061:AAEysp3ggXl5_1rSWXG4d-TOKy5-evQYNc0')

# DEX Screener API endpoint
DEX_SCREENER_API = "https://api.dexscreener.com/latest/dex/tokens/"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Welcome to CryptoAlertBot! Use /add <token_address> to add a token for tracking.')

async def add_token_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 1:
        await update.message.reply_text('Please provide a token address. Usage: /add <token_address>')
        return

    token_address = context.args[0]
    user_id = update.effective_user.id

    if get_user_token_count(user_id) >= 10:  # Limit to 10 tokens
        await update.message.reply_text('You have reached the maximum limit of 10 tokens.')
        return

    add_token(user_id, token_address)
    await update.message.reply_text(f'Token {token_address} added successfully!')

async def list_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    tokens = get_user_tokens(user_id)
    if tokens:
        message = "Your tracked tokens:\n"
        for token, last_check in tokens:
            message += f"{token} (Last checked: {last_check})\n"
    else:
        message = "You are not tracking any tokens."
    await update.message.reply_text(message)

async def remove_token_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 1:
        await update.message.reply_text('Please provide a token address. Usage: /remove <token_address>')
        return

    token_address = context.args[0]
    user_id = update.effective_user.id

    remove_token(user_id, token_address)
    await update.message.reply_text(f'Token {token_address} removed successfully!')

async def get_token_price(token_address: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{DEX_SCREENER_API}{token_address}") as response:
            if response.status == 200:
                data = await response.json()
                if data['pairs']:
                    pair = data['pairs'][0]  # Get the first pair (usually the most liquid)
                    return {
                        'price': float(pair['priceUsd']),
                        'change_24h': float(pair['priceChange']['h24']),
                        'change_1h': float(pair['priceChange']['h1']),
                        'symbol': pair['baseToken']['symbol'],
                        'name': pair['baseToken']['name']
                    }
    return None

async def check_prices(context: ContextTypes.DEFAULT_TYPE) -> None:
    for user_id, tokens in get_user_tokens():
        for token_address, last_check in tokens:
            if datetime.now() - last_check >= timedelta(minutes=15):
                price_data = await get_token_price(token_address)
                if price_data:
                    message = (
                        f"{price_data['name']} ({price_data['symbol']}) Price: ${price_data['price']:.4f}\n"
                        f"Change: 24h: {price_data['change_24h']:+.2f}% | "
                        f"1h: {price_data['change_1h']:+.2f}%"
                    )
                    await context.bot.send_message(chat_id=user_id, text=message)

                    # Check for significant price changes (e.g., > 10% in 1 hour)
                    if abs(price_data['change_1h']) > 10:
                        alert_message = f"🚨 Alert! {price_data['name']} ({price_data['symbol']}) price changed by {price_data['change_1h']:+.2f}% in the last hour!"
                        await context.bot.send_message(chat_id=user_id, text=alert_message)

                    update_token_check(user_id, token_address, price_data['price'])
                else:
                    await context.bot.send_message(chat_id=user_id, text=f"Unable to fetch data for token {token_address}")

async def continuous_price_check(application: Application) -> None:
    while True:
        await check_prices(application)
        await asyncio.sleep(60)  # Check every minute

def main() -> None:
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_token_command))
    application.add_handler(CommandHandler("list", list_tokens))
    application.add_handler(CommandHandler("remove", remove_token_command))

    # Start the continuous price checking in the background
    application.loop.create_task(continuous_price_check(application))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
