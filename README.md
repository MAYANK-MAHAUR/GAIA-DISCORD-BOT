# 🌿 GAIA Discord Bot

> Official bot of the **GAIA Discord server** — packed with moderation features, multiplayer games, and leaderboard support!

---

## 🔧 Features

### 🛡️ Moderation
- `/kick` — Kick a member from the server
- `/ban` — Ban a member permanently
- `/mute` & `/unmute` — Temporarily silence a member
- `/warn` — Warn users (3 warnings = auto-ban)
- `/unban` — Unban by user ID
- `/lockchannel` & `/unlockchannel` — Lock/unlock chat
- `/nickname` — Change a user’s nickname
- `/slowmode` — Add message cooldowns
- `/purge` — Bulk delete messages
- `/role` — Add or remove a role
- 🔒 All actions are **logged** in a mod log channel

---

### 🎮 Games
> Fun & fast-paced games anyone can join!

- **Trivia** — Answer general knowledge questions
- **Scramble** — Unscramble a random word
- **Guess the Number** — Classic number guessing game
- **Lyrics** — Guess the song from a lyric line
- **Emoji Decode** — Decode intuitive emoji puzzles
- **RPS** — Rock Paper Scissors with a twist

All games support:
- ✅ Slash commands
- 🏆 Cross-game leaderboard system
- 🔁 Looping with auto-timeouts and hints

---

### 🏆 Leaderboard System
- Shared across all games
- Max 10 recent winners per game
- Auto-reset after full leaderboard
- `/resetfinalleaderboard` & `/resetsecleaderboard`

---

## 🚀 Tech Stack

- **Language**: Python 3.11+
- **Library**: [discord.py v2.5.2](https://pypi.org/project/discord.py/)
- **Hosting**: Railway (24/7 free bot hosting)
- **Storage**: JSON files (for leaderboard, questions, etc.)
- **Structure**: Fully modular Cogs (`cogs/` folder)

---

## 📦 Installation

```bash
git clone https://github.com/YOUR_USERNAME/gaia-bot.git
cd gaia-bot
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
