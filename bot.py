import os
import subprocess
import requests
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, CallbackContext, filters
from time import time
from pytube import YouTube
from instaloader import Instaloader, Post

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Your bot token from Telegram
BOT_TOKEN = '7339145055:AAE7Olonw5aTAGsc3LxfCUyNVJbSTkaYPpM'

# Function to download a video with progress display
async def download_video_with_progress(url, filename, update, context):
    try:
        response = requests.get(url, stream=True)
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024  # 1 Kilobyte
        
        progress_message = None
        start_time = time()
        downloaded_size = 0
        progress_bar_length = 20  # Length of the progress bar
        
        with open(filename, 'wb') as file:
            for data in response.iter_content(block_size):
                downloaded_size += len(data)
                file.write(data)
                
                # Calculate progress
                percent_complete = downloaded_size / total_size if total_size > 0 else 0
                num_blocks = int(progress_bar_length * percent_complete)
                progress_bar = '█' * num_blocks + '░' * (progress_bar_length - num_blocks)
                elapsed_time = time() - start_time
                
                # Send progress update every 1MB
                if downloaded_size % (1024 * 1024) == 0 or downloaded_size == total_size:
                    # Human-readable file size
                    downloaded_mb = downloaded_size / (1024 * 1024)
                    total_mb = total_size / (1024 * 1024)
                    progress_text = (
                        f"📥 Downloading: {downloaded_mb:.2f}MB/{total_mb:.2f}MB\n"
                        f"[{progress_bar}] {percent_complete * 100:.2f}%\n"
                        f"⏳ Time elapsed: {elapsed_time:.2f}s"
                    )
                    
                    # Edit message with progress if it already exists, else send a new message
                    if progress_message:
                        await context.bot.edit_message_text(
                            chat_id=update.effective_chat.id,
                            message_id=progress_message.message_id,
                            text=progress_text
                        )
                    else:
                        progress_message = await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=progress_text
                        )
        
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            logger.info(f"Download completed successfully: {filename}")
            return filename
        else:
            logger.error(f"Download failed: {filename} not found or empty")
            return None
    except Exception as e:
        logger.error(f"Error downloading file: {e}", exc_info=True)
        return None

# Function to convert video to MP4
async def convert_to_mp4(input_file, output_file, update, context):
    try:
        if not os.path.exists(input_file):
            logger.error(f"Input file not found: {input_file}")
            return None

        command = ['ffmpeg', '-i', input_file, '-codec', 'copy', output_file]
        logger.info(f"Starting conversion: {input_file} -> {output_file}")
        logger.info(f"Command: {' '.join(command)}")

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"FFmpeg error: {stderr.decode()}")
            return None

        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            logger.info(f"Conversion completed successfully: {output_file}")
            return output_file
        else:
            logger.error(f"Conversion failed: {output_file} not found or empty")
            return None
    except Exception as e:
        logger.error(f"Error converting file: {e}", exc_info=True)
        return None

# Function to download YouTube videos
async def download_youtube(url, update, context):
    try:
        yt = YouTube(url)
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Downloading: {yt.title}")
        
        filename = f"{yt.title}_{int(time())}.mp4"
        stream.download(filename=filename)
        
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            logger.info(f"YouTube download completed: {filename}")
            return filename
        else:
            logger.error(f"YouTube download failed: {filename} not found or empty")
            return None
    except Exception as e:
        logger.error(f"YouTube download error: {str(e)}", exc_info=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error downloading YouTube video. Please try again or use a different link.")
        return None

# Function to download Instagram Reels
async def download_instagram_reel(url, update, context):
    try:
        L = Instaloader()
        post = Post.from_shortcode(L.context, url.split("/")[-2])
        
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Downloading Instagram Reel")
        
        filename = f"{post.owner_username}_{post.shortcode}_{int(time())}.mp4"
        L.download_post(post, target=filename)
        
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            logger.info(f"Instagram Reel download completed: {filename}")
            return filename
        else:
            logger.error(f"Instagram Reel download failed: {filename} not found or empty")
            return None
    except Exception as e:
        logger.error(f"Instagram download error: {str(e)}", exc_info=True)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error downloading Instagram Reel. Please try again or use a different link.")
        return None

# Function to create the main menu keyboard
def get_main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("YouTube", callback_data='youtube'),
         InlineKeyboardButton("Instagram Reel", callback_data='instagram')],
        [InlineKeyboardButton("Direct Link", callback_data='direct')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Command to start the bot
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Welcome to the Video Downloader Bot! What would you like to download?",
        reply_markup=get_main_menu_keyboard()
    )

# Function to handle button callbacks
async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel':
        context.user_data.pop('download_type', None)
        await query.edit_message_text("Operation cancelled. What would you like to do next?", reply_markup=get_main_menu_keyboard())
        return

    if query.data in ['youtube', 'instagram', 'direct']:
        context.user_data['download_type'] = query.data
        keyboard = [[InlineKeyboardButton("Cancel", callback_data='cancel')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Please send the {query.data} link(s) you want to download. You can send multiple links, one per line. Or use /cancel to go back to the main menu.", reply_markup=reply_markup)
        return

# Function to handle incoming messages (links)
async def handle_message(update: Update, context: CallbackContext):
    if 'download_type' not in context.user_data:
        await update.message.reply_text("Please select a download type from the main menu.", reply_markup=get_main_menu_keyboard())
        return

    download_type = context.user_data['download_type']
    urls = update.message.text.split('\n')

    for url in urls:
        url = url.strip()
        if not url:
            continue

        try:
            if download_type == 'youtube':
                filename = await download_youtube(url, update, context)
            elif download_type == 'instagram':
                filename = await download_instagram_reel(url, update, context)
            else:  # direct link
                filename = f"downloaded_video_{int(time())}.mp4"
                await update.message.reply_text(f"🚀 Starting download from the provided link: {url}")
                filename = await download_video_with_progress(url, filename, update, context)

            if filename:
                if filename.endswith('.mkv'):
                    await update.message.reply_text("✅ Download complete, converting the file to MP4...")
                    mp4_filename = f"converted_video_{int(time())}.mp4"
                    converted_file = await convert_to_mp4(filename, mp4_filename, update, context)
                    
                    if converted_file:
                        await update.message.reply_text("✅ Conversion complete, sending the file...")
                        await context.bot.send_document(chat_id=update.effective_chat.id, document=open(converted_file, 'rb'))
                        os.remove(filename)
                        os.remove(converted_file)
                    else:
                        await update.message.reply_text("❌ Conversion failed. Sending the original file...")
                        await context.bot.send_document(chat_id=update.effective_chat.id, document=open(filename, 'rb'))
                        os.remove(filename)
                else:
                    await update.message.reply_text("✅ Download complete, sending the file...")
                    await context.bot.send_document(chat_id=update.effective_chat.id, document=open(filename, 'rb'))
                    os.remove(filename)
            else:
                await update.message.reply_text(f"❌ Download failed for {url}. Please try again.")
        except Exception as e:
            logger.error(f"Error processing {url}: {str(e)}", exc_info=True)
            await update.message.reply_text(f"An error occurred while processing {url}. Please try again later.")

    await update.message.reply_text("All downloads completed. What would you like to do next?", reply_markup=get_main_menu_keyboard())

# Main function to run the bot
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot is starting...")
    application.run_polling()

if __name__ == "__main__":
    main()
