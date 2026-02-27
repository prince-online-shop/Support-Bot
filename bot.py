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

# লগিং সেটআপ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# গুগল শিট কানেক্ট করার জন্য Environment Variable পদ্ধতি
def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # এটি সরাসরি রেন্ডারের Environment Variable থেকে ডাটা নিবে
    creds_json = os.environ.get("GOOGLE_CREDS")
    
    if not creds_json:
        logging.error("GOOGLE_CREDS পাওয়া যায়নি! দয়া করে Render Environment-এ এটি সেট করুন।")
        return None
        
    try:
        # JSON টেক্সটকে ডিকশনারিতে রূপান্তর
        info = json.loads(creds_json)
        
        # Private Key-এর ফরম্যাট ঠিক করা
        if 'private_key' in info:
            info['private_key'] = info['private_key'].replace('\\n', '\n')
            
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
        return gspread.authorize(creds)
    except Exception as e:
        logging.error(f"Credentials Error: {e}")
        return None

# শিট থেকে ডাটা আনা
def get_fresh_data():
    client = get_gsheet_client()
    if client:
        try:
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
        btn_text = str(row.get('Button_Text', 'বাটন'))
        callback_id = str(row.get('ID', ''))
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback_id)])
    return InlineKeyboardMarkup(keyboard)

# /start কমান্ড
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_data = get_fresh_data()
    if not all_data:
        await update.message.reply_text("দুঃখিত, তথ্য লোড করা যাচ্ছে না। দয়া করে এডমিনকে জানান।")
        return
    await update.message.reply_text("স্বাগতম! একটি অপশন বেছে নিন:", reply_markup=make_menu(0, all_data))

# Render-এর পোর্ট সমস্যা সমাধানের জন্য ডামি সার্ভার
def run_dummy_server():
    PORT = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        logging.info(f"Dummy server running on port {PORT}")
        httpd.serve_forever()

# মেইন ফাংশন
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
    except (KeyboardInterrupt, SystemExit):
        pass
