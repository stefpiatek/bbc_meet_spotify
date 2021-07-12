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

        output_songs = bbc_sounds.get_music()
        assert len(output_songs) == 33
        # test first song
        assert output_songs[0].artist == "becca mancari"
        assert output_songs[0].title == "hunter"

        # test last song
        assert output_songs[-1].artist == "tim burgess"
        assert output_songs[-1].title == "laurie"

    def test_show_songs_parsed(self):
        """
         No previous playlist history, all songs from BBC sounds should be scraped
        """
        bbc_sounds = BBCSounds("dance_party_2021_standalone", True, "testing me", self.playlist_config)

        output_songs = bbc_sounds.get_music()
        assert len(output_songs) == 70
        assert output_songs[0].artist == "eric prydz"
        assert output_songs[0].title == "nopus"
        # test last song (reverse order)
        assert output_songs[-1].artist == "maduk"
        assert output_songs[-1].title == "come back to me"
        # check multiple artist doesn't break it
        assert output_songs[1].title == "i remember"
        assert output_songs[2].title == "channel 43"
        assert output_songs[5].title == "hands in the air"

    def test_parsed_shows_are_skipped(self, tmp_path):
        bbc_sounds = BBCSounds("dance_party_2021_standalone", False, "dance_party_2021_test", self.playlist_config)
        bbc_sounds.playlist_history_dir = tmp_path
        self.copy_resources("dance_party_2021_test.toml", tmp_path)
        output_songs = bbc_sounds.get_music()

        assert output_songs == []

    def test_parsed_shows_log(self, tmp_path, caplog):
        bbc_sounds = BBCSounds("dance_party_2021_standalone", False, "dance_party_2021_test", self.playlist_config)
        bbc_sounds.playlist_history_dir = tmp_path
        self.copy_resources("dance_party_2021_test.toml", tmp_path)
        bbc_sounds.get_music()

        assert "Previously scraped show" in caplog.text

    def test_unparsed_shows_are_scraped(self, tmp_path):
        bbc_sounds = BBCSounds("dance_party_2021_multi", False, "dance_party_2021_test", self.playlist_config)
        bbc_sounds.playlist_history_dir = tmp_path
        self.copy_resources("dance_party_2021_test.toml", tmp_path)

        output_songs = bbc_sounds.get_music()

        assert len(output_songs) == 63

    def test_chain_of_shows_parsed(self):
        bbc_sounds = BBCSounds("dance_party_2021_multi", True, "testing me", self.playlist_config)
        output_songs = bbc_sounds.get_music()
        assert len(output_songs) == 70 + 63
