from enum import Enum

import typer
from loguru import logger
from spotipy import Spotify

from . import BBCSounds, Spotify


class PlaylistChoices(str, Enum):
    six_music = "six_music"
    radio1 = "radio1"

@logger.catch
def console(playlist_key: PlaylistChoices,
         date_prefix: bool = typer.Option(False,
                                          help="Add a date prefix to be added to your spotify playlist?",
                                          show_default=True),
         public_playlist: bool = typer.Option(True, "--public-playlist/--private-playlist",
                                              help="Spotify playlist settings",
                                              show_default=True),
         custom_playlist_name: str = typer.Option(None, "--custom-playlist-name", "-n",
                                                  help="Set a custom name for playlist")
         ):
    logger.info(f"Getting playlist for bbc playlist key {playlist_key.value}")
    bbc_sounds = BBCSounds(playlist_key.value, date_prefix, custom_playlist_name)

    songs = bbc_sounds.get_songs()
    spotify = Spotify()
    spotify.main(bbc_sounds.playlist_suffix, songs, date_prefix, public_playlist)


def main():
    typer.run(console)
