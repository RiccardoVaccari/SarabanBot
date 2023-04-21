from typing import Union
import discord
from config import SERVER
from .music_player import MusicPlayer
from .view import SettingsView
from .game_components.game import Game
from .game_components.player import Player


class GuessTheSongBot(discord.Cog):

    def __init__(self, bot: discord.Bot) -> None:
        super().__init__()
        self.bot = bot
        self.games = {}

    @discord.Cog.listener()
    async def on_ready(self) -> None:
        print(f'{self.bot.user.name} has connected to Discord!')

    def _get_game(self, guild: discord.Guild) -> Game:
        """Retrieve the guild game"""
        try:
            return self.games[guild.id]
        except KeyError:
            return None

    def _create_game(self, ctx: discord.ApplicationContext, board_interaction: discord.Interaction, songs_number: int) -> Game:
        game = self._get_game(ctx.guild)
        if not game:
            game = Game(
                bot=self.bot,
                ctx=ctx,
                music_player=MusicPlayer(ctx, self.bot),
                board_interaction=board_interaction,
                songs_number=songs_number,
            )

        self.games[ctx.guild.id] = game
        return game

    @discord.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member == self.bot.user:
            return

        if before.channel and not after.channel:
            game = self._get_game(before.channel.guild)

            if game and game.started:
                game.remove_player(Player(member))
                await game.refresh_embed()

    async def cleanup(self, ctx: discord.ApplicationContext):
        """Disconnect procedure and delete the game"""
        game = self._get_game(ctx.guild)
        try:
            await ctx.guild.voice_client.disconnect()
        except AttributeError:
            pass
        try:
            if game:
                del self.games[ctx.guild.id]
        except KeyError:
            pass

    async def join_channel(self, ctx: discord.ApplicationContext, channel: discord.VoiceChannel = None) -> tuple[bool, str]:
        """ Join the VoiceChannel """

        if not channel:
            channel = ctx.author.voice.channel if ctx.author.voice else None

        if not channel:
            return False, "You are not connected to a voice channel."

        if ctx.voice_client:
            return False, f"The game is already running on <#{ctx.voice_client.channel.id}> "

        await channel.connect()
        return True, ""

    @discord.slash_command(guild_ids=SERVER, name='play', description='Start playing!')
    async def play(self, ctx: discord.ApplicationContext, songs_number: int) -> None:
        """
        Start a new game.
        Send the View message with game settings, then on confirm start the game
        """
        connected, error = await self.join_channel(ctx=ctx)
        if not connected:
            await ctx.respond(error)
            return

        embed = discord.Embed(
            color=discord.Colour.dark_grey(),
            title="⚙️ Game Settings",
            type="rich",
            description="React to the message to join, when you are all ready select the playlists.",
        )

        embed.add_field(
            name="Players",
            value=f"<@{ctx.author.id}>"
        )
        embed.add_field(
            name="Songs number",
            value=f"{songs_number}"
        )

        settings_message = await ctx.respond(embed=embed, view=SettingsView(self, self.bot, ctx))
        msg = await settings_message.original_response()
        await msg.add_reaction("🙋‍♂️")

        game = self._create_game(ctx, settings_message, songs_number)

    @discord.Cog.listener()
    async def on_reaction_add(self, reaction: discord.Reaction, user: Union[discord.Member, discord.User]) -> None:
        game = self._get_game(reaction.message.guild)

        if game and user != self.bot.user:
            await self._handle_reaction(reaction, user, game, game.add_player)

    @discord.Cog.listener()
    async def on_reaction_remove(self, reaction: discord.Reaction, user: Union[discord.Member, discord.User]) -> None:
        game = self._get_game(reaction.message.guild)

        if game and user != self.bot.user:
            await self._handle_reaction(reaction, user, game, game.remove_player)

    async def _handle_reaction(self, reaction: discord.Reaction, user: Union[discord.Member, discord.User], game: Game, hanle_player: callable) -> None:
        if user == self.bot.user and game.started:
            return

        if user not in game.music_player.vc.channel.members:
            return

        players = hanle_player(Player(user=user))
        if game.started:
            await game.refresh_embed()
        else:
            reaction.message.embeds[0].set_field_at(
                index=0,
                name="Players",
                value=", ".join(str(p) for p in list(players))
            )
            await game.board_message.edit_original_response(embeds=reaction.message.embeds)

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        game = self._get_game(message.guild)

        if not game or not game.started:
            return
        player = Player(message.author)
        if player not in game.players:
            return

        # checking word with title and artists [to OPTIMIZE]
        # title_answer = await game.check_title(player=player, title_attemp=message.content)
        if not await game.check_title(player=player, message=message) and not await game.check_artist(player=player, message=message):
            # artist_answer = await game.check_artist(player=player, artist_attemp=message.content)
            # if not title_answer and not artist_answer:
            await message.delete()

    @discord.slash_command(guild_ids=SERVER, name='end', description='End the game!')
    async def end(self, ctx: discord.ApplicationContext) -> None:
        await self.cleanup(ctx)

        if self._get_game(ctx.guild):
            await ctx.respond("There's no game running")
            return

        del self.games[ctx.guild.id]
        await ctx.respond("🛑 Game stopped!")
