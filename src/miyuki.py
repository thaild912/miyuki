import os
import discord
from discord.ext import tasks, commands
import mysql.connector


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

        def init_sql_connection():
            sqldb = mysql.connector.connect(
                host="localhost",
                user=str(os.getenv('MYSQL_USER')),
                password=str(os.getenv('MYSQL_PASSWORD'))
            )

            return sqldb, sqldb.cursor(buffered=True)

        self.init_sql_connection = init_sql_connection
        self.sqldb = None
        self.sql_cursor = None

    async def setup_hook(self):  # overwriting a handler
        print(f"\033[31mLogged in as {client.user}\033[39m")
        # loads cogs
        cogs_folder = f"{os.path.abspath(os.path.dirname(__file__))}/cogs"
        for filename in os.listdir(cogs_folder):
            if filename.endswith(".py"):
                await client.load_extension(f"cogs.{filename[:-3]}")
                print(f"Loaded cog: {filename[:-3]}")
        # await client.tree.sync()

        # connect to sql db
        self.sqldb, self.sql_cursor = self.init_sql_connection()
        self.sql_cursor.execute("CREATE DATABASE IF NOT EXISTS discord")
        self.sql_cursor.execute("USE discord")
        self.sql_cursor.execute("CREATE TABLE IF NOT EXISTS emojis (id INT AUTO_INCREMENT PRIMARY KEY, "
                                "emoji_name VARCHAR(22) NOT NULL, "
                                "guild_id BIGINT NOT NULL, "
                                "url VARCHAR(225) NOT NULL)")
        self.sqldb.commit()
        print("MySQL database connected")


if __name__ == '__main__':
    client = Client()
    client.run(os.getenv('DEBUG_DISCORD_TOKEN'))
