import logging
import json
import os
import random

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

logging.basicConfig(level=logging.INFO)

# ========= CONFIG =========
BOT_TOKEN = "8220357229:AAFmcIIanZ0W4pzGviy3T1K264CzS8DgbUs"

# Put your Telegram user ID here (the person who confirms payments)
ADMIN_USER_IDS = [5632357881]  # <-- replace with your numeric Telegram ID

# Local payment details (shown to buyers)
LOCAL_PAYMENT_TEXT = """
💳 Payment Instructions

Please pay ₹80 to:

• UPI ID: 7575025625@slc
  (or)
• Bank: Your Bank Name
• A/C No: 033325221776083
• IFSC: NESF0000333

📝 After payment, reply here with:
- Screenshot or
- Transaction ID

Once I confirm, you’ll receive your code. 😊
"""

PRICE_TEXT = "₹4000"  # Just for display messages

# Item configuration (no real payments, just labels)
ITEMS = {
    "premium_code": {
        "title": "Shein Premium Code",
        "description": "One-time use premium code."
    }
}

# ========= BOT SETUP =========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ========= ADMIN PANEL STORAGE (File-based for web panel compatibility) =========
PENDING_FILE = "pending_payments.json"
ADMIN_CONFIG_FILE = "admin_config.json"

def load_admin_config():
    if not os.path.exists(ADMIN_CONFIG_FILE):
        return {}
    with open(ADMIN_CONFIG_FILE, "r") as f:
        try:
            return json.load(f)
        except Exception:
            return {}

def load_pending():
    if not os.path.exists(PENDING_FILE):
        return []
    with open(PENDING_FILE, "r") as f:
        return json.load(f)

def save_pending(pending):
    with open(PENDING_FILE, "w") as f:
        json.dump(pending, f, indent=2)

# ========= INVENTORY HELPERS =========

INVENTORY_FILE = "codes.json"


def load_inventory():
    if not os.path.exists(INVENTORY_FILE):
        return {}
    with open(INVENTORY_FILE, "r") as f:
        return json.load(f)


def save_inventory(inv):
    with open(INVENTORY_FILE, "w") as f:
        json.dump(inv, f, indent=2)


def pop_code(item_id):
    inv = load_inventory()
    codes = inv.get(item_id, [])
    if not codes:
        return None
    code = codes.pop(0)
    inv[item_id] = codes
    save_inventory(inv)
    return code

# ========= SIMPLE "HUMAN-LIKE" REPLIES =========


def human_reply(user_text: str) -> str:
    text = user_text.lower()

    greetings = ["hi", "hello", "hey", "yo"]
    buy_words = ["buy", "code", "purchase", "order"]

    if any(w in text for w in greetings):
        return random.choice([
            "Hey! 😊 How can I help you today?",
            "Hello there! What are you looking for?",
            "Hi! Need a code or some info?"
        ])

    if any(w in text for w in buy_words):
        return (
            f"I can sell you a Premium Code for {PRICE_TEXT}.\n\n"
            "Tap the *Buy code* button or send /buy to see payment details. 💳"
        )

    # Default friendly reply
    return random.choice([
        f"If you want to buy a code ({PRICE_TEXT}), just send /buy. 😊",
        "I’m your little shop bot. For a code, type /buy.",
        "Got it! When you’re ready to buy, say /buy. 😉"
    ])

# ========= KEYBOARD =========


def main_keyboard():
    kb = ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=False,
        input_field_placeholder="",
        selective=False,
        is_persistent=False,
    )
    kb.add(KeyboardButton(text="💳 Buy code", request_contact=False, request_location=False))
    kb.add(KeyboardButton(text="❓ Help", request_contact=False, request_location=False))
    return kb

# ========= COMMAND HANDLERS =========
# ========= ADMIN PANEL: /panel =========
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

@dp.message_handler(commands=["panel"])
async def cmd_panel(message: types.Message):
    if message.from_user.id not in ADMIN_USER_IDS:
        await message.answer("You are not allowed to use this command.")
        return
    pending_payments = load_pending()
    if not pending_payments:
        await message.answer("No pending payment requests.")
        return
    for req in pending_payments:
        # List the pending request (admin can use web panel or /grant to process)
        await message.answer(
            f"Payment request from @{req['username'] or req['user_id']} for {ITEMS[req['item_id']]['title']}"
        )

# ========= CALLBACK HANDLER FOR GRANT CODE =========
@dp.callback_query_handler(lambda c: c.data and c.data.startswith("grant:"))
async def process_grant_callback(callback_query: CallbackQuery):
    if callback_query.from_user.id not in ADMIN_USER_IDS:
        await callback_query.answer("Not allowed.", show_alert=True)
        return
    _, user_id, item_id = callback_query.data.split(":")
    user_id = int(user_id)
    code = pop_code(item_id)
    if not code:
        await callback_query.answer("No codes left.", show_alert=True)
        return
    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                "✅ Payment confirmed!\n\n"
                f"Here is your code:\n```\n{code}\n```\n\n"
                "Thank you for your purchase 🎉"
            ),
            parse_mode="Markdown"
        )
        await callback_query.answer("Code sent!", show_alert=True)
        # Remove from pending_payments.json
        pending = load_pending()
        pending = [req for req in pending if not (str(req['user_id']) == str(user_id) and req['item_id'] == item_id)]
        save_pending(pending)
    except Exception as e:
        await callback_query.answer(f"Error: {e}", show_alert=True)


@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    text = (
        "Hey! 👋\n\n"
        "I’m your friendly code shop bot.\n"
        f"I sell Premium Codes of Rs {PRICE_TEXT} for rs 80 and deliver them here after you pay.\n\n"
        "Tap *Buy code* to see payment details, or send /buy."
    )
    await message.answer(text, reply_markup=main_keyboard(), parse_mode="Markdown")


@dp.message_handler(commands=["help"])
async def cmd_help(message: types.Message):
    text = (
        "Here’s how it works:\n\n"
        f"1️⃣ Send /buy – I’ll show you how to pay {PRICE_TEXT}\n"
        "2️⃣ Pay to the UPI/bank details I send\n"
        "3️⃣ Send me a screenshot or transaction ID\n"
        "4️⃣ My owner confirms payment and I send you a unique code 🎁\n\n"
        "Each code is one-time use only."
    )
    await message.answer(text, reply_markup=main_keyboard(), parse_mode="Markdown")


@dp.message_handler(commands=["buy"])
async def cmd_buy(message: types.Message):
    # For now we only sell "premium_code"
    item = ITEMS["premium_code"]
    # include admin mobile (if configured) so users can call/admin for help
    cfg = load_admin_config()
    admin_mobile = cfg.get("admin_mobile") if isinstance(cfg, dict) else None
    extra = ""
    if admin_mobile:
        # Prepare clickable WhatsApp and tel links; use wa.me with country code 91 (India)
        wa_link = f"https://wa.me/91{admin_mobile}?text=I%20have%20paid%20for%20the%20order"
        tel_link = f"tel:{admin_mobile}"
        extra = f"\n\nNeed help? WhatsApp: {wa_link}  |  Call: {tel_link}"

    text = (
        f"You’re buying: {item['title']}\n"
        f"Price: {PRICE_TEXT}\n\n"
        + LOCAL_PAYMENT_TEXT
        + extra
    )
    # send as plain text so links are autolinked by Telegram (avoid Markdown parsing issues)
    await message.answer(text, reply_markup=main_keyboard())

# ========= ADMIN COMMAND: /grant (confirm payment & send code) =========
# Usage:
# 1) Admin replies to the buyer's message (any message in the chat)
# 2) Admin sends: /grant premium_code


@dp.message_handler(commands=["grant"])
async def cmd_grant(message: types.Message):
    # Check admin
    if message.from_user.id not in ADMIN_USER_IDS:
        await message.answer("You are not allowed to use this command.")
        return

    # Get item_id from command arguments
    args = (message.get_args() or "").strip()
    if not args:
        await message.answer("Usage: reply to the user and send /grant premium_code", parse_mode="Markdown")
        return

    item_id = args.split()[0]
    if item_id not in ITEMS:
        await message.answer("Unknown item_id. Example: premium_code", parse_mode="Markdown")
        return

    # Must be used as reply to buyer's message
    if not message.reply_to_message:
        await message.answer("Please reply to the user's message and then send /grant premium_code.", parse_mode="Markdown")
        return

    buyer = message.reply_to_message.from_user

    # Pop a code from inventory
    code = pop_code(item_id)
    if not code:
        await message.answer(
            f"❌ No codes left in inventory for {item_id}. Please restock codes.json.",
            parse_mode="Markdown"
        )
        return

    # Send code to the buyer (in their chat)
    try:
        await bot.send_message(
            chat_id=buyer.id,
            text=(
                "✅ Payment confirmed!\n\n"
                f"Here is your code:\n```\n{code}\n```\n\n"
                "Thank you for your purchase 🎉"
            ),
            parse_mode="Markdown"
        )
        await message.answer(f"✅ Code sent to @{buyer.username or buyer.id}")
    except Exception as e:
        logging.exception("Error sending code to buyer")
        await message.answer(f"Error sending code to user: {e}")

# ========= TEXT HANDLER (HUMAN-LIKE CHAT) =========


@dp.message_handler()
async def handle_text(message: types.Message):
    text = message.text.lower()

    # Shortcut buttons:
    if "buy code" in text:
        await cmd_buy(message)
        return
    if "help" in text:
        await cmd_help(message)
        return

    reply = human_reply(message.text)
    await message.answer(reply, reply_markup=main_keyboard(), parse_mode="Markdown")
    # If user sends payment confirmation, add to pending_payments.json
    if message.from_user.id not in ADMIN_USER_IDS and ("screenshot" in text or "transaction" in text):
        req = {
            "user_id": message.from_user.id,
            "username": message.from_user.username,
            "item_id": "premium_code"
        }
        pending = load_pending()
        pending.append(req)
        save_pending(pending)
        await message.answer("Your payment request has been received. Please wait for admin confirmation.")
        # Notify admins about new pending payment
        notify_text = (
            f"🆕 New payment request:\n"
            f"User: @{req['username'] or req['user_id']} ({req['user_id']})\n"
            f"Item: {ITEMS[req['item_id']]['title']}\n"
            "Use /panel to view pending requests or open the admin panel."
        )
        for admin_id in ADMIN_USER_IDS:
            try:
                await bot.send_message(chat_id=admin_id, text=notify_text)
            except Exception:
                logging.exception(f"Failed to notify admin {admin_id}")


if __name__ == "__main__":
    print("Bot is running...")
    executor.start_polling(dp, skip_updates=True)