import yt_dlp
from config import YTDL_OPTIONS
import discord


class SpotifySource():

    def __init__(self, id_: str, title: str, artists: list[str], image: str, duration: int, link: str, isrc: str,  album: str = None) -> None:
        self.id = id_
        self.title = title
        self.artists = artists
        self.image = image
        self.duration = duration / 1000
        self.link = link
        self.isrc = isrc
        self.album = album
        self.stream_url = None
        self.guessed_metadata = {
            "title": (),    # (player, title_attemp, points)
            "artists": {},  # user : plyer,
                            # guessed : [(artist_attemp, points)]
        }
        self.messages: list[discord.Message] = list()

    def __eq__(self, __o: object) -> bool:
        return isinstance(__o, SpotifySource) and __o.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __repr__(self) -> str:
        return f"{self.title} - {', '.join(self.artists)} [{self.album}]"

    def get_stream(self) -> str:
        if self.isrc:
            query = self.isrc
        else:
            query = f"{self.title} - {','.join(self.artists)}".replace(
                ":", "").replace('"', "")

        YTDL_OPTIONS["postprocessor_args"] = [
            "-metadata",
            f"title={self.title}",
            "-metadata",
            f"artist={','.join(self.artists)}",
            "-metadata",
            f"album={self.album}",
        ]

        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            result = ydl.extract_info(query, download=False)

            if "entries" in result:
                try:
                    self.stream_url = result["entries"][0]["url"]
                except IndexError:
                    return None
            else:
                self.stream_url = result["url"]

        return self.stream_url
