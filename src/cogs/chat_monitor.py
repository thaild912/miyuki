import discord
from discord.ext import commands
from src.utils import helper
from urlextract import URLExtract
from src.cogs.custom_emojis import get_emoji_urls


class ChatMonitor(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.url_extractor = URLExtract()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # only check messages from human
        if message.author.bot:
            return

        # excludes commands
        ctx = await self.client.get_context(message)
        if ctx.valid:
            return

        # FB downloader
        urls = self.url_extractor.find_urls(message.content)
        if len(urls) > 0:
            ctx = None
            for url in urls:
                if helper.is_fb_video(url):
                    if ctx is None:
                        ctx = await self.client.get_context(message)
                    await helper.reply_with_video(ctx, url)

        # emoji uploader
        emojis = helper.has_emoji(message)
        if len(emojis) > 0:
            emojis_urls = get_emoji_urls(message.guild.id, emojis)
            for emoji_url in emojis_urls:
                await message.channel.send(emoji_url)


async def setup(client: discord.Client):
    await client.add_cog(ChatMonitor(client))
