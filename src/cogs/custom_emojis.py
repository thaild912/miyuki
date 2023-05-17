import discord
import mysql.connector.errors
import validators
from discord.ext import commands
from src.utils import helper
from src.utils.confirmation_button_view import ConfirmationButtonView, ConfirmationType
import json
import re
from src.miyuki import Client

CONFIRMATION_TIMEOUT = 30.0


class CustomEmojis(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command()
    @commands.is_owner()
    async def importemojisbackup(self, ctx):
        attachments = ctx.message.attachments
        counter = 0
        if len(attachments) != 1:
            await ctx.send("Too many or too few attachment(s).")
            return

        if attachments[0].content_type[:16] != "application/json":
            await ctx.send("Wrong backup file format.")
            return

        try:
            if await attachments[0].save("./temp/backup.json") > 0:
                with open("./temp/backup.json", 'r') as f:
                    data = json.load(f)
                    emojis = data['emojis']

                for guild in emojis:
                    for emoji in emojis[guild]:
                        await self.add_new_emoji(ctx, emoji, int(guild), emojis[guild][emoji], importing_backup=True)
                        counter += 1
                self.client.sqldb.commit()
        except Exception as err:
            raise err
        else:
            await ctx.send(f"Restored {counter} emojis from backup.")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def addemoji(self, ctx, emoji, url):
        if not validators.url(url):
            await helper.error_embed(ctx, "Invalid URL")
        elif len(emoji) > 22:
            await helper.error_embed(ctx, "Emoji name is too long (larger than 20 characters)")
        elif len(re.findall(r'^:\w+:$', emoji)) == 0:
            await helper.error_embed(ctx, "Invalid emoji name format")
        elif not helper.gif_url_checker(url):
            await helper.error_embed(ctx, "Url does not lead to a gif")
        else:
            await self.add_new_emoji(ctx, emoji, ctx.guild.id, url, importing_backup=False)

    async def add_new_emoji(self,
                            ctx: discord.ext.commands.Context,
                            emoji: str,
                            guild_id: int,
                            url: str,
                            importing_backup: bool):
        existing_emoji = get_emoji_urls(self.client, guild_id, [emoji])
        # emojis already in table, UPDATE
        if len(existing_emoji) > 0:
            # not importing backups, requires manual confirmation
            if not importing_backup:
                async def confirm_overwrite():
                    self.overwrite_emoji(emoji=emoji, guild_id=guild_id, url=url, autocommit=True)
                    await embedded_message.edit(embed=await helper.embed_generator(ctx=ctx,
                                                                                   title=f"{emoji} has been successfully overwritten",
                                                                                   img_url=url,
                                                                                   footer=f"by {ctx.author.name}#{ctx.author.discriminator}",
                                                                                   return_embed=True))

                async def reject_overwrite():
                    await embedded_message.edit(embed=await helper.embed_generator(ctx=ctx,
                                                                                   title=f"{emoji} has not been overwritten",
                                                                                   img_url=existing_emoji[0],
                                                                                   return_embed=True))

                confirmation_view = ConfirmationButtonView(ctx.author, ConfirmationType.OVERWRITE,
                                                           confirm_callback=confirm_overwrite,
                                                           reject_callback=reject_overwrite,
                                                           timeout=CONFIRMATION_TIMEOUT)
                embedded_message = await helper.embed_generator(ctx=ctx,
                                                                title=f"An emoji with similar name {emoji} already existed",
                                                                desc=f"Replace {emoji}?",
                                                                img_url=existing_emoji[0],
                                                                footer="Timeout in 30s.",
                                                                view=confirmation_view)
                confirmation_view.message = embedded_message
            else:
                self.overwrite_emoji(emoji=emoji, guild_id=guild_id, url=url, autocommit=not importing_backup)

        else:
            self.insert_emoji(emoji=emoji, guild_id=guild_id, url=url, autocommit=not importing_backup)
            if not importing_backup:
                await helper.embed_generator(ctx=ctx,
                                             title=f"{emoji} has been set as",
                                             img_url=url,
                                             footer=f"by {ctx.author.name}#{ctx.author.discriminator}")

    def overwrite_emoji(self, emoji: str, guild_id: int, url: str, autocommit: bool = False):
        self.client.sql_cursor.execute(f"UPDATE emojis SET url = '{url}' "
                                       f"WHERE guild_id = {guild_id} AND emoji_name = '{emoji}'")
        if autocommit:
            self.client.sqldb.commit()

    def insert_emoji(self, emoji: str, guild_id: int, url: str, autocommit: bool = False):
        self.client.sql_cursor.execute(f"INSERT INTO emojis (emoji_name, guild_id, url) "
                                       f"VALUES ('{emoji}', {guild_id}, '{url}')")
        if autocommit:
            self.client.sqldb.commit()

    def delete_emoji(self, emoji: str, guild_id: int):
        # no need for autocommit since calling this function already requires confirmation
        self.client.sql_cursor.execute(f"DELETE FROM emojis WHERE emoji_name='{emoji}' AND guild_id={guild_id}")
        self.client.sqldb.commit()

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def deleteemoji(self, ctx: discord.ext.commands.Context, emoji: str):
        if len(re.findall(r'^:\w+:$', emoji)) == 0:
            await helper.error_embed(ctx, "Invalid emoji name format")
            return

        existing_emoji = get_emoji_urls(self.client, ctx.guild.id, [emoji])
        if len(existing_emoji) > 0:
            async def confirm_delete():
                self.delete_emoji(emoji, ctx.guild.id)
                await embedded_message.edit(embed=await helper.embed_generator(ctx=ctx,
                                                                               title=f"{emoji} has been successfully deleted",
                                                                               img_url=existing_emoji[0],
                                                                               footer=f"by {ctx.author.name}#{ctx.author.discriminator}",
                                                                               return_embed=True))

            async def reject_delete():
                await embedded_message.edit(embed=await helper.embed_generator(ctx=ctx,
                                                                               title=f"{emoji} has not been deleted",
                                                                               img_url=existing_emoji[0],
                                                                               footer=f"by {ctx.author.name}#{ctx.author.discriminator}",
                                                                               return_embed=True))

            confirmation_view = ConfirmationButtonView(ctx.author, ConfirmationType.DELETE,
                                                       confirm_callback=confirm_delete,
                                                       reject_callback=reject_delete,
                                                       timeout=CONFIRMATION_TIMEOUT)
            embedded_message = await helper.embed_generator(ctx=ctx,
                                                            title=f"Delete {emoji}?",
                                                            img_url=existing_emoji[0],
                                                            footer="Timeout in 30s.",
                                                            view=confirmation_view)
            confirmation_view.message = embedded_message


async def setup(client):
    await client.add_cog(CustomEmojis(client))


def get_emoji_urls(client: Client, guild_id: int, emojis: list[str]):
    emoji_urls = []
    try:
        for emoji in emojis:
            client.sql_cursor.execute(f"SELECT url FROM emojis WHERE emoji_name = '{emoji}' AND guild_id = {guild_id}")
            if client.sql_cursor.rowcount > 0:
                emoji_urls.append(client.sql_cursor.fetchone()[0])
    except mysql.connector.errors.ProgrammingError as err:
        print(err)
        return []
    else:
        return emoji_urls
