import re
import time
import unicodedata
from enum import Enum
from pathlib import Path
from typing import List

import requests
import spotipy
import toml
import typer
from bs4 import BeautifulSoup
from loguru import logger
from spotipy import util
from spotipy.client import SpotifyException


class BBCSounds:
    @staticmethod
    def get_playlist_info(playlist_key: str = None) -> dict:
        """
        Get playlist information for requests playlist, if no playlist, returns the entire toml dictionary.
        :param playlist_key: key in the toml file
        :return: dictionary of url and verbose name for the playlist
        """
        playlists = toml.load(Path("./bbc_playlists.toml"))
        if playlist_key:
            playlists = playlists[playlist_key]
        return playlists

    @staticmethod
    def get_songs(url: str) -> dict:
        """
        Get artist and song name from bbc sounds url
        :param url: Url to scrape tracks from
        :return: List of songs
        """
        page = requests.get(url)
        soup = BeautifulSoup(page.text, "html.parser")
        song_grid = soup.find(class_="programmes-page article--individual")
        artists = [
            i.text.strip()
            for i in song_grid.find_all_next("a", class_="br-blocklink__link promotion__link")
            if not i.text.startswith("Tap here to listen to")
        ]
        song_title = [
            i.text.strip() for i in song_grid.find_all_next("p", class_="promotion__synopsis centi text--subtle")
        ]
        songs = [Song(artist, track_name) for track_name, artist in zip(song_title, artists)]
        # remove last item because this is an album
        logger.info(f"Album of the day is: {songs.pop(-1)}")
        return songs


class Song:
    def __init__(self, artist, song_title):
        self.song_title = self.clean_string(song_title)
        artist = self.clean_string(artist)
        self.artist = artist.split(" feat ")[0]

    def __repr__(self):
        return f"<{self.artist}: {self.song_title}>"

    @classmethod
    def clean_string(cls, string):
        """
        Converts any accented character to the base type, leaves alphanumeric and apostrophes
        All other characters are replaced with whitespace
        :param string: input string to be cleaned
        :return: cleaned string
        """
        new_string = "".join(
            [char for char in unicodedata.normalize("NFD", string) if unicodedata.category(char) != "Mn"]
        )
        new_string = re.sub("[^A-Za-z0-9']+", " ", new_string)
        return new_string


class Spotify:
    def __init__(self):
        """Save class data and set up spotify API"""
        config = toml.load(Path("./config.toml"))
        token = self.get_spotify_token(config)
        self.username = config["username"]
        self.spotify = spotipy.Spotify(auth=token)

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
        except SpotifyException as e:
            logger.info(f"No new songs were added to the playlist")

    def get_spotify_token(self, config: dict) -> str:
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
        logger.info("All done, if you have any errors then you'll have to add these manually I'm afraid")

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
                song_id = self.query_spotify(song.artist.replace("'", ""), song.song_title.replace("'", ""))
            except IndexError as e:
                logger.error(f"Could not find a song: {song}", e)
        return song_id


class PlaylistChoices(str, Enum):
    six_music = "six_music"
    radio1 = "radio1"


@logger.catch
def main(playlist_key: PlaylistChoices,
         date_prefix: bool = typer.Option(True, help="Add a date prefix to be added to your spotify playlist?"),
         public_playlist: bool = typer.Option(True, "--public-playlist/--private-playlist",
                                              help="Spotify playlist settings"),
         custom_playlist_name: str = typer.Option(None, "--custom-playlist-name", "-n", help="Set a custom name for playlist")):
    logger.info(f"Getting playlist for bbc playlist key {playlist_key.value}")
    playlist_info = BBCSounds.get_playlist_info(playlist_key.value)

    if custom_playlist_name:
        playlist_suffix = custom_playlist_name
    else:
        playlist_suffix = playlist_info["verbose_name"]

    songs = BBCSounds.get_songs(playlist_info["url"])
    spotify = Spotify()
    spotify.main(playlist_suffix, songs, date_prefix, public_playlist)


if __name__ == "__main__":
    typer.run(main)
