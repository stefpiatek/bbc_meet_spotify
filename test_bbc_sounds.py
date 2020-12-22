from pathlib import Path

from bbc_meet_spotify import BBCSounds


def test_all_songs_parsed():
    """
    Assuming that there is no previous playlist history, all songs from BBC sounds should be scraped
    """

    test_resources = Path(__file__).parent / "tests" / "resources"
    bbc_sounds = BBCSounds("six_music", True, "testing me", test_resources / "test_playlists.toml")

    output_songs = bbc_sounds.get_songs()
    assert len(output_songs) == 33

    # test first song (reverse order)
    assert output_songs[0].artist == "Tim Burgess"
    assert output_songs[0].song_title == "Laurie"
    # test last song (reverse order)
    assert output_songs[-1].artist == "Becca Mancari"
    assert output_songs[-1].song_title == "Hunter"
