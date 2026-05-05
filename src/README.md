# Nudge Bot — Anonymous Gentle Reminders

A zero-account, zero-database Telegram bot that sends anonymous reminders.

## Quick Start (Local)

```bash
# 1. Get a bot token from @BotFather in Telegram
# 2. Set the token
export BOT_TOKEN="123456:ABC-DEF..."

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python bot.py
```

## Usage

```
/nudge @username Your reminder message here
```

The target user receives:
```
🕊️ Anonymous Reminder

_Don't forget our call at 3pm!_
```

They do NOT see who sent it.

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message + usage |
| `/help` | Same as /start |
| `/nudge @username text` | Send anonymous reminder |

## Deploy on Railway

1. Create account at [railway.app](https://railway.app)
2. Connect your GitHub repo
3. Add environment variable: `BOT_TOKEN` = your token from @BotFather
4. Deploy — Railway auto-detects Python and runs `web: python bot.py`

## Deploy on Render

1. Create account at [render.com](https://render.com)
2. Create a **Web Service** from your repo
3. Set:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
4. Add environment variable: `BOT_TOKEN`
5. Deploy

## Get Your Bot Token

1. Open Telegram and chat with **@BotFather**
2. Send `/newbot`
3. Follow prompts, give it a name + username
4. Copy the token it gives you (looks like `123456789:AAFhPiXq...`)
5. Keep it secret — don't share publicly

## MVP Notes

- No database or user accounts
- In-memory session tracking (resets on restart)
- Free tier on Railway/Render is sufficient for MVP
- Bot must be started by target user before sending nudges (Telegram requirement)