import os
import subprocess
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Start Command
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text('Send me a .txt file with master.mpd URLs.')

# Handle TXT File and Convert URLs
async def handle_txt_file(update: Update, context: CallbackContext):
    try:
        file = await update.message.document.get_file()
        file_path = f"{update.message.document.file_id}.txt"

        # Retry logic for file download
        for attempt in range(3):
            try:
                await file.download_to_drive(file_path)
                break
            except Exception as e:
                if attempt == 2:
                    await update.message.reply_text('Failed to download file after several attempts. Please try again later.')
                else:
                    await asyncio.sleep(5)  # Wait before retrying
                    continue

        # Extract and convert master.mpd URLs
        urls = []
        converted_urls = []
        with open(file_path, 'r') as f:
            for line in f:
                if 'master.mpd' in line:
                    url = line.strip()
                    urls.append(url)

                    # Extract the unique ID from the original URL
                    video_id = url.split('/')[-2]
                    
                    # Convert to the new URL format
                    new_url = f'https://jarvis-stream.pages.dev/{video_id}/hls/240/main.m3u8'
                    ffmpeg_command = f'ffmpeg -i "{new_url}" -c copy output.mp4'
                    converted_urls.append(ffmpeg_command)

        if urls:
            await update.message.reply_text(f"Found {len(urls)} master.mpd URLs.")
            await update.message.reply_text(f"Successfully converted {len(converted_urls)} URLs.")

            # Save converted URLs in user_data for future use
            context.user_data['converted_urls'] = converted_urls
            await update.message.reply_text("Please enter the range of URLs you want to download (e.g., 1-4).")
        else:
            await update.message.reply_text("No master.mpd URLs found in the file.")

    except Exception as e:
        await update.message.reply_text(f"An error occurred while processing the file: {e}")

# Handle Range Input and Download Videos
async def handle_range_input(update: Update, context: CallbackContext):
    try:
        range_input = update.message.text.split('-')
        start, end = int(range_input[0]), int(range_input[1])
        converted_urls = context.user_data.get('converted_urls', [])
        
        if not converted_urls:
            await update.message.reply_text("No URLs to process.")
            return
        
        # Retry logic for ffmpeg command execution
        for i in range(start - 1, end):
            command = converted_urls[i]
            await update.message.reply_text(f"Downloading video from URL {i+1}...")

            temp_video_path = f"output_{i+1}.mp4"

            for attempt in range(3):
                try:
                    process = await asyncio.create_subprocess_shell(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    stdout, stderr = await process.communicate()

                    if process.returncode == 0:
                        await update.message.reply_text(f"URL {i+1} downloaded successfully.")
                        
                        # Send the video back to user
                        with open(temp_video_path, 'rb') as video:
                            await update.message.reply_video(video)
                        break
                    else:
                        if attempt == 2:
                            await update.message.reply_text(f"Error downloading URL {i+1}: {stderr.decode()}. Please try again later.")
                        else:
                            await asyncio.sleep(5)  # Wait before retrying
                            continue
                except Exception as e:
                    if attempt == 2:
                        await update.message.reply_text(f"Error executing ffmpeg command for URL {i+1}: {e}. Please try again later.")
                    else:
                        await asyncio.sleep(5)  # Wait before retrying
                        continue
            
            # Remove the temporary video file after sending
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)

    except Exception as e:
        await update.message.reply_text(f"Invalid input or an error occurred: {e}")

# Main Bot
def main():
    # Create application instead of Updater
    application = Application.builder().token("7497967505:AAHUTJt31Znc1pKXUmoRKMpF4QgmATGpUlU").build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.MimeType("text/plain"), handle_txt_file))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_range_input))

    # Start the bot
    loop = asyncio.get_event_loop()
    loop.run_until_complete(application.run_polling())

if __name__ == '__main__':
    main()
