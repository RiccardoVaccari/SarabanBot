from spotipy import Spotify, SpotifyClientCredentials

# -- Discord Config --
BOT_TOKEN = ""
SERVER = []

# -- Spotify Config --
SPOTIFY_CLIENT_ID = ""
SPOTIFY_CLIENT_SECRET = ""

client_credentials_manager = SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET)
SPOTIFY = Spotify(client_credentials_manager=client_credentials_manager)

# -- GAME Config --
TITLE_POINTS = 10
ARTIST_POINTS = 10

# -- Spotify Playlists --
PLAYLISTS = {
    "🌍": "https://open.spotify.com/playlist/37i9dQZEVXbMDoHDwVN2tF?si=ab558af4e5be421d",
}


# -- Streaming Settings --

YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    # Bind to ipv4 since ipv6 addresses cause issues at certain times
    "source_address": "0.0.0.0",
    "force-ipv4": True,
    "cachedir": False,
    "postprocessor_args": [],
}

FFMPEG_OPTIONS = {"options": "-vn",
                  "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"}
