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

# --- সেটিংস (আপনার তথ্যগুলো দিন) ---
BOT_TOKEN = "8624201473:AAGCtrK4FjtIUCco0ngPrKVK_x4Bt5vSguc"  
BOT_USERNAME = "Prince_telecom_chatbot" 
ADMIN_IDS = [5533760143] 
SHEET_NAME = "Support_Bot_DB"
JSON_KEY_FILE = "service_account.json"

# লগিং সেটআপ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# গুগল শিট কানেক্ট করার ফাংশন
def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    with open(JSON_KEY_FILE, 'r') as f:
        key_data = json.load(f)
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

# মেনু তৈরির ফাংশন
def make_menu(parent_id, all_data):
    keyboard = []
    filtered = [row for row in all_data if str(row.get('Parent_ID')) == str(parent_id)]
    for row in filtered:
        keyboard.append([InlineKeyboardButton(str(row.get('Button_Text')), callback_data=str(row.get('ID')))])
    return InlineKeyboardMarkup(keyboard)

# কমান্ড হ্যান্ডলার
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_data = get_fresh_data()
    await update.message.reply_text("স্বাগতম!", reply_markup=make_menu(0, all_data))

# Render-এর পোর্ট এরর দূর করার ডামি সার্ভার
def run_dummy_server():
    PORT = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        logging.info(f"Dummy server running on port {PORT}")
        httpd.serve_forever()

async def main():
    # ডামি সার্ভার চালু করা (ব্যাকগ্রাউন্ডে)
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    # অ্যাপ্লিকেশন তৈরি
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    
    # নতুন নিয়মে পোলিং চালু করা (Event Loop এরর এড়াতে)
    async with application:
        await application.initialize()
        await application.start()
        print("বট সফলভাবে চালু হয়েছে...")
        await application.updater.start_polling()
        # বটকে চালু রাখতে ইনফিনিট লুপ
        while True:
            await asyncio.sleep(1)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
