# 🏀 Baller Memes Moderation Bot

A highly configurable Discord moderation bot with advanced features and a clean cogs structure.

## ✨ Features

### 🛡️ Moderation
- **Comprehensive Moderation Commands**: Ban, kick, mute, warn, purge, and more
- **Advanced Automoderation**: Spam detection, raid protection, invite filtering
- **Temporary Actions**: Temporary bans, mutes with automatic removal
- **Moderation Logging**: Detailed logs of all moderation actions
- **Warning System**: Configurable warning thresholds and automatic actions

### ⚙️ Configuration
- **Per-Guild Settings**: Customizable prefix, roles, channels per server
- **Flexible Permissions**: Role-based command access control
- **Automod Settings**: Toggle various automoderation features
- **Logging Options**: Choose what events to log

### 🎯 Advanced Features
- **Slash Commands**: Modern Discord slash command support
- **Hybrid Commands**: Both slash and text commands available
- **Database Integration**: Persistent data storage
- **Cogs Structure**: Organized, modular code architecture
- **Error Handling**: Comprehensive error handling and logging

## 📁 Project Structure

```
baller-memes-mod-bot/
├── bot.py              # Main bot file
├── config.json         # Bot configuration
├── requirements.txt    # Python dependencies
├── cogs/              # Bot cogs (modules)
│   ├── moderation.py  # Moderation commands
│   ├── automod.py     # Automatic moderation
│   ├── logging.py     # Event logging
│   ├── config.py      # Configuration commands
│   ├── utility.py     # Utility commands
│   └── owner.py       # Owner-only commands
├── utils/             # Utility modules
│   ├── database.py    # Database operations
│   ├── checks.py      # Custom permission checks
│   └── helpers.py     # Helper functions
└── data/              # Data storage
    └── moderation.db  # SQLite database
```

## 🚀 Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/aurora9161/baller-memes-mod-bot.git
   cd baller-memes-mod-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the bot**
   - Edit `config.json` and add your bot token
   - Customize other settings as needed

4. **Run the bot**
   ```bash
   python bot.py
   ```

## ⚡ Quick Configuration

### Bot Token
Replace `YOUR_BOT_TOKEN_HERE` in `config.json` with your actual bot token.

### Basic Settings
- `default_prefix`: Default command prefix (default: `!`)
- `owner_ids`: List of Discord user IDs with owner permissions
- `embed_color`: Color for bot embeds (RGB decimal)

### Moderation Settings
- `auto_dehoist`: Remove special characters from usernames
- `spam_detection`: Enable spam detection and prevention
- `raid_protection`: Enable raid protection measures
- `max_mentions`: Maximum mentions allowed per message

## 🎮 Commands

### Moderation Commands
- `/ban <user> [reason]` - Ban a user
- `/kick <user> [reason]` - Kick a user
- `/mute <user> [duration] [reason]` - Mute a user
- `/warn <user> [reason]` - Warn a user
- `/purge <amount>` - Delete messages
- `/slowmode <seconds>` - Set channel slowmode

### Configuration Commands
- `/config prefix <new_prefix>` - Change server prefix
- `/config modrole <role>` - Set moderator role
- `/config logchannel <channel>` - Set log channel
- `/config automod <setting> <value>` - Configure automod

### Utility Commands
- `/userinfo <user>` - Get user information
- `/serverinfo` - Get server information
- `/help` - Show help menu

## 🔧 Customization

The bot is designed to be highly customizable:

1. **Add new cogs**: Create new `.py` files in the `cogs/` directory
2. **Modify settings**: Edit `config.json` for global settings
3. **Database changes**: Modify `utils/database.py` for data structure changes
4. **Custom checks**: Add permission checks in `utils/checks.py`

## 🐛 Troubleshooting

- Check `bot.log` for error messages
- Ensure the bot has necessary permissions in your server
- Verify your bot token is correct
- Make sure Python 3.8+ is installed

## 📝 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

**Made with ❤️ for the Discord community**