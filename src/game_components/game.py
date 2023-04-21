import discord
from ..music_player import MusicPlayer
from ..source import SpotifySource
from .player import Player
from ..utils import get_field, compare_words
from config import TITLE_POINTS, ARTIST_POINTS
from enum import Enum


class GameState(Enum):
    NOT_STARTED = 0
    STARTED = 1
    ENDED = 2


class Game:
    def __init__(self, bot: discord.Bot, ctx: discord.ApplicationContext, music_player: MusicPlayer, board_interaction: discord.Interaction, songs_number: int) -> None:
        self._bot = bot
        self._ctx = ctx
        self.music_player = music_player
        self.board_message = board_interaction
        self.songs_number = songs_number
        self.creator = Player(self._ctx.author)
        self.players = set()
        self.add_player(self.creator)
        self.state: GameState = GameState.NOT_STARTED
        self.music_player.game = self

        self.songs: list[SpotifySource] = list()
        self.playlists_names: list[str] = list()
        self._skip_song_votes = set()
        self._last_round_points = dict()

    @property
    def started(self) -> bool:
        return self.state == GameState.STARTED

    def add_player(self, player: Player) -> set[Player]:
        self.players.add(player)
        return self.players

    def remove_player(self, player: Player) -> set[Player]:
        if player in self.players and player != self.creator:
            self.players.remove(player)
        return self.players

    def clear_votes(self) -> None:
        self._skip_song_votes = set()

    def get_player(self, player: Player) -> Player:
        for p in self.players:
            if player == p:
                return p
        return

    async def refresh_embed(self) -> None:
        message = self.board_message.message
        if message:
            embed = self.get_embed(embed=message.embeds[0])
            await self.edit_message(embed=embed)

    async def add_songs(self, songs: list[SpotifySource], playlists_names: list[str]) -> None:
        self.songs = songs
        self.playlists_names = playlists_names

        for i, song in enumerate(songs):
            await self.music_player.add_to_queue(i+1, song)
        await self.music_player.add_to_queue(0, None)

    async def start(self) -> None:
        # start the game
        self.state = GameState.STARTED
        # 0. start the music
        await self.music_player.player_loop()

    async def edit_message(self, **kwargs) -> None:
        self.board_message.message = await self.board_message.edit_original_response(**kwargs)

    def get_embed(self, embed: discord.Embed = None, **kwargs):
        if not embed:
            # print(len(self.songs), self.songs)
            index, song = self.music_player.playing_song
            embed = discord.Embed(
                color=discord.Color.green(),
                title=f"Guess the song #{index}",
                description=f"Songs from {', '.join(self.playlists_names)}\nSend messages with the name of the song!"
            )
            embed.add_field(name="Title", value="???")
            embed.add_field(name="Artists", value="???")
            embed.add_field(name='\u200B', value='\u200B')

            embed.add_field(name="Players", value="\n".join(
                [str(p) for p in sorted(self.players, key=lambda p: p.points, reverse=True)]))
            embed.add_field(name="Points", value="\n".join(
                [str(p.points) for p in sorted(self.players, key=lambda p: p.points, reverse=True)]))

            embed.add_field(name="Skips", value="\n".join(
                [str(p) for p in self._skip_song_votes]) if self._skip_song_votes else f"0/{len(self.players)}")

            last_song_index = index-2
            if last_song_index >= 0:
                last_song = self.songs[last_song_index]
                last_song_text = (
                    f"🎵 Title: **{last_song.title}**\n"
                    f"✏️ Artists: **{', '.join(last_song.artists)}**\n\n"
                )
                if last_song.guessed_metadata["title"]:
                    title_guesser, title_text, title_points = last_song.guessed_metadata["title"]
                    last_song_text += f"{str(title_guesser)} guessed the **title** with `{title_text}` **[+{title_points}]**"

                for _, guessed_artists_dict in last_song.guessed_metadata["artists"].items():
                    last_song_text += f"\n{str(guessed_artists_dict['player'])} guessed "
                    last_song_text += " | ".join([f"`{artist_text}` **[+{artist_points}]**" for artist_text,
                                                 artist_points in guessed_artists_dict['guessed']])

                embed.add_field(name="About the last song",
                                value=last_song_text, inline=False)

        else:
            for name, value in kwargs.items():
                pos, field = get_field(embed.fields, name)

                embed.set_field_at(pos, name=field.name,
                                   value=f"**{value}**", inline=field.inline)

            # Updates points & skips
            pos, field = get_field(embed.fields, "Players")
            if field:
                embed.set_field_at(index=pos, name="Players", value="\n".join(
                    [str(p) for p in sorted(self.players, key=lambda p: p.points, reverse=True)]))

            pos, field = get_field(embed.fields, "Points")
            if field:
                embed.set_field_at(index=pos, name="Points", value="\n".join(
                    [str(p.points) for p in sorted(self.players, key=lambda p: p.points, reverse=True)]), inline=field.inline)

            pos, field = get_field(embed.fields, "Skips")
            if field:
                embed.set_field_at(index=pos, name="Skips", value=", ".join(
                    [str(p) for p in self._skip_song_votes]) if self._skip_song_votes else f"0/{len(self.players)}", inline=field.inline)

        return embed

    async def check_title(self, player: Player, message: discord.Message) -> bool:
        title_attemp = message.content
        song = self.music_player.playing_song[1]
        if not compare_words(title_attemp, song.title):
            return False

        player = self.get_player(player)
        player.points += TITLE_POINTS
        song.guessed_metadata.update(
            {"title": (player, title_attemp, TITLE_POINTS)})

        song.messages.append(message)

        message = self.board_message.message
        embed = self.get_embed(embed=message.embeds[0], title=song.title)

        await self.edit_message(embed=embed)

        await self.music_player.skip()
        return True

    async def check_artist(self, player: Player, message: discord.Message) -> bool:
        artist_attemp = message.content
        song = self.music_player.playing_song[1]
        embed_message = self.board_message.message
        old_embed = embed_message.embeds[0]
        _, field = get_field(old_embed.fields, "Artists")

        artist = None
        for a in song.artists:
            if compare_words(artist_attemp, a) and a.lower() not in field.value.lower():
                artist = a

        if not artist:
            return False

        complete = all([a.lower() in field.value.lower()
                       or a.lower() == artist.lower() for a in song.artists])

        artists = ", ".join(
            [a for a in song.artists if a in field.value or a == artist])

        if not complete:
            artists += ", ???"

        player = self.get_player(player)
        player.points += ARTIST_POINTS // len(song.artists)

        if player.user.id not in song.guessed_metadata["artists"]:
            song.guessed_metadata["artists"][player.user.id] = {
                "player": player,
                "guessed": [(artist_attemp, ARTIST_POINTS // len(song.artists))]
            }
        else:
            song.guessed_metadata["artists"][player.user.id]["guessed"].append(
                (artist_attemp, ARTIST_POINTS // len(song.artists)))

        song.messages.append(message)

        embed = self.get_embed(embed=embed_message.embeds[0], artists=artists)

        await self.edit_message(embed=embed)
        return True

    async def skip_song(self, user: discord.User) -> list[Player]:
        player = self.get_player(Player(user=user))

        if player in self._skip_song_votes:
            self._skip_song_votes.remove(player)
        else:
            self._skip_song_votes.add(player)

        if len(self._skip_song_votes) == len(self.players):
            await self.music_player.skip()

        return self._skip_song_votes

    async def insert_image(self, song: SpotifySource) -> None:
        message = self.board_message.message
        embed = message.embeds[0]
        embed.set_thumbnail(url=song.image)

        await self.edit_message(embed=embed)

    async def end(self) -> None:
        self.state = GameState.ENDED

        players_leaderboard = sorted(
            self.players, key=lambda p: p.points, reverse=True)

        embed = discord.Embed(
            color=discord.Color.yellow(),
            title="🛑 Game Over 🛑"
        )
        embed.add_field(name="The Winner is",
                        value=f"🏆 {str(players_leaderboard[0])}")
        embed.add_field(name="Score",
                        value=players_leaderboard[0].points)
        embed.add_field(name='\u200B', value='\u200B')

        if players_leaderboard[1:]:
            embed.add_field(name="Players", value="\n".join(
                [f"{i+2}. {str(p)}" for i, p in enumerate(players_leaderboard[1:])]), inline=True)
            embed.add_field(name="Points", value="\n".join(
                [str(p.points) for p in players_leaderboard[1:]]), inline=True)

        await self.board_message.message.clear_reactions()
        await self.edit_message(embed=embed, view=None)
