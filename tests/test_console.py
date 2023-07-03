from bbc_meet_spotify.console import console
from bbc_meet_spotify.music import Music
from bbc_meet_spotify.playlist_parsing import PlaylistChoices
from unittest.mock import patch, MagicMock, ANY


def test_invalid_playlist_type():
    try:
        console(PlaylistChoices("invalid"))
    except ValueError:
        pass


@patch("bbc_meet_spotify.console.BBCSounds")
@patch("bbc_meet_spotify.console.Spotify")
def test_add_songs(mock_spotify: MagicMock, mock_bbc_sounds: MagicMock):
    mock_bbc_sounds_instance = mock_bbc_sounds.return_value
    mock_spotify_instance = mock_spotify.return_value
    music = {Music("artist", "title")}
    mock_bbc_sounds_instance.get_music.return_value = music
    playlist_name = "suffix"
    mock_bbc_sounds_instance.playlist_suffix = playlist_name
    console(PlaylistChoices("six_music"))
    mock_bbc_sounds_instance.get_music.assert_called_once()
    mock_spotify_instance.add_albums.assert_not_called()
    mock_spotify_instance.add_songs.assert_called_with(playlist_name, music, ANY, ANY)
    mock_bbc_sounds_instance.write_playlist_history.assert_called_with(music)


@patch("bbc_meet_spotify.console.BBCSounds")
@patch("bbc_meet_spotify.console.Spotify")
def test_add_albums(mock_spotify: MagicMock, mock_bbc_sounds: MagicMock):
    mock_bbc_sounds_instance = mock_bbc_sounds.return_value
    mock_spotify_instance = mock_spotify.return_value
    music = {Music("artist", "title")}
    mock_bbc_sounds_instance.get_music.return_value = music
    mock_bbc_sounds_instance.type = "album"
    playlist_name = "suffix"
    mock_bbc_sounds_instance.playlist_suffix = playlist_name
    console(PlaylistChoices("six_music"))
    mock_bbc_sounds_instance.get_music.assert_called_once()
    mock_spotify_instance.add_albums.assert_called_with(playlist_name, music, ANY, ANY)
    mock_spotify_instance.add_songs.assert_not_called()
    mock_bbc_sounds_instance.write_playlist_history.assert_called_with(music)


@patch("bbc_meet_spotify.console.BBCSounds")
@patch("bbc_meet_spotify.console.Spotify")
def test_exits_when_no_new_music(mock_spotify: MagicMock, mock_bbc_sounds: MagicMock):
    mock_bbc_sounds_instance = mock_bbc_sounds.return_value
    mock_spotify_instance = mock_spotify.return_value
    music = []
    mock_bbc_sounds_instance.get_music.return_value = music
    playlist_name = "suffix"
    mock_bbc_sounds_instance.playlist_suffix = playlist_name
    console(PlaylistChoices("six_music"))
    mock_bbc_sounds_instance.get_music.assert_called_once()
    mock_spotify_instance.add_albums.assert_not_called()
    mock_spotify_instance.add_songs.assert_not_called()
    mock_bbc_sounds_instance.write_playlist_history.assert_not_called()
