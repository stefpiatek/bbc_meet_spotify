from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Union

import requests
import toml
from bs4 import BeautifulSoup
from loguru import logger

from bbc_meet_spotify.songs import Song

class BBCSounds:
    def __init__(self, playlist_key: str, date_prefix: bool, playlist_name: str = None,
                 toml_path: Path = Path("./bbc_playlists.toml")):
        """Builds playlist name and gets playlist url from bbc_playists.toml"""
        self.playlist_history_dir = Path("playlist_history")
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

        # get previous songs in playlist
        playlist_history =  self.playlist_history_dir / f"{self.playlist_suffix}.toml"
        if not playlist_history.exists() or self.date_prefix:
            previous_songs = defaultdict(list)
        else:
            previous_songs = defaultdict(list, toml.load(playlist_history))

        # get all bbc sounds songs
        current_songs = self.scraper.scrape_bbc_sounds(self.url, previous_songs["_parsed_shows"])

        # remove songs which have already been seen in previous versions of bbc sounds
        new_songs = [(artist, song_name)
                     for artist, song_name in current_songs
                     if song_name.lower() not in previous_songs[artist.lower()]]

        # merge new songs with previous songs
        for artist, song_name in new_songs:
            previous_songs[artist.lower()].append(song_name.lower())

        # for shows, track newly added shows
        self.scraper.add_parsed_shows(previous_songs)

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

    def __init__(self):
        self.parsed_urls = set()
        self.not_broadcasted_message = "This programme will be available shortly after broadcast"

    def add_parsed_shows(self, shows: Dict[str, List[str]]):

        shows["_parsed_shows"] = self.parsed_urls

    def scrape_bbc_sounds(self, url: Union[str, Path], parsed_show_urls: List[str]) -> List[Tuple[str, str]]:
        """
        Get all artists and song names for a show, skipping parsed shows
        :param url: first show url
        :param parsed_show_urls: previously parsed show urls
        :return: artists and songs from show
        """
        self.parsed_urls.update(parsed_show_urls)
        songs = self._scrape_show(url, None)

        return songs

    def _scrape_show(self, url: Union[str, Path], songs: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        if songs is None:
            songs = []

        soup = self.read_html(url)
        if self.not_broadcasted_message in soup.text:
            return songs

        show_url = soup.find("link", attrs={"rel": "canonical"})["href"]
        if show_url in self.parsed_urls:
            logger.info(f"Previously scraped show {show_url}, skipping")
        else:
            self.parsed_urls.add(show_url)
            tracks = soup.find_all(class_="segment__content")
            for track in tracks:
                artist = ", ".join(x.text for x in track.find_all("span", class_="artist"))
                song_name = track.find_all("span", class_="")[0].text
                songs.append((artist, song_name))

        link_to_next = soup.find("a", attrs={"data-bbc-container": "episode", "data-bbc-title": "next:title"})
        next_url = link_to_next["href"]
        return self._scrape_show(next_url, songs)


class PlaylistScraper(ScraperBase):
    def scrape_bbc_sounds(self, url: Union[str, Path], parsed_show_urls: List[str]) -> List[Tuple[str, str]]:
        """
        Get all artist and song names from bbc sounds url
        :param url Playlist url
        :param parsed_show_urls not used
        :return: List of songs in (artist, song_name)
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
            track_strings.extend([
                (i.text.strip().split(separator))
                for i in header.find_all_previous(song_tag)
                if separator in i.text
            ])

        songs = [(artist, song_name) for artist, song_name in track_strings]
        return songs

    def add_parsed_shows(self, shows: Dict[str, List[str]]):
        pass
