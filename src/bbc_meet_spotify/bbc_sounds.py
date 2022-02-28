from collections import defaultdict
from pathlib import Path
from typing import List, Tuple

import requests
import toml
from bbc_meet_spotify.songs import Song
from bs4 import BeautifulSoup


class BBCSounds:
    def __init__(self, playlist_key: str, date_prefix: bool, playlist_name: str = None,
                 toml_path: Path = Path("./bbc_playlists.toml")):
        """Builds playlist name and gets playlist url from bbc_playists.toml"""
        playlist = self.get_playlist_info(playlist_key, toml_path)
        self.url = playlist["url"]
        self.date_prefix = date_prefix
        if playlist_name:
            self.playlist_suffix = playlist_name
        else:
            self.playlist_suffix = playlist["verbose_name"]
        if playlist["type"] == "playlist":
            self.scraper = PlaylistScraper()
        elif playlist["type"] == "show":
            self.scraper = ShowScraper()

    def get_playlist_info(self, playlist_key: str, toml_path: Path) -> dict:
        """
        Get playlist information for requests playlist
        :param toml_path: path for toml for playlists
        :param playlist_key: key in the toml file
        :return: dictionary of url and verbose name for the playlist
        """
        playlists = toml.load(toml_path)
        if playlist_key:
            playlists = playlists[playlist_key]
        return playlists

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
        current_songs = self.scraper.scrape_bbc_sounds(self.url)

        # get previous songs in playlist
        playlist_history = Path("playlist_history", f"{self.playlist_suffix}.toml")
        if not playlist_history.exists() or self.date_prefix:
            previous_songs = defaultdict(list)
        else:
            previous_songs = defaultdict(list, toml.load(playlist_history))

        # remove songs which have already been seen in previous versions of bbc sounds
        new_songs = [(artist, song_name)
                     for artist, song_name in current_songs
                     if song_name.lower() not in previous_songs[artist.lower()]]

        # merge new songs with previous songs
        for artist, song_name in new_songs:
            previous_songs[artist.lower()].append(song_name.lower())

        # write history of songs to file if not a date-prefixed playlist
        if not self.date_prefix:
            with open(playlist_history, "w") as handle:
                toml.dump(previous_songs, handle)

        # return list of Songs
        return [Song(artist, song_name) for artist, song_name in new_songs]


class ScraperBase:
    @staticmethod
    def read_html(url: str) -> BeautifulSoup:
        """
        Opens url or file path.
        :param url: url/file path to open
        :return: beautiful soup object of the html
        """
        if url.startswith("http") or url.startswith("www."):
            page = requests.get(url)
            soup = BeautifulSoup(page.text, "html.parser")
        else:
            file = Path(__file__).parent.parent.parent / url
            with open(file) as handle:
                page = handle.read()
            soup = BeautifulSoup(page, "html.parser")
        return soup


class ShowScraper(ScraperBase):
    not_broadcasted_message = "This programme will be available shortly after broadcast"

    def scrape_bbc_sounds(self, url) -> List[Tuple[str, str]]:
        more_songs = True
        next_url = url
        songs = []

        while True:
            soup = self.read_html(next_url)
            if self.not_broadcasted_message in soup.text:
                break;

            tracks = soup.find_all(class_="segment__content")
            for track in tracks:
                artist = ", ".join(x.text for x in track.find_all("span", class_="artist"))
                song_name = track.find_all("span", class_="")[0].text
                songs.append((artist, song_name))
            link_to_next = soup.find("a", attrs={"data-bbc-container": "episode", "data-bbc-title": "next:title"})
            next_url = link_to_next["href"]

        return songs


class PlaylistScraper(ScraperBase):
    def scrape_bbc_sounds(self, url: str) -> List[Tuple[str, str]]:
        """
        Get all artist and song names from bbc sounds url
        :return: List of songs in {artist: song_name}
        """
        soup = self.read_html(url)
        # go to after C list and then get all of the tracks before
        header = soup.find(class_="beta")
        for _ in ["B list", "C list", "Album of the day"]:
            header = header.find_next(class_="beta")

        track_strings = []
        song_tag = "p"
        # can be separated by dashes or hyphens
        for separator in [" – ", " - "]:
            for track_tag in header.find_all_previous(song_tag):
                for track_contents in track_tag.contents:
                    track_contents_string = track_contents.text
                    if separator in track_contents_string:
                        track_strings.extend([track_contents_string.strip().split(separator)])

        songs = [(artist, song_name) for artist, song_name in track_strings]
        return songs
