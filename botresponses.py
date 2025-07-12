# --- General Response ---
HELLO_MESSAGE = "Hello there! How can I help you today? 😊"
GOODBYE_MESSAGE = "Goodbye! Hope to see you soon! 👋"
ERROR_GENERIC = "Oops! Something went wrong. Please try again later. 😔"
NO_PERMISSION = "Sorry, you don't have the required permissions to use this command. 🚫"

# --- GaiaNet AI Response ---
GAIANET_LOADING = "Just a moment......"
GAIANET_ERROR = "I'm having trouble connecting to the GaiaNet AI right now. Please check the API status or try again later. 🚧"
GAIANET_NO_QUESTION_MENTION_REPLY = "Hey! Please ask me a question after mentioning me or in your reply. For example: `@YourBot What is the capital of France?`"
GAIANET_NO_QUESTION_COMMAND = "Please provide a question for the GaiaNet AI. Example: `!askgaia What is blockchain?`"


# --- Fun Response ---
PONG_MESSAGE = "Pong! 🏓"
FLIP_COIN_HEADS = "It's **Heads**! 🪙"
FLIP_COIN_TAILS = "It's **Tails**! 🪙"

def command_help_message(command_prefix: str) -> str:
    return (
        f"Here are some commands you can use:\n"
        f"`{command_prefix}askgaia <question>` - Ask the GaiaNet AI a question.\n"
        f"`@{command_prefix.strip()} <question>` - Ask the GaiaNet AI by mentioning me.\n"
        f"`{command_prefix}hello` - Get a friendly greeting.\n"
        f"`{command_prefix}ping` - Check if the bot is alive.\n"
        f"`{command_prefix}coinflip` - Flip a coin."
    )
