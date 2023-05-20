import discord
from discord.ext import commands
import validators
import src.utils.helper as helper
import ffmpeg


class UtilityCog(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command()
    async def sendvideo(self, ctx: discord.ext.commands.Context, url: str):
        if validators.url(url):
            if helper.is_supported(url):
                await helper.reply_with_video(ctx, url, notify_error=True)


async def setup(client):
    await client.add_cog(UtilityCog(client))
