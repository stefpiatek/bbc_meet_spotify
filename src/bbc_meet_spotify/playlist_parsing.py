from enum import Enum
from pathlib import Path
from typing import Tuple

import toml


def parse_playlist_file(playlist_key: str, custom_playlist_name: str = None) -> Tuple[str, str]:
    """
    Parses playlist file, with optional custom playlist name override
    :param playlist_key:
    :param custom_playlist_name:
    :return:
    """
    playlist = toml.load(Path("./bbc_playlists.toml"))[playlist_key]
    playlist_suffix = custom_playlist_name or playlist["verbose_name"]
    return playlist["url"], playlist_suffix


class PlaylistChoices(str, Enum):
    six_music = "six_music"
    radio1 = "radio1"
    dance_party_2021 = "dance_party_2021"
