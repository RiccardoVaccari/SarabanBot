import asyncio
import discord
from .source import SpotifySource
from config import FFMPEG_OPTIONS
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import timedelta, datetime as dt


class MusicPlayer:

    def __init__(self, ctx: discord.ApplicationContext, bot: discord.Bot):
        self.bot = bot
        self.ctx = ctx
        self.vc = ctx.voice_client
        self._guild = ctx.guild
        self._channel = ctx.channel
        self._cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()

        self.np = None  # Now playing message
        self.volume = 1
        self.current = None
        self.playing_song: tuple[int, SpotifySource] = None

        self.scheduler = AsyncIOScheduler(timezone="Europe/Rome")
        self.scheduler.start()

        self.game = None

    @property
    def is_playing(self):
        return self.vc and self.current

    async def add_to_queue(self, index: int, song: SpotifySource) -> None:
        await self.queue.put((index, song))

    async def player_loop(self):
        """Our main player loop."""
        from .view import GameView

        await self.ctx.bot.wait_until_ready()

        while not self.ctx.bot.is_closed():
            self.next.clear()
            self.game.clear_votes()
            self.playing_song = await self.queue.get()
            index, song = self.playing_song

            if index == 0 and not song:
                await self.destroy(self.ctx)
                await self.game.end()
                return

            try:
                source = discord.PCMVolumeTransformer(
                    discord.FFmpegPCMAudio(source=song.get_stream(), **FFMPEG_OPTIONS))
            except (AttributeError, TypeError):
                print("Errore nella riproduzione")
                continue

            source = discord.PCMVolumeTransformer(source, volume=self.volume)
            self.current = source

            if not self._guild.voice_client:
                return await self.destroy(self.ctx)

            self._guild.voice_client.play(
                # lambda _: self.ctx.bot.loop.call_soon_threadsafe(self.next.set))
                source, after=self.play_next_song)

            self.scheduler.add_job(
                self.load_image, id=song.title, run_date=dt.now() + timedelta(seconds=song.duration/2))

            embed = self.game.get_embed()

            await self.game.edit_message(embed=embed, view=GameView(self._cog, self.bot, self.ctx, self.game))

            # self.np = await self._channel.send(embed=embed)

            await self.next.wait()

            # Make sure the FFmpeg process is cleaned up.
            source.cleanup()
            self.current = None

    def play_next_song(self, error=None):
        if error:
            print(error)

        _, song = self.playing_song
        job = self.scheduler.get_job(job_id=song.title)
        if job:
            job.remove()

        self.next.set()

    async def load_image(self):
        _, song = self.playing_song
        await self.game.insert_image(song)

    async def destroy(self, ctx: discord.ApplicationContext):
        """Disconnect and cleanup the player."""
        await self._cog.cleanup(ctx)

    async def skip(self) -> None:
        _, song = self.playing_song
        if self.is_playing:
            self.vc.stop()

        for m in song.messages:
            await m.delete()
