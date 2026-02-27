import logging
import asyncio
import gspread
import json
import os
import http.server
import socketserver
import threading
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- সেটিংস (আপনার তথ্যগুলো এখানে দিন) ---
BOT_TOKEN = "8624201473:AAGCtrK4FjtIUCco0ngPrKVK_x4Bt5vSguc"  # BotFather থেকে পাওয়া টোকেন দিন
BOT_USERNAME = "Prince_telecom_chatbot"  # @ ছাড়া বটের ইউজারনেম দিন
ADMIN_IDS = [5533760143]  # আপনার আইডি দিন
SHEET_NAME = "Support_Bot_DB"
JSON_KEY_FILE = "service_account.json"

# লগিং সেটআপ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# গুগল শিট কানেক্ট করার জন্য সবথেকে শক্তিশালী ফাংশন
def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # এটি ফাইলের ভেতরের সব তথ্য হুবহু পড়বে কোনো পরিবর্তন ছাড়াই
    with open(JSON_KEY_FILE, 'r') as f:
        key_data = json.load(f)
    
    # অনেক সময় পাইথন \n ঠিকমতো চেনে না, তাই এটি ম্যানুয়ালি ঠিক করে দিবে
    if 'private_key' in key_data:
        key_data['private_key'] = key_data['private_key'].replace('\\n', '\n')
    
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_data, scope)
    return gspread.authorize(creds)

# শিট থেকে ডাটা আনা
def get_fresh_data():
    try:
        client = get_gsheet_client()
        sheet = client.open(SHEET_NAME).sheet1
        return sheet.get_all_records()
    except Exception as e:
        logging.error(f"Sheet Access Error: {e}")
        return []

# বাটন তৈরির ফাংশন
def make_menu(parent_id, all_data):
    keyboard = []
    filtered = [row for row in all_data if str(row.get('Parent_ID')) == str(parent_id)]
    for row in filtered:
        keyboard.append([InlineKeyboardButton(str(row.get('Button_Text')), callback_data=str(row.get('ID')))])
    return InlineKeyboardMarkup(keyboard)

# /start কমান্ড
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_data = get_fresh_data()
    if not all_data:
        await update.message.reply_text("সিস্টেম আপডেট হচ্ছে, দয়া করে একটু পর চেষ্টা করুন।")
        return
    await update.message.reply_text("স্বাগতম! একটি অপশন বেছে নিন:", reply_markup=make_menu(0, all_data))

# Render-এর পোর্ট সমস্যা সমাধানের জন্য ডামি সার্ভার
def run_dummy_server():
    PORT = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        httpd.serve_forever()

# মেইন ফাংশন যা এরর হতে দিবে না
async def main():
    # ডামি সার্ভার চালু
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    
    async with application:
        await application.initialize()
        await application.start()
        print("বট সফলভাবে চালু হয়েছে...")
        await application.updater.start_polling()
        while True:
            await asyncio.sleep(1)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
