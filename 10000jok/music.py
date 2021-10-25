from discord import client
from discord.ext import commands
import discord
import asyncio
import youtube_dl
import logging
from video import Video

#ตั้งค่า FFmpeg
FFMPEG_BEFORE_OPTS = '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'

#เป็นฟังก์ชั่นที่ใช้ในการตรวจสอบว่าตอนนี้บอทมีการใช้งานเสียงอยู่หรือไม่
async def audio_playing(ctx):
    client = ctx.guild.voice_client
    #ถ้ามีการใช้งานเสียงอยู่จะ return ว่าเป็นจริง
    if client and client.channel and client.source:
        return True
    #ถ้าไม่มีการใช้ จะแสดงใน command
    else:
        raise commands.CommandError("Not currently playing any audio.")

#เป็นฟังก์ชั่นที่ใช้ในการตรวจสอบว่ามีผู้ใช้งานอยู่ใน voice channel หรือไม่
async def in_voice_channel(ctx):
    voice = ctx.author.voice
    bot_voice = ctx.guild.voice_client
    #ถ้ามีผู้ใช้งานอยู่ใน voice channel จะ return ว่าเป็นจริง
    if voice and bot_voice and voice.channel and bot_voice.channel and voice.channel == bot_voice.channel:
        return True
    #ถ้าไม่มีผู้ใช้ จะแสดงใน command
    else:
        raise commands.CommandError("You need to be in the channel to do that.")

#เป็นคำสั่งที่ใช้ในการสั่งให้บอทเล่นเพลง
class MUSIC(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.states = {}
        self.bot.add_listener(self.on_reaction_add, "on_reaction_add")
        
        self.is_playing = False
        self.music_queue = []
        self.YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist':'True'}
        self.FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
        self.vc = ""

    #เป็นฟังก์ชั่นที่เกี่ยวกับ lib ของ discord.py
    def get_state(self, guild):
        if guild.id in self.states:
            return self.states[guild.id]
        else:
            self.states[guild.id] = GuildState()
            return self.states[guild.id]

    #เป็นคำสั่งที่ใช้ในการข้ามเพลง
    @commands.guild_only()
    @commands.check(audio_playing)
    @commands.check(in_voice_channel)
    @commands.command(name="skip", help="Skips the current song being played")
    async def skip(self, ctx):
        state = self.get_state(ctx.guild)
        client = ctx.guild.voice_client
        if ctx.channel.permissions_for(ctx.author).administrator or state.is_requester(ctx.author):
            client.stop()

    def _play_song(self, client, state, song):
        state.now_playing = song
        state.skip_votes = set()
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(song.stream_url, before_options=FFMPEG_BEFORE_OPTS), volume=state.volume)

        def after_playing(err):
            if len(state.playlist) > 0:
                next_song = state.playlist.pop(0) #เป็นการใช้ stack ในการนำเพลงเดิมออก แล้วเล่นเพลงต่อไป
                self._play_song(client, state, next_song)
            else:
                asyncio.run_coroutine_threadsafe(client.disconnect(),self.bot.loop)

        client.play(source, after=after_playing)

    #เป็นคำสั่งเอาบอทออกจาก voice channel
    @commands.command(aliases=["stop"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def leave(self, ctx):
        client = ctx.guild.voice_client
        state = self.get_state(ctx.guild)
        if client and client.channel:
            await client.disconnect()
            state.playlist = []
            state.now_playing = None
        else:
            raise commands.CommandError("Not in a voice channel.")

    #เป็นคำสั่งเพื่อหยุดเพลงชั่วคราว/เล่นต่อ
    @commands.command(aliases=["resume","r"])
    @commands.guild_only()
    @commands.check(audio_playing)
    @commands.check(in_voice_channel)
    async def pause(self, ctx):
        client = ctx.guild.voice_client
        self._pause_audio(client)

    def _pause_audio(self, client):
        if client.is_paused():
            client.resume()
        else:
            client.pause()

    #้เป็นคำสั่งใช่ในการเพิ่ม/ลดเสียงของบอท ตั้งแต่ 0 ถึง 250
    @commands.command(aliases=["vol", "v"])
    @commands.guild_only()
    @commands.check(audio_playing)
    @commands.check(in_voice_channel)
    async def volume(self, ctx, volume: int):
        state = self.get_state(ctx.guild)
        if volume < 0:
            volume = 0

        client = ctx.guild.voice_client

        state.volume = float(volume) / 100.0
        client.source.volume = state.volume

    #เป็นคำสั่งเพื่อแสดงเพลงปัจจุบัน
    @commands.command(aliases=["np"])
    @commands.guild_only()
    @commands.check(audio_playing)
    async def nowplaying(self, ctx):
        state = self.get_state(ctx.guild)
        message = await ctx.send("", embed=state.now_playing.get_embed())
        await self._add_reaction_controls(message)

    #เป็นคำสั่งแสดงเพลงในคิว
    @commands.command(aliases=["q", "playlist"])
    @commands.guild_only()
    @commands.check(audio_playing)
    async def queue(self, ctx):
        state = self.get_state(ctx.guild)
        await ctx.send(self._queue_text(state.playlist))

    def _queue_text(self, queue):
        """Returns a block of text describing a given song queue."""
        if len(queue) > 0:
            message = [f"{len(queue)} songs in queue:"]
            message += [
                f"  {index+1}. **{song.title}** (requested by **{song.requested_by.name}**)"
                for (index, song) in enumerate(queue)
            ]  
            return "\n".join(message)
        else:
            return "The play queue is empty."
        
    #เป็นคำสั่งลบเพลงทั้งหมดในคิว
    @commands.command(aliases=["cq"])
    @commands.guild_only()
    @commands.check(audio_playing)
    @commands.has_permissions(administrator=True)
    async def clearqueue(self, ctx):
        state = self.get_state(ctx.guild)
        state.playlist = []

    #เป็นคำสั่งเล่นเพลงจาก url หรือ พิมพ์ชื่อเพลงได้เลย
    @commands.command(aliases=["p"],brief="Plays audio from <url>.")
    @commands.guild_only()
    async def play(self, ctx, *, url):
        client = ctx.guild.voice_client
        state = self.get_state(ctx.guild) 

        if client and client.channel:
            try:
                video = Video(url, ctx.author)
            except youtube_dl.DownloadError as e:
                logging.warn(f"Error downloading video: {e}")
                await ctx.send("There was an error downloading your video, sorry.")
                return
            state.playlist.append(video)
            message = await ctx.send(
                "Added to queue.", embed=video.get_embed())
            await self._add_reaction_controls(message)
        else:
            if ctx.author.voice is not None and ctx.author.voice.channel is not None:
                channel = ctx.author.voice.channel
                try:
                    video = Video(url, ctx.author)
                except youtube_dl.DownloadError as e:
                    await ctx.send(
                        "There was an error downloading your video, sorry.")
                    return
                client = await channel.connect()
                self._play_song(client, state, video)
                message = await ctx.send("", embed=video.get_embed())
                await self._add_reaction_controls(message)
                logging.info(f"Now playing '{video.title}'")
            else:
                raise commands.CommandError(
                    "You need to be in a voice channel to do that.")
    #เพิ่มปุ่ม pause/play และ skip
    async def on_reaction_add(self, reaction, user):
        message = reaction.message
        if user != self.bot.user and message.author == self.bot.user:
            await message.remove_reaction(reaction, user)
            if message.guild and message.guild.voice_client:
                user_in_channel = user.voice and user.voice.channel and user.voice.channel == message.guild.voice_client.channel
                permissions = message.channel.permissions_for(user)
                guild = message.guild
                state = self.get_state(guild)
                if permissions.administrator or (
                        user_in_channel and state.is_requester(user)):
                    client = message.guild.voice_client
                    if reaction.emoji == "⏯":
                        # pause audio
                        self._pause_audio(client)
                    elif reaction.emoji == "⏭":
                        # skip audio
                        client.stop()
                    
    async def _add_reaction_controls(self, message):
        """Adds a 'control-panel' of reactions to a message that can be used to control the bot."""
        CONTROLS = ["⏯", "⏭"]
        for control in CONTROLS:
            await message.add_reaction(control)


class GuildState:
    """Helper class managing per-guild state."""

    def __init__(self):
        self.volume = 1.0
        self.playlist = []
        self.skip_votes = set()
        self.now_playing = None

    def is_requester(self, user):
        return self.now_playing.requested_by == user
