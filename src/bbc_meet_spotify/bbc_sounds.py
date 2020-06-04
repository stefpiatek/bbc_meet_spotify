from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import requests
import toml
from bs4 import BeautifulSoup

from .songs import Song


class BBCSounds:
    def __init__(self, playlist_key: str, date_prefix: bool, playlist_name: str = None):
        """Builds playlist name and gets playlist url from bbc_playists.toml"""
        playlist = self.get_playlist_info(playlist_key)
        self.url = playlist["url"]
        self.date_prefix = date_prefix
        if playlist_name:
            self.playlist_suffix = playlist_name
        else:
            self.playlist_suffix = playlist["verbose_name"]

    def get_playlist_info(self, playlist_key: str) -> dict:
        """
        Get playlist information for requests playlist
        :param playlist_key: key in the toml file
        :return: dictionary of url and verbose name for the playlist
        """
        playlists = toml.load(Path("./bbc_playlists.toml"))
        if playlist_key:
            playlists = playlists[playlist_key]
        return playlists

    def _scrape_bbc_sounds(self) -> Dict[str, str]:
        """
        Get all artist and song names from bbc sounds url
        :return: List of songs in {artist: song_name}
        """

        page = requests.get(self.url)
        soup = BeautifulSoup(page.text, "html.parser")
        # go to after C list and then get all of the tracks before
        header = soup.find(class_="beta")
        for _ in ["B list", "C list", "Album of the day"]:
            header = header.find_next(class_="beta")

        track_strings = []
        song_tag = "p"
        # can be separated by dashes or hyphens
        for separator in [" – ", " - "]:
            track_strings.extend([
                (i.text.strip().split(separator))
                for i in header.find_all_previous(song_tag)
                if separator in i.text
            ])

        songs = {artist: song_name for artist, song_name in track_strings}
        return songs

    def get_songs(self) -> List[Song]:
        """Gets songs from bbc sounds url,

        If BBC Sounds was initialised with a date_prefix = false:
        - Compares against previous scraping for the playlist name if this has been done before
        - Writes out history of all songs for this playlist to playlist_history directory

        (It was a pain to have spotify singles and album versions become duplicates for songs, so filtering at the
        BBC sounds stage made more sense)

        :return: list of new Songs
        """
        # get all bbc sounds songs
        current_songs = self._scrape_bbc_sounds()

        # get previous songs in playlist
        playlist_history = Path("playlist_history", f"{self.playlist_suffix}.toml")
        if not playlist_history.exists() or self.date_prefix:
            previous_songs = defaultdict(list)
        else:
            previous_songs = defaultdict(list, toml.load(playlist_history))

        # remove songs which have already been seen in previous versions of bbc sounds
        new_songs = {artist: song_name for artist, song_name in current_songs.items()
                     if song_name not in previous_songs[artist]}

        # merge new songs with previous songs
        for artist, song_name in new_songs.items():
            previous_songs[artist].append(song_name)

        # write history of songs to file if not a date-prefixed playlist
        if not self.date_prefix:
            with open(playlist_history, "w") as handle:
                toml.dump(previous_songs, handle)

        # return list of Songs
        return [Song(artist, song_name) for artist, song_name in new_songs.items()]


