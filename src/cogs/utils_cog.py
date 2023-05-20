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

    @commands.command()
    async def t(self, ctx):
        probe = ffmpeg.probe('./temp/temp_video_compressed.mp4')
        video = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        print(video)

async def setup(client):
    await client.add_cog(UtilityCog(client))
