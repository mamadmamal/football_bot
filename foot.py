# ------------------------------
# بخش ۱: تنظیمات اولیه و اتصال به دیتابیس
# ------------------------------

import os
import random
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters
from tinydb import TinyDB, Query

# ساخت پوشه دیتابیس در صورت نبود
os.makedirs("database", exist_ok=True)

# اتصال به دیتابیس
db = TinyDB('database/users.json')
User = Query()

# لیست تیم‌ها
TEAMS = {
    "vip": "🔥 تیم VIP",
    "basic": "🌱 تیم معمولی"
}

# --- پایان بخش ۱: تنظیمات اولیه ---

# ------------------------------
# بخش ۲: مدیریت کاربران و سکه‌ها
# ------------------------------

# بررسی وجود کاربر در دیتابیس
def get_user(user_id):
    user = db.get(User.id == user_id)
    return user

# ثبت‌نام کاربر جدید
def register_user(user_id, username):
    user = {
        'id': user_id,
        'username': username,
        'coins': 100,
        'team': None,
        'medals': [],
        'last_spin': None,
        'last_guess': None
    }
    db.insert(user)
    return user

# گرفتن یا ساختن کاربر
def get_or_create_user(user_id, username):
    user = get_user(user_id)
    if user:
        return user
    else:
        return register_user(user_id, username)

# افزودن سکه به کاربر
def add_coins(user_id, amount):
    user = get_user(user_id)
    if user:
        new_amount = user['coins'] + amount
        db.update({'coins': new_amount}, User.id == user_id)

# کم کردن سکه از کاربر
def remove_coins(user_id, amount):
    user = get_user(user_id)
    if user and user['coins'] >= amount:
        new_amount = user['coins'] - amount
        db.update({'coins': new_amount}, User.id == user_id)
        return True
    return False

# تنظیم تیم کاربر
def set_team(user_id, team_key):
    if team_key in TEAMS:
        db.update({'team': team_key}, User.id == user_id)

# گرفتن نام تیم کاربر
def get_team_name(user):
    team_key = user.get('team')
    return TEAMS.get(team_key, "بدون تیم")

# --- پایان بخش ۲: مدیریت کاربران و سکه‌ها ---

# ------------------------------
# بخش ۳: هندلر /start و منوی اصلی
# ------------------------------

def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    username = update.effective_user.username or "بدون‌نام"
    user = get_or_create_user(user_id, username)

    keyboard = [
        [InlineKeyboardButton("🎮 بازی", callback_data="menu_game")],
        [InlineKeyboardButton("💰 شرط‌بندی", callback_data="menu_bet")],
        [InlineKeyboardButton("👤 پروفایل", callback_data="menu_profile")],
        [InlineKeyboardButton("⚙️ انتخاب تیم", callback_data="menu_team")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("به ربات خوش اومدی! یه گزینه رو انتخاب کن:", reply_markup=reply_markup)

# --- پایان بخش ۳: هندلر /start و منوی اصلی ---

# ------------------------------
# بخش ۴: انتخاب تیم توسط کاربر
# ------------------------------

def handle_team_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.username or "بدون‌نام"
    user = get_or_create_user(user_id, username)

    keyboard = [
        [InlineKeyboardButton("🔥 تیم VIP", callback_data="team_vip")],
        [InlineKeyboardButton("🌱 تیم معمولی", callback_data="team_basic")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("یه تیم انتخاب کن:", reply_markup=reply_markup)

def apply_team_choice(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id

    if query.data == "team_vip":
        set_team(user_id, "vip")
        query.edit_message_text("✅ تیم VIP انتخاب شد!")
    elif query.data == "team_basic":
        set_team(user_id, "basic")
        query.edit_message_text("✅ تیم معمولی انتخاب شد!")

# --- پایان بخش ۴: انتخاب تیم توسط کاربر ---

# ------------------------------
# بخش ۵: بازی چرخ‌شانس (Spin)
# ------------------------------

def handle_spin(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.username or "بدون‌نام"
    user = get_or_create_user(user_id, username)

    now = datetime.now()
    last_spin = user.get('last_spin')
    if last_spin:
        last_time = datetime.strptime(last_spin, "%Y-%m-%d %H:%M:%S")
        if now - last_time < timedelta(hours=1):
            query.answer("⏳ هر ساعت فقط یک‌بار می‌تونی بچرخی!")
            return

    reward = random.choice([10, 20, 30, 50, 100])
    add_coins(user_id, reward)
    db.update({'last_spin': now.strftime("%Y-%m-%d %H:%M:%S")}, User.id == user_id)
    query.edit_message_text(f"🎉 چرخیدی و {reward} سکه گرفتی!")

# --- پایان بخش ۵: بازی چرخ‌شانس ---

# ------------------------------
# بخش ۶: بازی حدس عدد (Guess)
# ------------------------------

def handle_guess(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.username or "بدون‌نام"
    user = get_or_create_user(user_id, username)

    now = datetime.now()
    last_guess = user.get('last_guess')
    if last_guess:
        last_time = datetime.strptime(last_guess, "%Y-%m-%d %H:%M:%S")
        if now - last_time < timedelta(hours=1):
            query.answer("⏳ هر ساعت فقط یک‌بار می‌تونی حدس بزنی!")
            return

    number = random.randint(1, 5)
    keyboard = [
        [InlineKeyboardButton(str(i), callback_data=f"guess_{i}") for i in range(1, 6)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("🤔 یه عدد بین ۱ تا ۵ حدس بزن:", reply_markup=reply_markup)

    context.user_data['guess_number'] = number
    db.update({'last_guess': now.strftime("%Y-%m-%d %H:%M:%S")}, User.id == user_id)

def handle_guess_result(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    user = get_user(user_id)

    if not user or 'guess_number' not in context.user_data:
        query.answer("❌ خطا در حدس! دوباره امتحان کن.")
        return

    correct = context.user_data['guess_number']
    chosen = int(query.data.split("_")[1])

    if chosen == correct:
        add_coins(user_id, 50)
        query.edit_message_text("🎯 درست حدس زدی! ۵۰ سکه گرفتی!")
    else:
        query.edit_message_text(f"😅 نه! عدد درست {correct} بود.")

    del context.user_data['guess_number']

# --- پایان بخش ۶: بازی حدس عدد ---

# ------------------------------
# بخش ۷: شرط‌بندی بین کاربران
# ------------------------------

# شروع شرط‌بندی
def handle_bet_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    query.edit_message_text("💰 برای شرط‌بندی، عدد سکه رو بنویس (مثلاً 50):")
    context.user_data['bet_stage'] = 'awaiting_amount'

# دریافت مبلغ شرط
def handle_bet_amount(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    username = update.effective_user.username or "بدون‌نام"
    user = get_or_create_user(user_id, username)

    if context.user_data.get('bet_stage') != 'awaiting_amount':
        return

    try:
        amount = int(update.message.text)
        if amount <= 0 or user['coins'] < amount:
            update.message.reply_text("❌ مبلغ نامعتبر یا سکه کافی نداری.")
            return
        context.user_data['bet_amount'] = amount
        context.user_data['bet_stage'] = 'awaiting_opponent'
        update.message.reply_text("👤 حالا آیدی عددی رقیبت رو بفرست (مثلاً 123456789):")
    except:
        update.message.reply_text("❌ لطفاً فقط عدد بفرست.")

# دریافت رقیب و بررسی نتیجه
def handle_bet_opponent(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    username = update.effective_user.username or "بدون‌نام"
    user = get_or_create_user(user_id, username)

    if context.user_data.get('bet_stage') != 'awaiting_opponent':
        return

    try:
        opponent_id = int(update.message.text)
        opponent = get_user(opponent_id)
        if not opponent or opponent['coins'] < context.user_data['bet_amount']:
            update.message.reply_text("❌ رقیب پیدا نشد یا سکه کافی نداره.")
            return

        amount = context.user_data['bet_amount']
        winner_id = random.choice([user_id, opponent_id])
        loser_id = opponent_id if winner_id == user_id else user_id

        add_coins(winner_id, amount)
        remove_coins(loser_id, amount)

        winner_text = "🎉 تو برنده شدی!" if winner_id == user_id else "😢 باختی!"
        update.message.reply_text(f"{winner_text} مبلغ شرط: {amount} سکه")

        context.user_data.clear()
    except:
        update.message.reply_text("❌ آیدی نامعتبره.")
        context.user_data.clear()

# --- پایان بخش ۷: شرط‌بندی بین کاربران ---

# ------------------------------
# بخش ۸: پروفایل و مدال‌ها
# ------------------------------

def handle_profile(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.username or "بدون‌نام"
    user = get_or_create_user(user_id, username)

    coins = user['coins']
    team = get_team_name(user)
    medals = user.get('medals', [])
    medal_text = "🏅 " + " ".join(medals) if medals else "نداری!"

    text = f"""
👤 نام کاربری: @{username}
💰 سکه‌ها: {coins}
⚙️ تیم: {team}
🎖️ مدال‌ها: {medal_text}
"""
    query.edit_message_text(text)

# --- پایان بخش ۸: پروفایل و مدال‌ها ---

# ------------------------------
# بخش ۹: مدیریت دکمه‌ها و هندلرها
# ------------------------------

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data

    if data == "menu_game":
        keyboard = [
            [InlineKeyboardButton("🎰 چرخ‌شانس", callback_data="spin")],
            [InlineKeyboardButton("🔢 حدس عدد", callback_data="guess")],
            [InlineKeyboardButton("⬅️ بازگشت", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text("🎮 یکی از بازی‌ها رو انتخاب کن:", reply_markup=reply_markup)

    elif data == "menu_bet":
        handle_bet_menu(update, context)

    elif data == "menu_profile":
        handle_profile(update, context)

    elif data == "menu_team":
        handle_team_selection(update, context)

    elif data == "spin":
        handle_spin(update, context)

    elif data == "guess":
        handle_guess(update, context)

    elif data.startswith("guess_"):
        handle_guess_result(update, context)

    elif data.startswith("team_"):
        apply_team_choice(update, context)

    elif data == "back_to_menu":
        start(update, context)

# --- پایان بخش ۹: مدیریت دکمه‌ها و هندلرها ---

# ------------------------------
# بخش ۱۰: اجرای ربات
# ------------------------------

def main():
    updater = Updater("8470884905:AAFe84i1C6ofaL5J2JEDsBgROSEHQ9_q0Ww", use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(button_handler))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex(r'^\d+$'), handle_bet_amount))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex(r'^\d{5,}$'), handle_bet_opponent))

    updater.start_polling()
    print("✅ ربات اجرا شد...")
    updater.idle()

main()

# --- پایان بخش ۱۰: اجرای ربات ---
