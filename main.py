import asyncio
from ircbot import SimpleIRCBot
from oi import ChatInterpreter

if __name__ == '__main__':

    interpreter = ChatInterpreter()

    bot = SimpleIRCBot(interpreter=interpreter)

    try:
        # Run the bot within the asyncio event loop
        asyncio.run(bot.start())
    except Exception as e:
        print(f"Bot encountered an error: {e}")
