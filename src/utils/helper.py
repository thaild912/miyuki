import asyncio
import datetime
import functools
import requests
import yt_dlp
import validators
import ffmpeg
import re
import discord
import os
from typing import Tuple, Union, Callable, Coroutine
import mysql.connector
from mysql.connector import MySQLConnection
from mysql.connector.cursor import MySQLCursor
from mysql.connector.pooling import PooledMySQLConnection

MAX_VIDEO_UPLOAD_SIZE_MB = 10
MAX_SEND_VIDEO_DURATION = 300


def to_thread(func: Callable) -> Coroutine:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        return await asyncio.to_thread(func, *args, **kwargs)

    return wrapper


def is_supported(url: str) -> bool:
    extractors = yt_dlp.extractor.gen_extractors()
    for e in extractors:
        if e.suitable(url) and e.IE_NAME != 'generic':
            return True
    return False


def to_playable(query: str):
    if validators.url(query):
        if is_supported(query) or query[:-4] in ['.mp3', '.wav', '.ogg']:
            pass
    pass


def is_fb_video(url: str) -> bool:
    if validators.url(url):
        # is supported doesn't catch all facebook cases
        if ('fb.watch' in url or 'facebook' in url) or (is_supported(url) and ('fb.watch' in url or 'facebook' in url)):
            if url.find('facebook') or url.find('fb'):
                return True

    return False


def get_video_length(url: str) -> None | int:
    extractor_opts = {
        'ignoreerrors': False,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'playlist_items': f'1-1',
        'source_address': '0.0.0.0'
    }
    with yt_dlp.YoutubeDL(extractor_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if 'duration' in info:
            return info['duration']
        return None


@to_thread
def download_video(url: str) -> bool:
    ydl_opts_sep = {
        'format': 'bestvideo[ext=mp4]+worstaudio[ext=m4a]/best[ext=mp4]/best',
        'quiet': True,
        # 'verbose': True,
        'nooverwrites': False,
        "geo_bypass": True,
        'merge_output_format': 'mp4',
        'outtmpl': f'./temp/temp_video.%(ext)s'
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts_sep) as ydl:
            ydl.download(url)
    except yt_dlp.DownloadError as error:
        return False
    except Exception as error:
        print(error)
        return False
    else:
        return True


@to_thread
def compress_video(video_full_path: str, output_file_name: str, target_size: int):
    # Reference: https://stackoverflow.com/questions/64430805/how-to-compress-video-to-target-size-by-python
    # Reference: https://en.wikipedia.org/wiki/Bit_rate#Encoding_bit_rate
    probe = ffmpeg.probe(video_full_path)
    # Video duration, in s.
    duration = float(probe['format']['duration'])
    # Audio bitrate, in bps.
    audio_bitrate = float(next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)['bit_rate'])
    # Target total bitrate, in bps.
    target_total_bitrate = (target_size * 1024 * 8) / (1.073741824 * duration)

    audio_bitrate = 32000
    # Target video bitrate, in bps.
    video_bitrate = target_total_bitrate - audio_bitrate

    i = ffmpeg.input(video_full_path)
    ffmpeg.output(i, os.devnull,
                  **{'c:v': 'libx264', 'b:v': video_bitrate, 'pass': 1, 'f': 'mp4'}
                  ).overwrite_output().global_args('-loglevel', 'error').run()
    ffmpeg.output(i, output_file_name,
                  **{'c:v': 'libx264', 'b:v': video_bitrate, 'pass': 2, 'c:a': 'aac', 'b:a': audio_bitrate}
                  ).overwrite_output().global_args('-loglevel', 'error').run()


async def reply_with_video(ctx: discord.ext.commands.Context, url: str, notify_error: bool = False):
    await ctx.message.edit(suppress=True)
    if get_video_length(url) is None or get_video_length(url) > MAX_SEND_VIDEO_DURATION:
        if notify_error:
            await embed_generator(ctx, color=discord.Color.red(),
                                  title=f"Video requested is longer than {MAX_SEND_VIDEO_DURATION} seconds or invalid",
                                  reply=True)
        return
    downloaded = await download_video(url)
    if not downloaded:
        return

    reply = await ctx.message.reply(content="Please wait a moment...")
    size = os.path.getsize("./temp/temp_video.mp4")
    probe = ffmpeg.probe('./temp/temp_video.mp4')
    video_metadata = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)

    print(video_metadata["codec_name"])
    if video_metadata["codec_name"] in ["h264", "vp9"]:
        try:
            await reply.edit(content=None, attachments=[discord.File("./temp/temp_video.mp4")])
            return
        except discord.errors.HTTPException as err:
            if err.text == "Request entity too large":
                pass
            else:
                return

    # needs compression
    await reply.edit(content="Compressing...")
    await compress_video('./temp/temp_video.mp4', './temp/temp_video_compressed.mp4',
                         MAX_VIDEO_UPLOAD_SIZE_MB * 1000)
    await reply.edit(content=None, attachments=[discord.File("./temp/temp_video_compressed.mp4")])


def has_emoji(msg: discord.Message) -> list[str]:
    emojis = re.findall(r':\w+:', msg.content)
    return emojis


async def embed_generator(ctx,
                          color: int | discord.Color = discord.Color.blue(),
                          title: str = None,
                          desc: str = None,
                          url: str = None,
                          img_url: str = None,
                          footer: str = None,
                          reactions: list = None,
                          timestamp: datetime.datetime = None,
                          view: discord.ui.View = None,
                          reply: bool = False,
                          return_embed: bool = False) -> Union[None, discord.Embed, discord.Message]:
    embed = discord.Embed(color=color, title=title, description=desc, url=url, timestamp=timestamp)
    if img_url is not None:
        embed.set_image(url=img_url)
    if footer is not None:
        embed.set_footer(text=footer)

    if return_embed:
        return embed

    if not reply:
        embed_msg = await ctx.send(embed=embed, view=view)
    else:
        embed_msg = await ctx.message.reply(embed=embed, view=view)

    if reactions is not None:
        for reaction in reactions:
            await embed_msg.add_reaction(reaction)

    return embed_msg


async def error_embed(ctx: discord.ext.commands.Context, content: str):
    # generates embedded error message
    await ctx.message.reply(embed=embed_generator(ctx, color=discord.Color.red(), title=content))


def gif_url_checker(url: str) -> bool:
    r = requests.head(url)
    if r.headers["content-type"] == "image/gif":
        return True
    return False


def open_sql_connection(init: bool = False) -> Tuple[PooledMySQLConnection | MySQLConnection, MySQLCursor]:
    sqldb = mysql.connector.connect(
        host="localhost",
        user=str(os.getenv('MYSQL_USER')),
        password=str(os.getenv('MYSQL_PASSWORD')),
    )
    if not init:
        sqldb.connect(database="discord")

    return sqldb, sqldb.cursor(buffered=True)


def close_sql_connection(sqldb: PooledMySQLConnection | MySQLConnection, sql_cursor: MySQLCursor):
    sql_cursor.close()
    sqldb.close()


def sql_query(query: str):
    try:
        sqldb, sql_cursor = open_sql_connection()
        sql_cursor.execute(query)
    except mysql.connector.errors.Error:
        raise
    else:
        sqldb.commit()
    finally:
        close_sql_connection(sqldb, sql_cursor)
