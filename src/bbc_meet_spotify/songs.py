import re
import unicodedata


class Song:
    def __init__(self, artist, song_title):
        self.song_title = self.clean_string(song_title)
        self.artist = self.clean_string(artist)

    def __repr__(self):
        return f"<{self.get_track_string()}>"

    def get_track_string(self):
        """Get string value for track"""
        return f"{self.artist}: {self.song_title}"

    @staticmethod
    def clean_string(string):
        """
        Converts any accented character to the base type, leaves alphanumeric and apostrophes
        All other characters are replaced with whitespace, finally split at feat. and the first part taken
        :param string: input string to be cleaned
        :return: cleaned string
        """
        new_string = "".join(
            [char for char in unicodedata.normalize("NFD", string) if unicodedata.category(char) != "Mn"]
        )
        new_string = re.sub("[^A-Za-z0-9.'’]+", " ", new_string)
        return new_string.split(" feat.")[0].split(" ft.")[0]