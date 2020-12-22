from pathlib import Path

from bbc_meet_spotify import BBCSounds


def test_all_songs_parsed():
    """
    Assuming that there is no previous playlist history, all songs from BBC sounds should be scraped
    """
    test_path = Path(__file__).parent / "test_resources" / "bbc_sounds_6music.html"
    bbc_sounds = BBCSounds(test_path, "testing me", True)

    output_songs = bbc_sounds.get_songs()
    assert len(output_songs) == 33

    # test first song
    assert output_songs[0].artist == "Becca Mancari"
    assert output_songs[0].song_title == "Hunter"

