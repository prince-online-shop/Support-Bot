import logging
import asyncio
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- সেটিংস (আপনার তথ্যগুলো এখানে দিন) ---
BOT_TOKEN = "8624201473:AAGCtrK4FjtIUCco0ngPrKVK_x4Bt5vSguc"  # BotFather থেকে পাওয়া টোকেন দিন
BOT_USERNAME = "Prince_telecom_chatbot"  # @ ছাড়া আপনার বটের ইউজারনেম দিন
ADMIN_IDS = [5533760143]  # আপনার টেলিগ্রাম আইডি দিন (একাধিক হলে কমা দিয়ে লিখুন)
SHEET_NAME = "Support_Bot_DB"  # আপনার গুগল শিটের সঠিক নাম
JSON_KEY_FILE = "service_account.json" # গিটহাবে আপলোড করা ফাইলের নাম

# লগিং সেটআপ (এরর ট্র্যাক করার জন্য)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# গুগল শিট কানেক্ট করার জন্য আপডেট করা ফাংশন
def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # JSON ফাইল থেকে ডাটা পড়ে মেমোরিতে রাখা
    with open(JSON_KEY_FILE, 'r') as f:
        key_data = json.load(f)
    
    # JWT Signature Error এড়াতে Private Key ফরম্যাট ঠিক করা
    if 'private_key' in key_data:
        key_data['private_key'] = key_data['private_key'].replace('\\n', '\n')
    
    # ডিকশনারি থেকে ক্রেডেনশিয়াল তৈরি
    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_data, scope)
    return gspread.authorize(creds)

# একটিভ সাপোর্ট সেশন এবং এডমিন রিপ্লাই ম্যাপিং
active_support = {} 
admin_reply_map = {} 

# গুগল শিট থেকে ডাটা রিফ্রেশ করার ফাংশন
def get_fresh_data():
    try:
        client = get_gsheet_client()
        sheet = client.open(SHEET_NAME).sheet1
        return sheet.get_all_records()
    except Exception as e:
        logging.error(f"Google Sheet Access Error: {e}")
        return []

# ডাইনামিক মেনু বাটন তৈরির ফাংশন
def make_menu(parent_id, all_data):
    keyboard = []
    # Parent_ID এর সাথে মিল রেখে বাটন ফিল্টার
    filtered = [row for row in all_data if str(row.get('Parent_ID')) == str(parent_id)]
    
    for row in filtered:
        btn_text = str(row.get('Button_Text', 'বাটন'))
        callback_id = str(row.get('ID', ''))
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback_id)])
    
    return InlineKeyboardMarkup(keyboard)

# /start কমান্ড হ্যান্ডলার
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_type = update.effective_chat.type
    all_data = get_fresh_data()

    # গ্রুপে মেসেজ দিলে সরাসরি ইনবক্সে পাঠানোর বাটন
    if chat_type in ["group", "supergroup"]:
        keyboard = [[InlineKeyboardButton("🟢 লাইভ সাপোর্ট শুরু করুন", url=f"https://t.me/{BOT_USERNAME}?start=support")]]
        await update.message.reply_text("সরাসরি কথা বলতে নিচের বাটনে চাপ দিয়ে আমার ইনবক্সে আসুন:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # প্রাইভেট চ্যাটে মেইন মেনু দেখানো
    reply_markup = make_menu(0, all_data)
    await update.message.reply_text("স্বাগতম! নিচের অপশনগুলো থেকে আপনার প্রয়োজনীয় সেবাটি বেছে নিন:", reply_markup=reply_markup)

# ইনলাইন বাটন ক্লিক হ্যান্ডলার
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    selected_id = query.data
    all_data = get_fresh_data()
    
    # শিট থেকে সঠিক রো খুঁজে বের করা
    row = next((r for r in all_data if str(r.get('ID')) == selected_id), None)
    if not row: return

    res_type = str(row.get('Type', '')).lower()
    res_text = str(row.get('Reply_Text', 'দুঃখিত, কোনো তথ্য পাওয়া যায়নি।'))

    if res_type == "menu":
        # সাব-মেনু দেখানো
        await query.edit_message_text(text=res_text, reply_markup=make_menu(selected_id, all_data))
    
    elif res_type == "support":
        # লাইভ সাপোর্ট মোড অন করা
        active_support[user_id] = True
        await context.bot.send_message(chat_id=user_id, text=res_text)
    
    else:
        # সাধারণ ইনফরমেশন টেক্সট
        await context.bot.send_message(chat_id=user_id, text=res_text)

# লাইভ মেসেজিং হ্যান্ডলার (ইউজার এবং এডমিন উভয় পক্ষের জন্য)
async def handle_support_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg_text = update.message.text
    
    # ইউজার যখন সাপোর্টে মেসেজ দেয় (এডমিনের কাছে যাবে)
    if update.effective_chat.type == "private" and user.id in active_support:
        for admin_id in ADMIN_IDS:
            m = await context.bot.send_message(
                chat_id=admin_id,
                text=f"📩 নতুন মেসেজ\nইউজার: {user.full_name} ({user.id})\n\nমেসেজ: {msg_text}"
            )
            # কোন এডমিন মেসেজের বিপরীতে কোন ইউজার সেটা ম্যাপ করা
            admin_reply_map[m.message_id] = user.id
        await update.message.reply_text("✅ আপনার মেসেজটি আমাদের প্রতিনিধিকে জানানো হয়েছে।")
        
    # এডমিন যখন রিপ্লাই দেয় (ইউজারের কাছে যাবে)
    elif user.id in ADMIN_IDS and update.message.reply_to_message:
        replied_msg_id = update.message.reply_to_message.message_id
        if replied_msg_id in admin_reply_map:
            target_user_id = admin_reply_map[replied_msg_id]
            await context.bot.send_message(chat_id=target_user_id, text=f"👨‍💼 এডমিন রিপ্লাই:\n\n{msg_text}")
            await update.message.reply_text("✅ রিপ্লাই পৌঁছে গেছে।")

# মেইন এক্সেকিউশন
if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_support_messages))
    
    print("বট সফলভাবে চালু হয়েছে...")
    application.run_polling()
