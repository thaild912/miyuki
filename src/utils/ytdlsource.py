import discord
import asyncio
import yt_dlp

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': False,
    'playlist_items': f'69-{69}',
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
}

ytdlp = yt_dlp.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, data, *, loop=None, stream=False, queue: list = None, added_options=""):
        filename = data['url'] if stream else ytdlp.prepare_filename(data)
        local_ffmpeg_options = ffmpeg_options.copy()
        local_ffmpeg_options['before_options'] += added_options
        if queue is not None:
            # queue exists, add player to queue
            queue.append(cls(discord.FFmpegPCMAudio(filename, **local_ffmpeg_options), data=data))
        else:
            # get song only
            return cls(discord.FFmpegPCMAudio(filename, **local_ffmpeg_options), data=data)


async def playlist_parse(url: str, loop, stream, queue, added_options=""):

    for i in range(1, 101):
        temp_ytdl_format_options = ytdl_format_options.copy()
        temp_ytdl_format_options['playlist_items'] = f'{i}-{i}'
        temp_extractor = yt_dlp.YoutubeDL(temp_ytdl_format_options)
        data = temp_extractor.extract_info(url, download=False)
        if 'entries' in data:
            if len(data['entries']) == 0:
                break
            data = data['entries'][0]
            await YTDLSource.from_url(data=data, loop=loop, stream=stream, queue=queue, added_options=added_options)
            await asyncio.sleep(0.01)
        else:
            await YTDLSource.from_url(data=data, loop=loop, stream=stream, queue=queue, added_options=added_options)
            break
