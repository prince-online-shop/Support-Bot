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

# --- আপনার সেটিংস (এগুলো অবশ্যই চেক করে নিন) ---
BOT_TOKEN = "8624201473:AAGCtrK4FjtIUCco0ngPrKVK_x4Bt5vSguc"  # BotFather থেকে পাওয়া টোকেন দিন
BOT_USERNAME = "Prince_telecom_chatbot"  # @ ছাড়া বটের ইউজারনেম দিন
ADMIN_IDS = [5533760143]  # আপনার টেলিগ্রাম আইডি দিন
SHEET_NAME = "Support_Bot_DB" # আপনার গুগল শিটের সঠিক নাম
JSON_KEY_FILE = "service_account.json"

# লগিং সেটআপ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# গুগল শিট কানেক্ট করার চূড়ান্ত নিরাপদ ফাংশন
def get_gsheet_client():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # সরাসরি ফাইল থেকে লোড করা সিগনেচার এরর দূর করতে সবথেকে কার্যকর
        creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_KEY_FILE, scope)
        return gspread.authorize(creds)
    except Exception as e:
        logging.error(f"Google Connection Error: {e}")
        return None

# ডাটা রিফ্রেশ করার ফাংশন
def get_fresh_data():
    client = get_gsheet_client()
    if client:
        try:
            sheet = client.open(SHEET_NAME).sheet1
            return sheet.get_all_records()
        except Exception as e:
            logging.error(f"Sheet Data Error: {e}")
    return []

# মেনু তৈরির ফাংশন
def make_menu(parent_id, all_data):
    keyboard = []
    filtered = [row for row in all_data if str(row.get('Parent_ID')) == str(parent_id)]
    for row in filtered:
        btn_text = str(row.get('Button_Text', 'বাটন'))
        callback_id = str(row.get('ID', ''))
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback_id)])
    return InlineKeyboardMarkup(keyboard)

# /start কমান্ড
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_data = get_fresh_data()
    if not all_data:
        await update.message.reply_text("দুঃখিত, গুগল শিটের সাথে কানেক্ট করা যাচ্ছে না। দয়া করে শেয়ার সেটিংস চেক করুন।")
        return
    reply_markup = make_menu(0, all_data)
    await update.message.reply_text("স্বাগতম! একটি অপশন বেছে নিন:", reply_markup=reply_markup)

# Render-এর পোর্ট টাইমআউট এরর দূর করার ডামি সার্ভার
def run_dummy_server():
    PORT = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        logging.info(f"Dummy server running on port {PORT}")
        httpd.serve_forever()

# মেইন ফাংশন (Event Loop এরর সমাধান করবে)
async def main():
    # ডামি সার্ভার ব্যাকগ্রাউন্ডে চালু করা
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
    except (KeyboardInterrupt, SystemExit):
        pass
