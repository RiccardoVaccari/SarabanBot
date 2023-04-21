import discord


class Player:
    def __init__(self, user: discord.User) -> None:
        self.user = user
        self.points = 0

    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, Player) and self.user == __o.user

    def __hash__(self) -> int:
        return hash(self.user)

    def __str__(self) -> str:
        return f"<@{self.user.id}>"
