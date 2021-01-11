from pathlib import Path

from bbc_meet_spotify import BBCSounds


class TestPlaylistParsing:
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

        # test first song (reverse order)
        assert output_songs[0].artist == "Tim Burgess"
        assert output_songs[0].song_title == "Laurie"
        # test last song (reverse order)
        assert output_songs[-1].artist == "Becca Mancari"
        assert output_songs[-1].song_title == "Hunter"

    def test_show_songs_parsed(self):
        """
         No previous playlist history, all songs from BBC sounds should be scraped
        """
        bbc_sounds = BBCSounds("dance_party_2021", True, "testing me", self.playlist_config)

        output_songs = bbc_sounds.get_songs()
        assert len(output_songs) == 70
        assert output_songs[0].artist == "Eric Prydz"
        assert output_songs[0].song_title == "NOPUS"
        # test last song (reverse order)
        assert output_songs[-1].artist == "Maduk"
        assert output_songs[-1].song_title == "Come Back To Me"
        # check multiple artist doesn't break it
        assert output_songs[1].song_title == "I Remember"
        assert output_songs[2].song_title == "Channel 43"
        assert output_songs[5].song_title == "Hands In The Air"

