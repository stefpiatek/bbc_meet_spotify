import time
from pathlib import Path
from typing import List, Set

import spotipy
import toml

from bbc_meet_spotify.music import Music
from loguru import logger
from spotipy import util


class Spotify:
    def __init__(self):
        """Save class data and set up spotify API"""
        config = toml.load(Path("./config.toml"))
        token = self.get_spotify_token(config)
        self.username = config["username"]
        self.spotify = spotipy.Spotify(auth=token)
        self.music_not_found = []

    def add_music_to_playlist(self, playlist_id: str, song_ids: List[str]) -> None:
        """
        Songs which are not currently in the playlist will be added.
        :param playlist_id: id for playlist
        :param song_ids: list of song ids
        :return:
        """
        playlist_info = self.spotify.user_playlist(self.username, playlist_id, "tracks")
        existing_songs = [x["track"]["id"] for x in playlist_info["tracks"]["items"]]
        new_song_ids = [song_id for song_id in song_ids if song_id not in existing_songs]
        if new_song_ids:
            self.spotify.user_playlist_add_tracks(self.username, playlist_id, new_song_ids)
        else:
            logger.info("No new music to add to the playlist")


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

    def get_song_ids(self, songs: List[Music]) -> List[str]:
        """
        Convert all Songs into song ids, failed conversions will be removed
        :param songs: Songs to be converted
        :return: list of song ids from spotify
        """
        song_ids = [self._get_song_id(song) for song in songs]
        return list(filter(None, song_ids))

    def add_albums(self, playlist_name: str, albums: Set[Music], add_date_prefix=True, public_playlist=True) -> None:
        playlist_id = self.create_playlist(playlist_name, add_date_prefix, public_playlist)
        album_ids = []
        for album in albums:
            album_ids.extend(self._query_spotify_album_tracks(album))
            self.add_music_to_playlist(playlist_id, album_ids)

        message_base = "All done!"
        if self.music_not_found:
            not_found = "\n\t".join(self.music_not_found)
            logger.info(f"{message_base}\n"
                        f"Couldn't find the following albums,  you'll have to do this manually for now 😥\n\t"
                        f"{not_found}")
        else:
            logger.info(f"{message_base} No albums need to be added manually 🥳")

    def add_songs(self, playlist_name: str, songs: Set[Music], add_date_prefix=True, public_playlist=True) -> None:
        """
        Run all spotify actions
        :param playlist_name: name of the playlist to be used or created
        :param songs: songs to be added
        :param add_date_prefix: If true, add date prefix to playlist
        :param public_playlist: If true, make playlist public
        """
        playlist_id = self.create_playlist(playlist_name, add_date_prefix, public_playlist)
        song_ids = self.get_song_ids(songs)
        self.add_music_to_playlist(playlist_id, song_ids)

        message_base = "All done!"
        if self.music_not_found:
            not_found = "\n\t".join(self.music_not_found)
            logger.info(f"{message_base}\n"
                        f"Couldn't find the following songs,  you'll have to do this manually for now 😥\n\t"
                        f"{not_found}")
        else:
            logger.info(f"{message_base} No songs need to be added manually 🥳")

    def _query_spotify_track(self, artist: str, song_title: str) -> str:
        """
        Query spotify for artist and song title, returning the id
        :param artist: artist
        :param song_title: song title
        :raises IndexError: if no tracks are found
        :return: spotify song id
        """
        results = self.spotify.search(q=f"artist:{artist} track:{song_title}")["tracks"]["items"]
        filtered = [result for result in results if song_title in result['name'].lower()]
        filtered.sort(key=lambda x: len(x["name"]))
        return filtered[0]["id"]

    def _query_spotify_album_tracks(self, album: Music) -> List[str]:
        """
        Query spotify for artist and song title, returning the id
        :param artist: artist
        :param title: album title
        :raises IndexError: if no tracks are found
        :return: spotify song id
        """
        results = self.spotify.search(q=f"artist:{album.artist} album:{album.title}")["tracks"]["items"]
        song_ids = [result["id"] for result in results]

        if song_ids == []:
            self.music_not_found.append(album.to_string())

        return song_ids

    def _get_song_id(self, song: Music) -> str:
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
            song_id = self._query_spotify_track(song.artist, song.title)
        except IndexError:
            # try fixing the strings with removing apostrophes
            try:
                song_id = self._query_spotify_track(song.artist.replace("'", "").replace(".", ""),
                                                    song.title.replace("'", "").replace(".", ""))
            except IndexError:
                self.music_not_found.append(f"{song.to_string()}")
        return song_id
