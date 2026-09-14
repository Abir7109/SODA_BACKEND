"""
Telegram Bot — background thread module for SODA.
Runs python-telegram-bot in a dedicated thread with its own asyncio loop.
Zero impact on the main Socket.IO server performance.
"""
import asyncio
import os
import threading
import zipfile
from pathlib import Path

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from telegram.error import NetworkError, TelegramError


class TelegramBot:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._token = os.getenv("BOT_TOKEN", "")
        self._user_id = int(os.getenv("TELEGRAM_USER_ID", "0"))
        self._app = None
        self._loop = None
        self._thread = None
        self._sio = None
        self._running = False

    def _get_bot_token(self):
        token = self._token
        if not token:
            from dotenv import load_dotenv
            load_dotenv()
            token = os.getenv("BOT_TOKEN", "")
        return token

    def start(self, sio):
        if self._running:
            print("[TELEGRAM] Already running, skipping start")
            return
        self._sio = sio
        token = self._get_bot_token()
        if not token:
            print("[TELEGRAM] ⚠️  No BOT_TOKEN set — Telegram bot DISABLED")
            print("[TELEGRAM]    Set BOT_TOKEN in .env to enable Telegram bridge")
            return
        if not self._user_id:
            print("[TELEGRAM] ⚠️  No TELEGRAM_USER_ID set — bot will accept ALL users")
            print("[TELEGRAM]    Set TELEGRAM_USER_ID in .env for security")
        self._running = True
        self._thread = threading.Thread(target=self._run_bot, args=(token,), daemon=True)
        self._thread.start()
        print(f"[TELEGRAM] 🚀 Bot thread started (user_id={self._user_id or 'ANY'})")

    def stop(self):
        self._running = False
        if self._app:
            try:
                self._app.stop()
            except:
                pass
        if self._loop and self._loop.is_running():
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except:
                pass
        print("[TELEGRAM] Bot stopped")

    def _run_bot(self, token):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        retry_delay = 5
        while self._running:
            try:
                self._app = (
                    ApplicationBuilder()
                    .token(token)
                    .connect_timeout(15)
                    .read_timeout(15)
                    .build()
                )
                self._app.add_handler(
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
                )
                self._app.post_init = self._post_init
                print("[TELEGRAM] Starting polling...")
                self._app.run_polling(drop_pending_updates=True)
            except Exception as e:
                print(f"[TELEGRAM] Bot error: {e}")
                if self._running:
                    print(f"[TELEGRAM] Retrying in {retry_delay}s...")
                    import time as _time
                    _time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 30)
            else:
                retry_delay = 5
        self._running = False

    async def _post_init(self, app):
        print("[TELEGRAM] ✅ Bot connected to Telegram servers")
        if self._user_id:
            try:
                await app.bot.send_message(chat_id=self._user_id, text="SODA Telegram bridge is online ⚡")
                print(f"[TELEGRAM] ✅ Startup message sent to user {self._user_id}")
            except Exception as e:
                print(f"[TELEGRAM] ❌ Startup message failed: {e}")
        else:
            print("[TELEGRAM] ⚠️  No user_id — startup message skipped")

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return
        user_id = update.effective_user.id
        username = update.effective_user.username or "unknown"
        if self._user_id and user_id != self._user_id:
            print(f"[TELEGRAM] 🚫 Unauthorized message from user {user_id} (@{username})")
            await update.message.reply_text("Unauthorized")
            return

        text = update.message.text.strip()
        print(f"[TELEGRAM] ✉️  Received from @{username} ({user_id}): {text[:80]}")

        await update.message.reply_text("🤖 Processing...")

        if self._sio:
            print(f"[TELEGRAM] 📤 Emitting 'telegram_message' event to backend")
            await self._sio.emit('telegram_message', {'text': text, 'from': user_id})
        else:
            print(f"[TELEGRAM] ❌ No Socket.IO connection — message dropped!")

    async def send_message(self, text: str) -> str:
        if not self._app or not self._user_id:
            return "Telegram bot not connected"
        try:
            await self._app.bot.send_message(chat_id=self._user_id, text=text)
            return "Message sent"
        except Exception as e:
            return f"Send failed: {e}"

    async def send_file(self, path: str) -> dict:
        if not self._app or not self._user_id:
            return {"success": False, "result": "Telegram bot not connected"}

        p = Path(path)
        if not p.exists():
            return {"success": False, "result": f"File not found: {path}"}

        # Folders → zip first
        if p.is_dir():
            zip_dir = Path("temp")
            zip_dir.mkdir(exist_ok=True)
            zip_path = zip_dir / f"{p.name}.zip"
            try:
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for f in p.rglob('*'):
                        if f.is_file():
                            zf.write(f, f.relative_to(p))
                p = zip_path
            except Exception as e:
                return {"success": False, "result": f"Failed to zip folder: {e}"}

        # Size check
        max_bytes = 50 * 1024 * 1024
        if p.stat().st_size > max_bytes:
            return {"success": False, "result": f"File too large ({p.stat().st_size / 1024 / 1024:.1f}MB). Max 50MB."}

        try:
            with open(p, 'rb') as f:
                await self._app.bot.send_document(chat_id=self._user_id, document=f, filename=p.name)
            # Clean up temp zip
            if str(p).startswith('temp\\') or str(p).startswith('temp/'):
                p.unlink(missing_ok=True)
            return {"success": True, "result": f"Sent {p.name} to Telegram"}
        except Exception as e:
            return {"success": False, "result": f"Send failed: {e}"}


telegram_bot = TelegramBot()
