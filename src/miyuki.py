import os
import discord
from discord.ext import commands
from src.utils.helper import open_sql_connection


class Client(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=["!"],
            intents=discord.Intents.all(),
            help_command=commands.DefaultHelpCommand(dm_help=True)
        )
        if not discord.opus.is_loaded() and os.name != 'nt':
            # the 'opus' library here is opus.dll on windows
            # or libopus.so on linux in the current directory
            # you should replace this with the location the
            # opus library is located in and with the proper filename.
            # note that on windows this DLL is automatically provided for you
            discord.opus.load_opus('libopus.so.0')

    async def setup_hook(self):  # overwriting a handler
        print(f"\033[31mLogged in as {client.user}\033[39m")
        # loads cogs
        cogs_folder = f"{os.path.abspath(os.path.dirname(__file__))}/cogs"
        for filename in os.listdir(cogs_folder):
            if filename.endswith(".py"):
                await client.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded cog: {filename[:-3]}")
        # await client.tree.sync()

        # setup mysql db
        sqldb, sql_cursor = open_sql_connection(init=True)
        sql_cursor.execute("CREATE DATABASE IF NOT EXISTS discord")
        sql_cursor.execute("USE discord")
        sql_cursor.execute("CREATE TABLE IF NOT EXISTS emojis (id INT AUTO_INCREMENT PRIMARY KEY, "
                           "emoji_name VARCHAR(22) NOT NULL, "
                           "guild_id BIGINT NOT NULL, "
                           "url VARCHAR(225) NOT NULL)")
        sqldb.close()


if __name__ == '__main__':
    client = Client()
    client.run(os.getenv('DISCORD_TOKEN'))
