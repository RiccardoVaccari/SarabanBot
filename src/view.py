from __future__ import annotations
import discord
from .game_components.game import Game
from config import PLAYLISTS
from .utils import parse_playlist
import random

PLAYLIST_DROPDOWN_ID = "settings:dropdown:playlist"
ADD_PLAYLIST_BTN_ID = "settings:button:add_playlist"


class MyModal(discord.ui.Modal):
    def __init__(self, view: GameView, * args, **kwargs) -> None:
        self.view = view
        super().__init__(
            discord.ui.InputText(
                label="Spotify Playlist URL",
                placeholder="https://open.spotify.com/playlist/...",
            ),
            *args,
            **kwargs,
        )

    async def callback(self, interaction: discord.Interaction):
        playlist_name, sources = parse_playlist(
            playlist_url=self.children[0].value)
        playlist_dropdown: PlaylistDropdown = self.view.get_item(
            PLAYLIST_DROPDOWN_ID)
        playlist_dropdown.playlists.update({playlist_name: sources})
        playlist_dropdown.add_option(
            label=playlist_name, description=f"{len(sources)} songs", emoji="➕")
        playlist_dropdown.max_values += 1

        await interaction.response.edit_message(view=self.view)


class PlaylistDropdown(discord.ui.Select):
    def __init__(self, bot_: discord.Bot) -> None:
        self.bot = bot_
        self.playlists = dict()
        options = list()

        for emoji, link in PLAYLISTS.items():
            playlist_name, sources = parse_playlist(playlist_url=link)
            self.playlists.update({playlist_name: sources})
            options.append(
                discord.SelectOption(
                    label=playlist_name, description=f"{len(sources)} songs", emoji=emoji
                ))

        super().__init__(
            placeholder="Choose some playlists...",
            min_values=1,
            max_values=len(options),
            options=options,
            custom_id=PLAYLIST_DROPDOWN_ID
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await self.view.start_game(dropdown=self, interaction=interaction)


class SettingsView(discord.ui.View):

    def __init__(self, cog: discord.Cog, bot: discord.Bot, ctx: discord.ApplicationContext) -> None:
        self.cog = cog
        self.bot = bot
        self.ctx = ctx
        super().__init__()
        self.add_item(PlaylistDropdown(bot_=self.bot))

    async def start_game(self, dropdown: PlaylistDropdown, interaction: discord.Interaction) -> None:
        game: Game = self.cog._get_game(interaction.guild)

        if interaction.user != game.creator.user:
            await interaction.response.send_message(f"Only when {game.creator} has selected the playlists will the game begin.", ephemeral=True)
            return

        embed = discord.Embed(
            color=discord.Color.orange(),
            title="Starting..."
        )

        self.clear_items()
        await interaction.response.edit_message(embed=embed, view=self)

        songs = set()

        for playlist_selected in dropdown.values:
            songs = songs.union(set(dropdown.playlists[playlist_selected]))

        # await game.add_songs(songs, dropdown.values)
        await game.add_songs(random.choices(
            [*songs], k=game.songs_number), dropdown.values)
        await game.start()

    @discord.ui.button(label="Add Playlist", style=discord.ButtonStyle.green, custom_id=ADD_PLAYLIST_BTN_ID, emoji="➕")
    async def add_playlist_btn(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        modal = MyModal(view=self, title="Add a playlist")
        await interaction.response.send_modal(modal=modal)
        await interaction.edit_original_response(view=self)


class GameView(discord.ui.View):
    def __init__(self, cog: discord.Cog, bot: discord.Bot, ctx: discord.ApplicationContext, game: Game) -> None:
        self.cog = cog
        self.bot = bot
        self.ctx = ctx
        self.game = game
        super().__init__()

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.blurple, custom_id="game:button:skip")
    async def skip_btn(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        voters = await self.game.skip_song(interaction.user)
        if len(voters) > 0:
            button.label = f"Skip {len(voters)}/{len(self.game.players)}"

            embed = self.game.get_embed(embed=interaction.message.embeds[0])

            await interaction.response.edit_message(embed=embed, view=self)
