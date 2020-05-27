from enum import Enum

import typer
from loguru import logger
from spotipy import Spotify

from . import BBCSounds, Spotify, __version__


class PlaylistChoices(str, Enum):
    six_music = "six_music"
    radio1 = "radio1"


def version_callback(value: bool):
    if value:
        typer.echo(f"BBC meet Spotify version: {__version__}")
        raise typer.Exit()


@logger.catch
def console(
        playlist_key: PlaylistChoices,
        date_prefix: bool = typer.Option(False,
                                         help="Add a date prefix to be added to your spotify playlist?",
                                         show_default=True),
        public_playlist: bool = typer.Option(True, "--public-playlist/--private-playlist",
                                             help="Spotify playlist settings",
                                             show_default=True),
        custom_playlist_name: str = typer.Option(None, "--custom-playlist-name", "-n",
                                                 help="Set a custom name for playlist"),
        version: bool = typer.Option(
            None, "--version", callback=version_callback, is_eager=True
        ),
):
    logger.info(f"Getting playlist for bbc playlist key {playlist_key.value}")
    bbc_sounds = BBCSounds(playlist_key.value, date_prefix, custom_playlist_name)

    songs = bbc_sounds.get_songs()
    spotify = Spotify()
    spotify.main(bbc_sounds.playlist_suffix, songs, date_prefix, public_playlist)


def main():
    typer.run(console)
