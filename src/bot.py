#!/usr/bin/env python3
"""
Nudge MVP — Anonymous gentle reminder bot for Telegram.
Beautiful inline keyboard UI, no accounts, no database.
"""

import os
import re
import logging
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ─── Config ────────────────────────────────────────────────────────────────────

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# ─── State Machine ──────────────────────────────────────────────────────────────
# user_id -> state: "idle" | "waiting_username" | "waiting_reminder"
_state: dict[int, str] = {}

# pending nudge data: user_id -> {"username": str}
_pending: dict[int, dict] = {}

# ─── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Helpers ───────────────────────────────────────────────────────────────────

def extract_mention(text: str) -> Optional[str]:
    """Extract @username from plain text."""
    m = re.search(r"@(\w+)", text)
    return m.group(1) if m else None


def state_reset(user_id: int) -> None:
    _state.pop(user_id, None)
    _pending.pop(user_id, None)


# ─── Keyboard Builders ──────────────────────────────────────────────────────────

def start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Send Reminder", callback_data="start_reminder")],
        [InlineKeyboardButton("📖 Help", callback_data="show_help")],
        [InlineKeyboardButton("❤️ About", callback_data="show_about")],
    ])


def help_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 Send Reminder", callback_data="start_reminder")],
        [InlineKeyboardButton("❤️ About", callback_data="show_about")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")],
    ])


def about_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 Send Reminder", callback_data="start_reminder")],
        [InlineKeyboardButton("📖 Help", callback_data="show_help")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_start")],
    ])


def success_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔔 Send Another", callback_data="start_reminder")],
        [InlineKeyboardButton("📤 Share Bot", callback_data="share_bot")],
        [InlineKeyboardButton("📖 Help", callback_data="show_help")],
    ])


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data="back_to_start")],
    ])


# ─── Message Builders ───────────────────────────────────────────────────────────

def welcome_message() -> tuple[str, InlineKeyboardMarkup]:
    text = (
        "<b>🕊️ Nudge Bot</b>\n"
        "<i>Anonymous reminders, zero friction.</i>\n\n"
        "─────────────────────\n"
        "Send a gentle anonymous reminder to any Telegram user — "
        "no accounts, no database, just privacy-first nudges.\n"
        "─────────────────────"
    )
    return text, start_keyboard()


def help_message() -> tuple[str, InlineKeyboardMarkup]:
    text = (
        "<b>📖 How It Works</b>\n\n"
        "<i>Step 1:</i> Press <b>➕ Send Reminder</b>\n"
        "<i>Step 2:</i> Enter the @username of the person\n"
        "<i>Step 3:</i> Send your reminder message\n"
        "<i>Step 4:</i> I'll deliver it anonymously ✨\n\n"
        "─────────────────────\n"
        "<b>Commands:</b>\n"
        "• <code>/start</code> — Show menu\n"
        "• <code>/nudge @user message</code> — Quick nudge\n"
        "• <code>/cancel</code> — Cancel current flow\n"
        "─────────────────────"
    )
    return text, help_keyboard()


def about_message() -> tuple[str, InlineKeyboardMarkup]:
    text = (
        "<b>❤️ About Nudge</b>\n\n"
        "🕊️ <i>Nudge Bot</i> lets you send anonymous reminders "
        "to anyone on Telegram — no sign-up, no tracking, no database.\n\n"
        "🔒 <b>Privacy-first:</b> We store nothing.\n"
        "⚡ <b>Fast:</b> One-tap reminder flow.\n"
        "🔗 <b>Anonymous:</b> The recipient won't see your identity.\n\n"
        "─────────────────────"
    )
    return text, about_keyboard()


def ask_username_message() -> tuple[str, InlineKeyboardMarkup]:
    text = (
        "<b>🔔 New Reminder</b>\n\n"
        "👤 <i>Who do you want to remind?</i>\n\n"
        "Send me the @username (e.g. <code>@johndoe</code>)\n"
        "─────────────────────"
    )
    return text, cancel_keyboard()


def ask_reminder_message(username: str) -> tuple[str, InlineKeyboardMarkup]:
    text = (
        f"<b>✏️ Reminder for @{username}</b>\n\n"
        "💬 <i>What should I tell them?</i>\n\n"
        "Send the reminder text you want to deliver anonymously.\n"
        "─────────────────────"
    )
    return text, cancel_keyboard()


def success_message(username: str) -> tuple[str, InlineKeyboardMarkup]:
    text = (
        f"<b>✅ Sent!</b>\n\n"
        f"🕊️ Your anonymous reminder has been delivered to <b>@{username}</b>.\n\n"
        "They won't know it was you — pure gentle nudge! 🌿\n"
        "─────────────────────"
    )
    return text, success_keyboard()


def error_no_user(username: str) -> tuple[str, InlineKeyboardMarkup]:
    text = (
        f"<b>❌ User Not Found</b>\n\n"
        f"⚠️ Could not find Telegram user <b>@{username}</b>.\n\n"
        "Make sure:\n"
        "• The username is correct\n"
        "• The user has started at least one bot on Telegram\n\n"
        "─────────────────────"
    )
    return text, cancel_keyboard()


# ─── Callback Query Handlers ───────────────────────────────────────────────────

async def cb_back_to_start(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    state_reset(query.from_user.id)
    text, keyboard = welcome_message()
    await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


async def cb_show_help(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    text, keyboard = help_message()
    await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


async def cb_show_about(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    text, keyboard = about_message()
    await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


async def cb_start_reminder(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    state_reset(query.from_user.id)
    _state[query.from_user.id] = "waiting_username"
    text, keyboard = ask_username_message()
    await query.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


async def cb_share_bot(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "<b>📤 Share Nudge Bot</b>\n\n"
        "🔗 Invite your friends to use Nudge!\n\n"
        "👉 <a href=\"https://t.me/NudgeAIBot\">@NudgeAIBot</a>\n\n"
        "─────────────────────"
    )
    await query.message.edit_text(text, reply_markup=help_keyboard(), parse_mode="HTML")


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route callback queries to specific handlers."""
    query = update.callback_query
    if not query:
        return

    await query.answer()
    data = query.data or ""

    if data == "back_to_start":
        await cb_back_to_start(query, context)
    elif data == "show_help":
        await cb_show_help(query, context)
    elif data == "show_about":
        await cb_show_about(query, context)
    elif data == "start_reminder":
        await cb_start_reminder(query, context)
    elif data == "share_bot":
        await cb_share_bot(query, context)


# ─── Command Handlers ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state_reset(update.message.from_user.id)
    text, keyboard = welcome_message()
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state_reset(update.message.from_user.id)
    text, keyboard = help_message()
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    state_reset(user_id)
    text = "<b>❌ Cancelled.</b> You're back to the main menu."
    await update.message.reply_text(text, reply_markup=start_keyboard(), parse_mode="HTML")


# ─── Reminder Send Logic ────────────────────────────────────────────────────────

async def send_nudge(
    target_username: str,
    reminder_text: str,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Resolve username and send anonymous nudge."""
    try:
        chat = await context.bot.get_chat(f"@{target_username}")
    except Exception as e:
        logger.warning("Could not resolve @%s: %s", target_username, e)
        text, keyboard = error_no_user(target_username)
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
        return

    target_id = chat.id
    sender_name = update.effective_user.full_name if update.effective_user else "Someone"
    sender_id = update.effective_user.id if update.effective_user else 0

    anonymous_text = (
        "🕊️ <b>Anonymous Reminder</b>\n\n"
        f"<i>{reminder_text}</i>\n\n"
        "— Sent via @NudgeAIBot"
    )

    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=anonymous_text,
            parse_mode="HTML",
        )
        text, keyboard = success_message(target_username)
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
        logger.info(
            "Nudge sent from %d (%s) → @%s (%d): %s",
            sender_id, sender_name, target_username, target_id, reminder_text,
        )
    except Exception as e:
        logger.error("Failed to send nudge to @%s: %s", target_username, e)
        await update.message.reply_text(
            f"❌ Failed to send reminder to <b>@{target_username}</b>.\n"
            "They may have blocked the bot.",
            parse_mode="HTML",
        )


# ─── Message Handlers ──────────────────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route incoming text based on current state machine state."""
    user_id = update.message.from_user.id
    text = (update.message.text or "").strip()

    # Ignore commands (they are handled separately)
    if text.startswith("/"):
        return

    state = _state.get(user_id, "idle")

    if state == "waiting_username":
        username = extract_mention(text)
        if not username:
            await update.message.reply_text(
                "⚠️ Please send a valid @username (e.g. <code>@johndoe</code>)",
                parse_mode="HTML",
            )
            return

        _state[user_id] = "waiting_reminder"
        _pending[user_id] = {"username": username}
        msg_text, keyboard = ask_reminder_message(username)
        await update.message.reply_text(msg_text, reply_markup=keyboard, parse_mode="HTML")
        return

    if state == "waiting_reminder":
        username = _pending.get(user_id, {}).get("username")
        if not username:
            # Shouldn't happen, but reset gracefully
            state_reset(user_id)
            await update.message.reply_text(
                "⚠️ Session expired. Please start again.",
                reply_markup=start_keyboard(),
                parse_mode="HTML",
            )
            return

        if not text:
            await update.message.reply_text(
                "⚠️ Please send a non-empty reminder message.",
                parse_mode="HTML",
            )
            return

        state_reset(user_id)
        await send_nudge(username, text, update, context)
        return

    # idle — check for @mentions as fallback nudge shortcut
    mention = extract_mention(text)
    if mention:
        # Quick nudge flow via /nudge prefix (optional — keep plain text path)
        await update.message.reply_text(
            f"💡 To send a reminder to <b>@{mention}</b>, press the button below:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    f"🔔 Remind @{mention}",
                    callback_data=f"quick_nudge_{mention}",
                )],
                [InlineKeyboardButton("🔙 Cancel", callback_data="back_to_start")],
            ]),
            parse_mode="HTML",
        )
        return

    # Fallback
    await update.message.reply_text(
        "🤔 Press a button below to get started:",
        reply_markup=start_keyboard(),
        parse_mode="HTML",
    )


# ─── Error Handler ─────────────────────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update: %s", context.error)


# ─── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN environment variable is not set.\n"
            "Create a bot via @BotFather and set BOT_TOKEN."
        )

    app = Application.builder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("cancel", cmd_cancel))

    # Callback queries (MUST be before text handler)
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Error handler
    app.add_error_handler(error_handler)

    logger.info("Nudge bot starting with inline keyboard UI...")
    app.run_polling()


if __name__ == "__main__":
    main()