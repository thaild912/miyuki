import asyncio
from src.utils import helper
from src.utils.navigation_button_view import NavigationButtonView
import discord
from discord.ext import tasks, commands
from src.utils.ytdlsource import YTDLSource, playlist_parse


class AudioPlayer(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.event_loop = None
        self.queue = {}
        self.loop = {}
        self.stop_task.start()

    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""
        await self.stop_guild_id(ctx.guild.id)

    async def stop_guild_id(self, guild_id):
        voice_client = self.client.get_guild(int(guild_id)).voice_client
        if voice_client is not None:
            await voice_client.disconnect()
            self.queue[str(guild_id)] = []
            self.loop[str(guild_id)] = False

    @commands.command(aliases=['pley', 'Play', 'PLAY', 'plya'])
    async def play(self, ctx, *, url, added_options=""):
        """Streams from an url (same as yt, but doesn't predownload)"""
        if not str(ctx.guild.id) in self.queue:
            self.queue[str(ctx.guild.id)] = []
            self.loop[str(ctx.guild.id)] = False

        self.client.loop.create_task(
            playlist_parse(url, loop=self.client.loop, stream=True, queue=self.queue[str(ctx.guild.id)],
                           added_options=added_options))
        await asyncio.sleep(0.01)

        # or paused
        if not (ctx.voice_client.is_playing()):
            self.play_queue(ctx)

    @commands.command()
    async def loop(self, ctx):
        self.loop[str(ctx.guild.id)] = not self.loop[str(ctx.guild.id)]

    @commands.command()
    async def skip(self, ctx):
        ctx.voice_client.stop()
        if len(self.queue[str(ctx.guild.id)]) == 0:
            await self.stop(ctx)

    @commands.command()
    async def seek(self, ctx, arg):
        time_list = list(map(int, arg.split(":")))[::-1]
        time_s = sum([time_list[i] * (60 ** i) for i in range(len(time_list))])
        data = self.queue[str(ctx.guild.id)][0].data
        seeked_song = await YTDLSource.from_url(data, loop=self.client.loop, stream=True, queue=None,
                                                added_options=f' -ss {time_s}')
        self.queue[str(ctx.guild.id)].insert(1, seeked_song)
        await self.skip(ctx)

    @commands.command()
    async def queue(self, ctx):
        current_page = 0

        async def prev_callback_func():
            nonlocal current_page
            current_page -= 1
            # first page reached
            if current_page < 0:
                current_page = 0
            await generate_queue_embed()
            return current_page > 0, current_page < len(self.queue[str(ctx.guild.id)]) // 10

        async def next_callback_func():
            nonlocal current_page
            current_page += 1
            # last page reached
            if current_page > len(self.queue[str(ctx.guild.id)]) // 10:
                current_page = len(self.queue[str(ctx.guild.id)]) // 10
            await generate_queue_embed()
            return current_page > 0, current_page < len(self.queue[str(ctx.guild.id)]) // 10

        async def generate_queue_embed(return_embed: bool = False):
            embed = await helper.embed_generator(ctx,
                                                 title=f"Currently playing: {self.queue[str(ctx.guild.id)][0].data['title']}",
                                                 url=self.queue[str(ctx.guild.id)][0].data['webpage_url'],
                                                 img_url=self.queue[str(ctx.guild.id)][0].data['thumbnail'],
                                                 footer=f"Page {current_page + 1}/{len(self.queue[str(ctx.guild.id)]) // 10 + 1}",
                                                 return_embed=True)
            # loop till 10 songs, or reached the end of the queue
            for i in range(current_page * 10, min(((current_page + 1) * 10), len(self.queue[str(ctx.guild.id)]))):
                embed.add_field(name="\u200b",
                                value=f"**{i+1}. [{self.queue[str(ctx.guild.id)][i].data['title']}]({self.queue[str(ctx.guild.id)][i].data['webpage_url']})**",
                                inline=False)
            if return_embed:
                return embed
            else:
                await embedded_message.edit(embed=embed)

        navigation_view = NavigationButtonView(prev_callback=prev_callback_func, next_callback=next_callback_func,
                                               timeout=60.0)
        embedded_message = await ctx.channel.send(embed=await generate_queue_embed(return_embed=True),
                                                  view=navigation_view)
        navigation_view.message = embedded_message

    @play.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")

    def play_queue(self, ctx):
        if len(self.queue[str(ctx.guild.id)]) == 0:
            return
        player = self.queue[str(ctx.guild.id)][0]

        def after_play(e):
            if e:
                print('Player error: %s' % e)
            else:
                if not self.loop[str(ctx.guild.id)]:
                    try:
                        self.queue[str(ctx.guild.id)].pop(0)
                    except IndexError:
                        pass
                self.play_queue(ctx)

        ctx.voice_client.play(player, after=lambda e: after_play(e))
        embed = discord.Embed(color=discord.Color.blue(), title=f"Now playing: {player.data['title']}",
                              url=player.data['url'])
        embed.set_image(url=player.data['thumbnail'])
        asyncio.run_coroutine_threadsafe(ctx.send(embed=embed), ctx.bot.loop)

    @tasks.loop(minutes=5.0)
    async def stop_task(self):
        for guild_id in self.queue:
            if len(self.queue[guild_id]) == 0:
                await self.stop_guild_id(guild_id)


async def setup(client: discord.Client):
    await client.add_cog(AudioPlayer(client))
