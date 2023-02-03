import itertools
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple, Union

import requests
import toml
from bs4 import BeautifulSoup
from loguru import logger
from ordered_set import OrderedSet

from .music import Music


class BBCSounds:
    def __init__(self, playlist_key: str, date_prefix: bool, playlist_name: str = None,
                 toml_path: Path = Path("./bbc_playlists.toml"), history_dir: Path = Path("./playlist_history")):
        self.history_dir = history_dir
        self.playlist = self.get_playlist_info(playlist_key, toml_path)
        self.url = self.playlist["url"]
        self.type = self.playlist["type"]
        self.date_prefix = date_prefix
        self.playlist_suffix = self.get_playlist_suffix(self.playlist, playlist_name)
        self.scraper = self.get_scraper_type(self.type)

    @staticmethod
    def get_scraper_type(playlist_type: str):
        if playlist_type == "playlist":
            return PlaylistScraper()
        elif playlist_type == "show":
            return ShowScraper()
        elif playlist_type == "album":
            return AlbumScraper()

    @staticmethod
    def get_playlist_suffix(playlist: dict, playlist_name: str) -> str:
        if playlist_name:
            return playlist_name
        else:
            return playlist["verbose_name"]

    @staticmethod
    def get_playlist_info(playlist_key: str, toml_path: Path) -> dict:
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

    def get_music(self) -> Set[Music]:
        previous_music = self._get_playlist_history(self._get_playlist_history_path())

        # get all bbc sounds music
        current_music = self.scraper.scrape_bbc_sounds(self.url, previous_music["_parsed_shows"])

        # remove songs/albums which have already been seen in previous versions of bbc sounds
        new_music = OrderedSet(Music(artist, title)
                               for artist, title in current_music
                               if Music.clean_string(title) not in previous_music[Music.clean_string(artist)])

        return new_music

    def write_playlist_history(self, new_music: Set[Music]) -> None:
        playlist_history_path = self._get_playlist_history_path()
        previous_music = self._get_playlist_history(playlist_history_path)
        # merge new songs/albums with previous songs
        for music in new_music:
            previous_music[music.artist].append(music.title)
        # for shows, track newly added shows
        self.scraper.add_parsed_shows(previous_music)
        # write history of songs to file if not a date-prefixed playlist
        if not self.date_prefix:
            with open(playlist_history_path, "w") as handle:
                toml.dump(previous_music, handle)
                logger.info("Successfully updated playlist history")

    def _get_playlist_history_path(self) -> str:
        return self.history_dir / f"{self.playlist_suffix}.toml"

    def _get_playlist_history(self, playlist_history_path: str) -> dict:
        if not playlist_history_path.exists() or self.date_prefix:
            previous_music = defaultdict(list)
        else:
            previous_music = defaultdict(list, toml.load(playlist_history_path))
        return previous_music


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


class AlbumScraper(ScraperBase):
    def scrape_bbc_sounds(self, url: Union[str, Path], parsed_show_urls: List[str]) -> List[Tuple[str, str]]:
        """
        Get all artist and album names from bbc sounds url
        :param url Playlist url
        :param parsed_show_urls not used
        :return: List of ablums in (artist, album_name)
        """
        soup = self.read_html(url)
        # go to after C list and then get all of the tracks before
        header = soup.find(class_="beta")
        for _ in ["B list", "C list", "Album of the day"]:
            header = header.find_next(class_="beta")

        album_strings = []
        album_tag = "p"
        # can be separated by dashes or hyphens
        for separator in [":"]:
            album_strings.extend([
                (i.text.strip().split(separator))
                for i in header.find_all_next(album_tag)
                if separator in i.text
            ])

        by = " by "
        albums = []
        for album_parts in album_strings:
            album_artist_selected = album_parts[1]
            album_name = album_artist_selected.split(by)[0].strip()
            artist = album_artist_selected.split(", selected by")[0].lstrip(f"{album_name}{by}").strip()
            albums.append((artist, album_name))
        return albums

    def add_parsed_shows(self, shows: Dict[str, List[str]]):
        pass


class ShowScraper(ScraperBase):

    def __init__(self):
        self.parsed_urls = OrderedSet()
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
        soup.preserve_whitespace_tags = 'br'
        # go to after C list and then get all of the tracks before
        header = soup.find(class_="beta")
        for _ in ["B list", "C list", "Album of the day"]:
            header = header.find_next(class_="beta")

        track_strings = []
        song_tag = "p"
        # keep br tags as sometimes they don't always use p in playlist
        for br in soup.find_all("br"):
            br.replace_with("\n")

        # can be separated by dashes or hyphens
        for separator in [" – ", " - "]:
            track_strings.extend([
                (i.text.split(separator))
                for i in header.find_all_previous(song_tag)
                if separator in i.text
            ])

        songs = []

        for track_tuple in track_strings:
            if len(track_tuple) == 2:
                artist, song_name = track_tuple
                songs.append((artist.strip(), song_name.strip()))
            elif len(track_tuple) > 2:
                br_separated_tracks = list(itertools.chain.from_iterable(i.split("\n\n") for i in track_tuple))
                for artist, song_name in zip(*[iter(br_separated_tracks)]*2):
                    songs.append((artist.strip(), song_name.strip()))
        # parsed backwards so correct it back to the right order
        songs.reverse()
        return songs

    def add_parsed_shows(self, shows: Dict[str, List[str]]):
        pass
