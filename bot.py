import os
import tempfile
import subprocess
from threading import Thread
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pydub import AudioSegment
from config import *

# Initialize Pyrogram Client
app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=API_TOKEN)

# Flask app for health check
health_app = Flask(__name__)

@health_app.route('/')
def health_check():
    return "Bot is running", 200

# Start Flask server on a separate thread for health checks
def run_health_server():
    health_app.run(host="0.0.0.0", port=8000)

# Start the health server thread
health_thread = Thread(target=run_health_server)
health_thread.start()

# Start command handler
@app.on_message(filters.command("start"))
def start(client, message):
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Compress Audio 🎧", callback_data="compress_audio"),
         InlineKeyboardButton("Compress Video 🎥", callback_data="compress_video")]
    ])
    message.reply_text("Choose what you want to compress:", reply_markup=markup)

# Callback query handler
@app.on_callback_query()
def callback(client, callback_query: CallbackQuery):
    callback_query.message.reply_text("Send me a file.")

# Audio compression handler
@app.on_message(filters.voice | filters.audio)
def handle_audio(client, message):
    file = client.download_media(message.voice.file_id if message.voice else message.audio.file_id)
    audio = AudioSegment.from_file(file).set_channels(AUDIO_CHANNELS).set_frame_rate(AUDIO_SAMPLE_RATE)
    with tempfile.NamedTemporaryFile(suffix=TEMP_FILE_SUFFIX_AUDIO, delete=False) as temp_file:
        temp_filename = temp_file.name
        audio.export(temp_filename, format=AUDIO_FORMAT, bitrate=AUDIO_BITRATE)
    message.reply_document(temp_filename)
    os.remove(file)
    os.remove(temp_filename)

# Video/Animation compression handler
@app.on_message(filters.video | filters.animation)
def handle_media(client, message):
    file = client.download_media(message.video.file_id if message.video else message.animation.file_id)
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as temp_file:
        temp_filename = temp_file.name
    # Run FFmpeg command
    subprocess.run(
        f'ffmpeg -i "{file}" -filter_complex "scale={VIDEO_SCALE}" -r {VIDEO_FPS} -c:v {VIDEO_CODEC} '
        f'-pix_fmt {VIDEO_PIXEL_FORMAT} -b:v {VIDEO_BITRATE} -crf {VIDEO_CRF} -preset {VIDEO_PRESET} '
        f'-c:a {VIDEO_AUDIO_CODEC} -b:a {VIDEO_AUDIO_BITRATE} -ac {VIDEO_AUDIO_CHANNELS} '
        f'-ar {VIDEO_AUDIO_SAMPLE_RATE} -profile:v {VIDEO_PROFILE} -map_metadata -1 "{temp_filename}"',
        shell=True, check=True
    )
    message.reply_video(temp_filename)
    os.remove(file)
    os.remove(temp_filename)

# Run the bot
app.run()
