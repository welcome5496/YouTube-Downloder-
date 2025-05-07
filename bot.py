import os
import asyncio
import logging
import yt_dlp
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

logging.basicConfig(level=logging.INFO)

# Search YouTube
def search_youtube(query):
    url = f"https://www.googleapis.com/youtube/v3/search"
    params = {
        'part': 'snippet',
        'q': query,
        'key': YOUTUBE_API_KEY,
        'maxResults': 5,
        'type': 'video'
    }
    res = requests.get(url, params=params).json()
    return res.get("items", [])

# Handle /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a song name or YouTube link!")

# Handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()

    if "youtube.com" in query or "youtu.be" in query:
        await download_and_send_audio(update, query)
    else:
        results = search_youtube(query)
        if not results:
            await update.message.reply_text("No results found.")
            return

        keyboard = []
        for i, item in enumerate(results):
            title = item["snippet"]["title"]
            video_id = item["id"]["videoId"]
            url = f"https://www.youtube.com/watch?v={video_id}"
            keyboard.append([InlineKeyboardButton(f"{title}", callback_data=url)])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Choose a video:", reply_markup=reply_markup)

# Handle button press
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    video_url = query.data
    await query.edit_message_text("Downloading...")
    await download_and_send_audio(update, video_url)

# Download and send audio
async def download_and_send_audio(update, video_url):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            file_path = ydl.prepare_filename(info).replace(info['ext'], 'mp3')

        chat_id = update.effective_message.chat_id
        await update.effective_message.reply_audio(audio=open(file_path, 'rb'), title=info.get('title'))

        os.remove(file_path)  # optional: clean up
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Error: {e}")

# Main app
async def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
  
