from pathlib import Path

from bbc_meet_spotify import BBCSounds


class TestPlaylistParsing:
    @staticmethod
    def copy_resources(file_name: str, new_dir: Path):
        resource_file = Path(__file__).parent / "resources" / file_name
        temp_file = new_dir / file_name
        temp_file.touch()
        temp_file.write_text(resource_file.read_text())

    def setup(self):
        test_resources = Path(__file__).parent / "resources"
        self.playlist_config = test_resources / "test_playlists.toml"

    def test_playlist_songs_parsed(self):
        """
        No previous playlist history, all songs from BBC sounds should be scraped
        """

        bbc_sounds = BBCSounds("six_music", True, "testing me", self.playlist_config)

        output_songs = bbc_sounds.get_songs()
        assert len(output_songs) == 33

    def test_show_songs_parsed(self):
        """
         No previous playlist history, all songs from BBC sounds should be scraped
        """
        bbc_sounds = BBCSounds("dance_party_2021_standalone", True, "testing me", self.playlist_config)

        output_songs = bbc_sounds.get_songs()
        assert len(output_songs) == 70

    def test_parsed_shows_are_skipped(self, tmp_path):
        bbc_sounds = BBCSounds("dance_party_2021_standalone", False, "dance_party_2021_test", self.playlist_config)
        bbc_sounds.playlist_history_dir = tmp_path
        self.copy_resources("dance_party_2021_test.toml", tmp_path)
        output_songs = bbc_sounds.get_songs()

        assert output_songs == []

    def test_unparsed_shows_are_scraped(self, tmp_path):
        bbc_sounds = BBCSounds("dance_party_2021_multi", False, "dance_party_2021_test", self.playlist_config)
        bbc_sounds.playlist_history_dir = tmp_path
        self.copy_resources("dance_party_2021_test.toml", tmp_path)

        output_songs = bbc_sounds.get_songs()

        assert len(output_songs) == 63

    def test_chain_of_shows_parsed(self):
        bbc_sounds = BBCSounds("dance_party_2021_multi", True, "testing me", self.playlist_config)
        output_songs = bbc_sounds.get_songs()
        assert len(output_songs) == 70 + 63
