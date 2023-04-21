from src.bot import GuessTheSongBot
from config import BOT_TOKEN
import discord

if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True
    bot = discord.Bot(intents=intents)

    bot.add_cog(GuessTheSongBot(bot))
    bot.run(BOT_TOKEN)
