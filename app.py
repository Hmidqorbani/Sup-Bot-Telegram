import os
import json
import asyncio
from datetime import datetime
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ================== تنظیمات ==================
# BOT_TOKEN = ""
# ADMIN_ID =   # آیدی عددی ادمین


BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

USERS_FILE = "users.json"
WELCOME_FILE = "welcome.txt"
# ============================================

message_map = {}
users = set()
last_user_id = None

DEFAULT_WELCOME = (
    "سلام دوست من 👋\n"
    "پشتیبانی در اسرع وقت جواب می‌ده."
)


def load_users():
    global users
    try:
        with open(USERS_FILE, "r") as f:
            data = json.load(f)
            users = set(data)
    except:
        users = set()


def save_users():
    with open(USERS_FILE, "w") as f:
        json.dump(list(users), f)


def load_welcome():
    try:
        with open(WELCOME_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except:
        return DEFAULT_WELCOME


def save_welcome(text: str):
    with open(WELCOME_FILE, "w", encoding="utf-8") as f:
        f.write(text)


def get_admin_inline_menu():
    keyboard = [
        [
            InlineKeyboardButton("📊 آمار", callback_data="admin_stats"),
            InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast"),
        ],
        [
            InlineKeyboardButton(
                "📝 تغییر خوش‌آمدگویی", callback_data="admin_setwelcome"
            ),
            InlineKeyboardButton(
                "👀 مشاهده خوش‌آمدگویی", callback_data="admin_welcome"
            ),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_admin_reply_keyboard():
    keyboard = [
        [KeyboardButton("🛠 پنل مدیریت")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ================== هندلرها ==================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    users.add(user.id)
    save_users()

    welcome_text = load_welcome()
    await update.message.reply_text(welcome_text)


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    # هم کیبورد پایین و هم منوی شیشه‌ای ارسال می‌شه
    await update.message.reply_text(
        "🛠 پنل مدیریت فعال شد\nکیبورد پایین صفحه برات تنظیم شد.",
        reply_markup=get_admin_reply_keyboard(),
    )

    await update.message.reply_text(
        "یکی از گزینه‌ها رو انتخاب کن:", reply_markup=get_admin_inline_menu()
    )


async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_user_id

    user = update.effective_user
    message = update.message

    if user.id == ADMIN_ID:
        return

    users.add(user.id)
    save_users()

    if user.id != last_user_id:
        info = (
            f"📩 پیام جدید | نام: {user.full_name} | "
            f"یوزرنیم: @{user.username or 'ندارد'} | "
            f"آیدی: `{user.id}`"
        )
        await context.bot.send_message(chat_id=ADMIN_ID, text=info)
        last_user_id = user.id

    sent = await context.bot.copy_message(
        chat_id=ADMIN_ID, from_chat_id=message.chat_id, message_id=message.message_id
    )

    message_map[sent.message_id] = user.id

    log_msg = await message.reply_text("✅ پیام شما ارسال شد")
    await asyncio.sleep(3)
    try:
        await log_msg.delete()
    except:
        pass


async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not update.message.reply_to_message:
        return

    replied_id = update.message.reply_to_message.message_id
    user_id = message_map.get(replied_id)

    if not user_id:
        await update.message.reply_text("❌ این پیام دیگه قابل پاسخ نیست.")
        return

    try:
        await context.bot.copy_message(
            chat_id=user_id,
            from_chat_id=update.message.chat_id,
            message_id=update.message.message_id,
        )
        await update.message.reply_text("✅ ارسال شد")
        message_map.pop(replied_id, None)
    except Exception as e:
        await update.message.reply_text(f"❌ خطا در ارسال: {e}")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    data = query.data

    if data == "admin_stats":
        text = (
            f"📊 آمار ربات\n\n"
            f"تعداد کل کاربران: {len(users)}\n"
            f"پیام‌های در انتظار پاسخ: {len(message_map)}"
        )
        await query.edit_message_text(text, reply_markup=get_admin_inline_menu())

    elif data == "admin_welcome":
        current = load_welcome()
        text = f"📝 پیام خوش‌آمدگویی فعلی:\n\n{current}"
        await query.edit_message_text(text, reply_markup=get_admin_inline_menu())

    elif data == "admin_setwelcome":
        context.user_data["waiting_for_welcome"] = True
        await query.edit_message_text(
            "📝 لطفاً متن جدید خوش‌آمدگویی رو ارسال کنید:\n\n"
            "(برای لغو، /cancel رو بفرستید)"
        )

    elif data == "admin_broadcast":
        context.user_data["waiting_for_broadcast"] = True
        await query.edit_message_text(
            "📢 لطفاً متن پیام همگانی رو ارسال کنید:\n\n"
            "(برای لغو، /cancel رو بفرستید)"
        )


async def handle_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    text = update.message.text

    # دکمه‌های کیبورد پایین
    if text == "📊 آمار":
        await update.message.reply_text(
            f"📊 آمار ربات\n\n"
            f"تعداد کل کاربران: {len(users)}\n"
            f"پیام‌های در انتظار پاسخ: {len(message_map)}"
        )
        return

    elif text == "👀 مشاهده خوش‌آمدگویی":
        current = load_welcome()
        await update.message.reply_text(f"📝 پیام خوش‌آمدگویی فعلی:\n\n{current}")
        return

    elif text == "📝 تغییر خوش‌آمدگویی":
        context.user_data["waiting_for_welcome"] = True
        await update.message.reply_text(
            "📝 لطفاً متن جدید خوش‌آمدگویی رو ارسال کنید:\n\n"
            "(برای لغو، /cancel رو بفرستید)"
        )
        return

    elif text == "📢 پیام همگانی":
        context.user_data["waiting_for_broadcast"] = True
        await update.message.reply_text(
            "📢 لطفاً متن پیام همگانی رو ارسال کنید:\n\n"
            "(برای لغو، /cancel رو بفرستید)"
        )
        return

    elif text == "🛠 پنل مدیریت":
        await update.message.reply_text(
            "🛠 پنل مدیریت ربات\n\nیکی از گزینه‌ها رو انتخاب کن:",
            reply_markup=get_admin_inline_menu(),
        )
        return

    # حالت انتظار برای تغییر خوش‌آمدگویی
    if context.user_data.get("waiting_for_welcome"):
        save_welcome(text)
        context.user_data["waiting_for_welcome"] = False
        await update.message.reply_text(
            f"✅ پیام خوش‌آمدگویی با موفقیت تغییر کرد.\n\nمتن جدید:\n{text}"
        )
        return

    # حالت انتظار برای پیام همگانی
    if context.user_data.get("waiting_for_broadcast"):
        context.user_data["waiting_for_broadcast"] = False

        success = 0
        failed = 0
        status_msg = await update.message.reply_text(
            f"⏳ در حال ارسال به {len(users)} کاربر..."
        )

        for user_id in list(users):
            try:
                await context.bot.send_message(chat_id=user_id, text=text)
                success += 1
            except:
                failed += 1

        await status_msg.edit_text(
            f"✅ پیام همگانی ارسال شد\nموفق: {success}\nناموفق: {failed}"
        )
        return


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    context.user_data["waiting_for_welcome"] = False
    context.user_data["waiting_for_broadcast"] = False

    await update.message.reply_text("❌ عملیات لغو شد.")


# ================== اجرا ==================


def main():
    load_users()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("cancel", cancel))

    app.add_handler(CallbackQueryHandler(button_handler))

    app.add_handler(
        MessageHandler(filters.REPLY & filters.User(ADMIN_ID), handle_admin_reply),
        group=1,
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.User(ADMIN_ID) & ~filters.COMMAND, handle_admin_text
        ),
        group=2,
    )

    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_user_message))

    print("ربات با موفقیت اجرا شد...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    main()
