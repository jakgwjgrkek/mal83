import os
import asyncio
import logging
import subprocess
import re
import uuid
import threading
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

# Load .env (Railway pe variables se load hoga)
load_dotenv()

# Config
API_TOKEN = os.getenv('8260830097:AAG8yYDN_kO1CsP1JMJ7YCkH-yyH-jzDey4')  # Railway variables se aayega

if not API_TOKEN:
    raise ValueError("BOT_TOKEN not found! Set it in .env or Railway variables.")

# Logging
logging.basicConfig(level=logging.INFO)

# Bot setup
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# States
class InstaForm(StatesGroup):
    waiting_for_username = State()
    waiting_for_password = State()

# Active sessions
active_sessions = {}

def run_automation(user_id, username, password):
    session_id = str(uuid.uuid4())[:8]
    log_file = f"logs/{user_id}_{session_id}.txt"
    os.makedirs("logs", exist_ok=True)

    active_sessions[user_id] = {"status": "running", "log": log_file}

    cmd = [
        "python", "automation.py",
        "--user", username,
        "--pass", password,
        "--output", log_file
    ]

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Live log streaming (simple way)
        def stream_logs():
            for line in iter(process.stdout.readline, ''):
                line = line.strip()
                if line:
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write(line + "\n")
                    # Send to Telegram (threadsafe)
                    try:
                        asyncio.run_coroutine_threadsafe(
                            bot.send_message(user_id, f"🔄 `{line}`", parse_mode="Markdown"),
                            asyncio.get_event_loop()
                        ).result(timeout=1)
                    except:
                        pass

        log_thread = threading.Thread(target=stream_logs, daemon=True)
        log_thread.start()

        process.wait()
        log_thread.join(timeout=5)

        # Extract final URL from log
        final_url = None
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                content = f.read()
                match = re.search(r"https://sheinverse\.galleri5\.com/instagram\?code=[^&\s]+", content)
                if match:
                    final_url = match.group(0)
        except Exception as e:
            print(f"Log read error: {e}")

        if final_url:
            active_sessions[user_id] = {"status": "done", "url": final_url}
            asyncio.run_coroutine_threadsafe(
                bot.send_message(user_id, f"✅ **Success!** Your Instagram is connected!\n\n🔗 **URL:** {final_url}\n\nSave this for sheinverse setup."),
                asyncio.get_event_loop()
            ).result(timeout=5)
        else:
            active_sessions[user_id] = {"status": "failed"}
            asyncio.run_coroutine_threadsafe(
                bot.send_message(user_id, "❌ **Failed!** Check logs or try again. Common issues: Wrong creds or Instagram blocks."),
                asyncio.get_event_loop()
            ).result(timeout=5)

    except Exception as e:
        print(f"Automation error: {e}")
        active_sessions[user_id] = {"status": "error"}
        asyncio.run_coroutine_threadsafe(
            bot.send_message(user_id, f"⚠️ **Error running automation:** {str(e)}"),
            asyncio.get_event_loop()
        ).result(timeout=5)

@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await message.answer(
        "🚀 **Welcome to Instagram Professional Connector Bot**!\n\n"
        "This bot converts your IG to Professional Creator & connects to sheinverse.galleri5.com.\n\n"
        "**Steps:**\n"
        "1. /connect — Start process\n"
        "2. Enter username/email\n"
        "3. Enter password (secure)\n"
        "4. Wait 2-5 mins for automation\n\n"
        "⚠️ Use real creds carefully. Bot runs on Android Chrome via Selenium.\n\n"
        "Ready? Send /connect!",
        parse_mode="Markdown"
    )

@dp.message(Command("connect"))
async def connect(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if active_sessions.get(user_id):
        await message.answer("⏳ One process already running. Wait or /cancel first.")
        return

    await message.answer("📝 Enter your Instagram **username or email**:")
    await state.set_state(InstaForm.waiting_for_username)

@dp.message(InstaForm.waiting_for_username)
async def get_username(message: Message, state: FSMContext):
    await state.update_data(username=message.text.strip())
    await message.answer("🔒 Now enter your **password** (this message will self-destruct after reading):\n\n*(Type it quickly & send)*")
    await state.set_state(InstaForm.waiting_for_password)

@dp.message(InstaForm.waiting_for_password)
async def get_password(message: Message, state: FSMContext):
    data = await state.get_data()
    username = data['username']
    password = message.text  # Insecure in memory, but for demo — use encryption in prod

    await message.delete()  # Delete password message for security
    await message.answer("🛠 **Starting automation...** This runs in background (2-5 mins).\nLive updates coming soon!\n\nDon't spam commands.")

    await state.clear()

    # Run in background thread
    thread = threading.Thread(
        target=run_automation,
        args=(message.from_user.id, username, password),
        daemon=True
    )
    thread.start()

@dp.message(Command("cancel"))
async def cancel(message: Message):
    user_id = message.from_user.id
    if active_sessions.get(user_id):
        del active_sessions[user_id]
        await message.answer("🛑 Process cancelled. Start fresh with /connect.")
    else:
        await message.answer("ℹ️ No active process found.")

@dp.message(Command("status"))
async def status(message: Message):
    user_id = message.from_user.id
    session = active_sessions.get(user_id)
    if session:
        status = session['status']
        if status == "running":
            await message.answer("⏳ Still running... Check live logs.")
        elif status == "done":
            await message.answer("✅ Done! Check your previous message for URL.")
        else:
            await message.answer("❌ Failed/Error. Try /connect again.")
    else:
        await message.answer("ℹ️ No active session. Use /connect to start.")

async def main():
    print("Bot starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
