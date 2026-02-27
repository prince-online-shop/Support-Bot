import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- সেটিংস ---
BOT_TOKEN = "8624201473:AAGCtrK4FjtIUCco0ngPrKVK_x4Bt5vSguc"
BOT_USERNAME = "@Prince_telecom_chatbot" # @ ছাড়াই আপনার বটের ইউজারনেম দিন
ADMIN_IDS = [5533760143] # আপনার এবং অন্য এডমিনদের টেলিগ্রাম আইডি
SHEET_NAME = "Support_Bot_DB"
JSON_KEY_FILE = "service_account.json"

# গুগল শিট কানেক্ট করা
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_KEY_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1

# ডিকশনারি ডাটাবেজ (টেম্পোরারি)
active_support = {} 
admin_reply_map = {} 

# শিট থেকে ডেটা রিফ্রেশ করার ফাংশন
def get_data():
    return sheet.get_all_records()

# ইনলাইন বাটন তৈরির ফাংশন
def make_menu(parent_id, all_data):
    keyboard = []
    filtered = [row for row in all_data if str(row['Parent_ID']) == str(parent_id)]
    for row in filtered:
        keyboard.append([InlineKeyboardButton(row['Button_Text'], callback_data=str(row['ID']))])
    return InlineKeyboardMarkup(keyboard)

# /start কমান্ড (গ্রুপ এবং পার্সোনাল উভয় ক্ষেত্রে কাজ করবে)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_type = update.effective_chat.type
    all_data = get_data()

    # যদি গ্রুপে /start দেয়
    if chat_type in ["group", "supergroup"]:
        keyboard = [[InlineKeyboardButton("🟢 লাইভ সাপোর্ট শুরু করুন", url=f"https://t.me/{BOT_USERNAME}?start=support")]]
        await update.message.reply_text("সরাসরি কথা বলতে নিচের বাটনে চাপ দিয়ে আমার ইনবক্সে আসুন:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    # যদি প্রাইভেট চ্যাটে আসে
    reply_markup = make_menu(0, all_data)
    await update.message.reply_text("স্বাগতম! নিচের মেনু থেকে আপনার পছন্দ বেছে নিন:", reply_markup=reply_markup)

# বাটন ক্লিক হ্যান্ডলার
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    selected_id = query.data
    all_data = get_data()
    
    row = next((r for r in all_data if str(r['ID']) == selected_id), None)
    if not row: return

    res_type = str(row['Type']).lower()
    res_text = row['Reply_Text']

    if res_type == "menu":
        await query.edit_message_text(text=res_text, reply_markup=make_menu(selected_id, all_data))
    elif res_type == "support":
        active_support[user_id] = True
        await context.bot.send_message(chat_id=user_id, text="🟢 লাইভ সাপোর্ট অন হয়েছে। আপনার সমস্যাটি লিখুন:")
    else:
        await context.bot.send_message(chat_id=user_id, text=res_text)

# ইউজার মেসেজ এডমিনকে পাঠানো
async def user_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if user.id in active_support:
        for admin in ADMIN_IDS:
            m = await context.bot.send_message(
                chat_id=admin,
                text=f"📩 মেসেজ ফ্রম: {user.full_name} ({user.id})\n\n{update.message.text}"
            )
            admin_reply_map[m.message_id] = user.id
        await update.message.reply_text("✅ এডমিনকে জানানো হয়েছে।")

# এডমিন রিপ্লাই ইউজারকে পাঠানো
async def admin_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id in ADMIN_IDS and update.message.reply_to_message:
        orig_msg_id = update.message.reply_to_message.message_id
        if orig_msg_id in admin_reply_map:
            user_id = admin_reply_map[orig_msg_id]
            await context.bot.send_message(chat_id=user_id, text=f"👨‍💼 এডমিন: {update.message.text}")
            await update.message.reply_text("✅ রিপ্লাই পাঠানো হয়েছে।")

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE & ~filters.REPLY, user_to_admin))
    app.add_handler(MessageHandler(filters.REPLY & filters.TEXT & filters.ChatType.PRIVATE, admin_to_user))
    
    print("বট চলছে...")
    app.run_polling()
