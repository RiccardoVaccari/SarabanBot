from .source import SpotifySource
from config import SPOTIFY
import discord
import re
import unidecode
import string


def parse_playlist(playlist_url: str) -> tuple[str, list[SpotifySource]]:
    playlist = SPOTIFY.playlist(playlist_url)

    playlist_name = playlist["name"]

    sources = list()

    for song in playlist["tracks"]["items"]:
        sources.append(
            SpotifySource(
                id_=song["track"]["id"],
                title=song["track"]["name"],
                artists=[artist["name"]
                         for artist in song["track"]["artists"]],
                image=song["track"]["album"]["images"][0]["url"] if "album" in song["track"] else None,
                link=song["track"]["external_urls"]["spotify"],
                duration=song["track"]["duration_ms"],
                isrc=song["track"]["external_ids"]["isrc"] if "isrc" in song["track"]["external_ids"] else None,
                album=song["track"]["album"]["name"] if "album" in song["track"] else None
            ))

    return playlist_name, sources


def get_field(fields: list[discord.EmbedField], key: str) -> tuple[int, discord.EmbedField]:
    """return pos, discord.EmbedField"""
    for i, field in enumerate(fields):
        if field.name.lower() == key.lower():
            return i, field

    return None, None


def normalize(name: str) -> str:

    name = unidecode.unidecode(name)
    name = name.lower().split(" - ")[0]
    # name = re.sub("\(with .+\)", "", name)
    # name = re.sub("\(feat\. .+\)", "", name)
    name = re.sub("\(.+\)", "", name)

    for x in string.punctuation:
        name = name.replace(x, "")

    return name.strip()


def compare_words(string: str, pattern: str) -> bool:

    string = normalize(string)
    pattern = normalize(pattern)

    return string == pattern
