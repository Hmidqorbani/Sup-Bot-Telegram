import os
import json
import asyncio
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ================== تنظیمات ==================
BOT_TOKEN = "8529660188:AAEovc-HbLkeTJ0mMbJ50cx5ufhmaMtIsJk"
ADMIN_ID = 588149325  # آیدی عددی ادمین


# BOT_TOKEN = os.getenv("BOT_TOKEN")
# ADMIN_ID = int(os.getenv("ADMIN_ID"))

USERS_FILE = "users.json"
WELCOME_FILE = "welcome.txt"
FORCE_JOIN_FILE = "force_join.json"
# ============================================

message_map = {}
users = set()
last_user_id = None

DEFAULT_WELCOME = (
    "سلام دوست من 👋\n"
    "پشتیبانی در اسرع وقت جواب می‌ده."
)

DEFAULT_FORCE_JOIN = {"enabled": False, "channels": []}


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


def load_force_join():
    try:
        with open(FORCE_JOIN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {
                "enabled": bool(data.get("enabled", False)),
                "channels": data.get("channels", []),
            }
    except (FileNotFoundError, json.JSONDecodeError, AttributeError):
        return DEFAULT_FORCE_JOIN.copy()


def save_force_join(settings):
    with open(FORCE_JOIN_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def force_join_menu():
    settings = load_force_join()
    state = "روشن ✅" if settings["enabled"] else "خاموش ❌"
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"وضعیت: {state}", callback_data="admin_join_toggle")],
            [InlineKeyboardButton("➕ افزودن کانال", callback_data="admin_join_add")],
            [InlineKeyboardButton("📋 کانال‌ها", callback_data="admin_join_list")],
            [InlineKeyboardButton("↩️ بازگشت", callback_data="admin_back")],
        ]
    )


def required_channels_keyboard(channels):
    keyboard = [
        [InlineKeyboardButton(channel["title"], url=channel["link"])]
        for channel in channels
    ]
    keyboard.append(
        [InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_join")]
    )
    return InlineKeyboardMarkup(keyboard)


async def get_missing_channels(bot, user_id):
    settings = load_force_join()
    if not settings["enabled"] or not settings["channels"]:
        return []

    missing = []
    for channel in settings["channels"]:
        try:
            member = await bot.get_chat_member(channel["chat_id"], user_id)
            if member.status not in {
                ChatMemberStatus.MEMBER,
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.OWNER,
            }:
                missing.append(channel)
        except Exception:
            missing.append(channel)
    return missing


async def require_channel_membership(update, context):
    user = update.effective_user
    if not user or user.id == ADMIN_ID:
        return True

    missing = await get_missing_channels(context.bot, user.id)
    if not missing:
        return True

    await update.effective_message.reply_text(
        "برای استفاده از ربات، ابتدا در کانال‌های زیر عضو شوید:",
        reply_markup=required_channels_keyboard(missing),
    )
    return False


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
        [InlineKeyboardButton("🔒 جوین اجباری", callback_data="admin_join")],
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
    if not await require_channel_membership(update, context):
        return

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

    if not await require_channel_membership(update, context):
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

    if query.data == "check_join":
        missing = await get_missing_channels(context.bot, query.from_user.id)
        if missing:
            await query.edit_message_text(
                "هنوز عضویت شما در همه کانال‌ها تأیید نشده است:",
                reply_markup=required_channels_keyboard(missing),
            )
        else:
            await query.edit_message_text("✅ عضویت شما تأیید شد. حالا می‌توانید پیام بفرستید.")
        return

    if query.from_user.id != ADMIN_ID:
        return

    data = query.data

    if data == "admin_join":
        await query.edit_message_text(
            "🔒 مدیریت جوین اجباری\nکانال‌ها را مدیریت کنید:",
            reply_markup=force_join_menu(),
        )

    elif data == "admin_join_toggle":
        settings = load_force_join()
        if not settings["channels"]:
            await query.answer("ابتدا حداقل یک کانال اضافه کنید.", show_alert=True)
            return
        settings["enabled"] = not settings["enabled"]
        save_force_join(settings)
        await query.edit_message_text(
            "🔒 مدیریت جوین اجباری\nکانال‌ها را مدیریت کنید:",
            reply_markup=force_join_menu(),
        )

    elif data == "admin_join_add":
        context.user_data["waiting_for_channel_title"] = True
        context.user_data.pop("pending_channel_title", None)
        await query.edit_message_text(
            " نام کانال را بفرستید.\n\n"
            "برای لغو، /cancel را بفرستید."
        )

    elif data == "admin_join_list":
        settings = load_force_join()
        if not settings["channels"]:
            text = "📋 هنوز کانالی ثبت نشده است."
            keyboard = force_join_menu()
        else:
            lines = ["📋 کانال‌های ثبت‌شده:"]
            keyboard_rows = []
            for index, channel in enumerate(settings["channels"], start=1):
                lines.append(f"{index}. {channel['title']} ({channel['chat_id']})")
                keyboard_rows.append(
                    [
                        InlineKeyboardButton(
                            f"🗑 حذف {channel['title']}",
                            callback_data=f"admin_join_remove:{index - 1}",
                        )
                    ]
                )
            text = "\n".join(lines)
            keyboard_rows.append(
                [InlineKeyboardButton("↩️ بازگشت", callback_data="admin_join")]
            )
            keyboard = InlineKeyboardMarkup(keyboard_rows)
        await query.edit_message_text(text, reply_markup=keyboard)

    elif data.startswith("admin_join_remove:"):
        try:
            index = int(data.rsplit(":", 1)[1])
            settings = load_force_join()
            removed = settings["channels"].pop(index)
            if not settings["channels"]:
                settings["enabled"] = False
            save_force_join(settings)
            await query.edit_message_text(
                f"✅ کانال «{removed['title']}» حذف شد.",
                reply_markup=force_join_menu(),
            )
        except (ValueError, IndexError):
            await query.edit_message_text(
                "❌ این کانال دیگر وجود ندارد.", reply_markup=force_join_menu()
            )

    elif data == "admin_back":
        await query.edit_message_text(
            "یکی از گزینه‌ها رو انتخاب کن:", reply_markup=get_admin_inline_menu()
        )

    elif data == "admin_stats":
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

    if context.user_data.get("waiting_for_channel_title"):
        title = text.strip()
        if not title:
            await update.message.reply_text("❌ نام کانال نمی‌تواند خالی باشد.")
            return

        context.user_data["pending_channel_title"] = title
        context.user_data["waiting_for_channel_title"] = False
        context.user_data["waiting_for_channel_link"] = True
        await update.message.reply_text(
            "حالا لینک عضویت همین کانال را بفرستید.\n\n"
            "مثال: https://t.me/my_channel\n\n"
            "ربات باید در کانال ادمین باشد.\n"
            "برای لغو، /cancel را بفرستید."
        )
        return

    if context.user_data.get("waiting_for_channel_link"):
        link = text.strip()
        title = context.user_data.get("pending_channel_title")
        if not title or not link.startswith(("https://t.me/", "http://t.me/")):
            await update.message.reply_text(
                "❌ لینک معتبر نیست. نمونه:\nhttps://t.me/my_channel"
            )
            return

        try:
            chat = await context.bot.get_chat(title)
            bot_user = await context.bot.get_me()
            bot_member = await context.bot.get_chat_member(chat.id, bot_user.id)
            if bot_member.status not in {
                ChatMemberStatus.ADMINISTRATOR,
                ChatMemberStatus.OWNER,
            }:
                raise PermissionError

            settings = load_force_join()
            if any(channel["chat_id"] == chat.id for channel in settings["channels"]):
                await update.message.reply_text("❌ این کانال قبلاً ثبت شده است.")
            else:
                settings["channels"].append(
                    {"chat_id": chat.id, "title": chat.title, "link": link}
                )
                save_force_join(settings)
                await update.message.reply_text(
                    f"✅ کانال «{chat.title}» اضافه شد.",
                    reply_markup=force_join_menu(),
                )
        except PermissionError:
            await update.message.reply_text("❌ ربات در این کانال ادمین نیست.")
        except Exception:
            await update.message.reply_text(
                "❌ کانال پیدا نشد یا دسترسی ربات به آن کافی نیست."
            )
        context.user_data["waiting_for_channel_link"] = False
        context.user_data.pop("pending_channel_title", None)
        return

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
    context.user_data["waiting_for_channel_title"] = False
    context.user_data["waiting_for_channel_link"] = False
    context.user_data.pop("pending_channel_title", None)

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
