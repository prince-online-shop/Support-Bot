import asyncio
import pandas as pd
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = "YOUR_BOT_TOKEN"
SHEET_ID = "YOUR_SHEET_ID"
ADMIN_GROUP_ID = -100XXXXXXXXXX

# ================== Google Sheet Load ==================
def load_sheet():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
    return pd.read_csv(url)

data = load_sheet()

async def refresh_sheet():
    global data
    while True:
        try:
            data = load_sheet()
        except:
            pass
        await asyncio.sleep(60)

# ================== Database ==================
conn = sqlite3.connect("tickets.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    status TEXT
)
""")
conn.commit()

# ================== Menu Generator ==================
def get_menu(parent_id):
    rows = data[data["Parent_ID"] == parent_id]
    keyboard = []
    for _, row in rows.iterrows():
        keyboard.append(
            [InlineKeyboardButton(row["Button_Text"], callback_data=str(row["ID"]))]
        )
    return InlineKeyboardMarkup(keyboard)

# ================== Start ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "মেনু নির্বাচন করুন:",
        reply_markup=get_menu(0)
    )

# ================== Button Click ==================
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    row = data[data["ID"] == int(query.data)].iloc[0]

    if row["Type"] == "menu":
        await query.message.reply_text(
            "নির্বাচন করুন:",
            reply_markup=get_menu(row["ID"])
        )

    elif row["Type"] == "info":
        await query.message.reply_text(row["Reply_Text"])

    elif row["Type"] == "support":
        user = query.from_user
        cursor.execute(
            "INSERT INTO tickets (user_id, username, status) VALUES (?, ?, ?)",
            (user.id, user.full_name, "OPEN")
        )
        conn.commit()
        ticket_id = cursor.lastrowid

        context.user_data["ticket"] = ticket_id

        await query.message.reply_text(
            f"🎫 Ticket #{ticket_id} তৈরি হয়েছে\nআপনার সমস্যা লিখুন:"
        )

# ================== User Message → Admin ==================
async def user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "ticket" in context.user_data:
        ticket_id = context.user_data["ticket"]
        user = update.message.from_user

        keyboard = [[InlineKeyboardButton("🔴 Close", callback_data=f"close_{ticket_id}")]]
        sent = await context.bot.send_message(
            ADMIN_GROUP_ID,
            f"🎫 Ticket #{ticket_id}\nUser ID: {user.id}\nName: {user.full_name}\n\n{update.message.text}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        context.user_data.clear()
        await update.message.reply_text("✅ সাপোর্টে পাঠানো হয়েছে।")

# ================== Admin Reply → User ==================
async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.id == ADMIN_GROUP_ID:
        if update.message.reply_to_message:
            text = update.message.reply_to_message.text
            if "User ID:" in text:
                user_id = int(text.split("User ID: ")[1].split("\n")[0])
                await context.bot.send_message(user_id, f"💬 Support:\n{update.message.text}")

# ================== Close Ticket ==================
async def close_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    ticket_id = int(query.data.split("_")[1])
    cursor.execute("UPDATE tickets SET status='CLOSED' WHERE ticket_id=?", (ticket_id,))
    conn.commit()

    await query.edit_message_text(f"🔴 Ticket #{ticket_id} Closed")

# ================== App Run ==================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_click))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, user_message))
app.add_handler(MessageHandler(filters.TEXT & filters.Chat(ADMIN_GROUP_ID), admin_reply))
app.add_handler(CallbackQueryHandler(close_ticket, pattern="^close_"))

app.job_queue.run_once(lambda ctx: asyncio.create_task(refresh_sheet()), 1)

app.run_polling()
