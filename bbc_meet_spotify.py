import re
import time
import unicodedata
from collections import defaultdict
from enum import Enum
from pathlib import Path
from typing import Dict, List

import requests
import spotipy
import toml
import typer
from bs4 import BeautifulSoup
from loguru import logger
from spotipy import util
from spotipy.client import SpotifyException


class Song:
    def __init__(self, artist, song_title):
        self.song_title = self.clean_string(song_title)
        self.artist = self.clean_string(artist)

    def __repr__(self):
        return f"<{self.get_track_string()}>"

    def get_track_string(self):
        """Get string value for track"""
        return f"{self.artist}: {self.song_title}"

    @staticmethod
    def clean_string(string):
        """
        Converts any accented character to the base type, leaves alphanumeric and apostrophes
        All other characters are replaced with whitespace, finally split at feat. and the first part taken
        :param string: input string to be cleaned
        :return: cleaned string
        """
        new_string = "".join(
            [char for char in unicodedata.normalize("NFD", string) if unicodedata.category(char) != "Mn"]
        )
        new_string = re.sub("[^A-Za-z0-9.'’]+", " ", new_string)
        return new_string.split(" feat.")[0]


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


class Spotify:
    def __init__(self):
        """Save class data and set up spotify API"""
        config = toml.load(Path("./config.toml"))
        token = self.get_spotify_token(config)
        self.username = config["username"]
        self.spotify = spotipy.Spotify(auth=token)
        self.songs_not_found = []

    def add_songs_to_playlist(self, playlist_id: str, song_ids: List[str]):
        """
        Songs which are not currently in the playlist will be added.
        :param playlist_id: id for playlist
        :param song_ids: list of song ids
        :return:
        """
        playlist_info = self.spotify.user_playlist(self.username, playlist_id, "tracks")
        existing_songs = [x["track"]["id"] for x in playlist_info["tracks"]["items"]]
        new_song_ids = [song_id for song_id in song_ids if song_id not in existing_songs]
        try:
            self.spotify.user_playlist_add_tracks(self.username, playlist_id, new_song_ids)
        except SpotifyException:
            logger.info(f"No new songs were added to the playlist")

    @staticmethod
    def get_spotify_token(config: dict) -> str:
        """
        If token isn't already generated, redirect to authorisation and then enter url to command line input
        :param config: configuration
        :return: spotify OAuth token
        """
        token = util.prompt_for_user_token(
            config["username"],
            "playlist-modify-private playlist-modify-public",
            config["client_id"],
            config["client_secret"],
            "http://localhost:8888",
        )
        return token

    def create_playlist(self, playlist_name: str, add_date_prefix: bool = True, public_playlist: bool = True) -> str:
        """
        Creates playlist if it doesn't already exist, otherwise get the playlist id
        :param playlist_name: name for the playlist
        :param add_date_prefix: if true, add ISO date
        :param public_playlist: if true, make the playlist public
        :return: the playlist id
        """
        if add_date_prefix:
            playlist_name = f"{time.strftime('%Y-%m-%d')}_{playlist_name}"
        current_playlists = self.spotify.user_playlists(self.username)

        playlist = {}
        for current_playlist in current_playlists["items"]:
            if playlist_name == current_playlist["name"]:
                playlist["id"] = current_playlist["id"]
                logger.info(f"Playlist '{playlist_name}' already exists, reusing playlist")

        if not playlist:
            logger.info(f"Creating playlist '{playlist_name}' for user '{self.username}'")
            playlist = self.spotify.user_playlist_create(self.username, playlist_name, public=public_playlist)

        return playlist["id"]

    def get_song_ids(self, songs: List[Song]) -> List[str]:
        """
        Convert all Songs into song ids, failed conversions will be removed
        :param songs: Songs to be converted
        :return: list of song ids from spotify
        """
        song_ids = [self._get_song_id(song) for song in songs]
        return list(filter(None, song_ids))

    def main(self, playlist_name, songs, add_date_prefix=True, public_playlist=True):
        """
        Run all spotify actions
        :param playlist_name: name of the playlist to be used or created
        :param songs: songs to be added
        :param add_date_prefix: If true, add date prefix to playlist
        :param public_playlist: If true, make playlist public
        """
        playlist_id = self.create_playlist(playlist_name, add_date_prefix, public_playlist)
        song_ids = self.get_song_ids(songs)
        self.add_songs_to_playlist(playlist_id, song_ids)

        message_base = "All done!"
        if self.songs_not_found:
            manual_songs = "\n\t".join(self.songs_not_found)
            logger.info(f"{message_base}\n"
                        f"Couldn't find the following songs,  you'll have to do this manually for now 😥\n\t"
                        f"{manual_songs}")
        else:
            logger.info(f"{message_base} No songs need to be added manually 🥳")

    def query_spotify(self, artist: str, song_title: str) -> str:
        """
        Query spotify for artist and song title, returning the id
        :param artist: artist
        :param song_title: song title
        :raises IndexError: if no tracks are found
        :return: spotify song id
        """
        results = self.spotify.search(q=f"artist:{artist} track:{song_title}")["tracks"]["items"]
        results.sort(key=lambda x: len(x["name"]))
        return results[0]["id"]

    def _get_song_id(self, song: Song) -> str:
        """
        Get song id from spotify.
        Will attempt to first search keeping apostrophes in text, if that fails then
        the song will be searched again without apostrophes
        Underscore so I don't get it mixed up with get_song_ids
        :param song: Song
        :return: song_id or None if song was not found
        """
        song_id = None
        try:
            song_id = self.query_spotify(song.artist, song.song_title)
        except IndexError:
            # try fixing the strings with removing apostrophes
            try:
                song_id = self.query_spotify(song.artist.replace("'", "").replace(".", ""),
                                             song.song_title.replace("'", "").replace(".", ""))
            except IndexError:
                self.songs_not_found.append(f"{song.get_track_string()}")
        return song_id


class PlaylistChoices(str, Enum):
    six_music = "six_music"
    radio1 = "radio1"


@logger.catch
def main(playlist_key: PlaylistChoices,
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


if __name__ == "__main__":
    typer.run(main)
