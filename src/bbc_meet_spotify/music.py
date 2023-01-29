import re
import unicodedata

class Music:
    def __init__(self, artist, title):
        self.title = self.clean_string(title)
        self.artist = self.clean_string(artist)

    def __hash__(self):
        return hash(self.to_string())

    def __eq__(self, other):
        return self.artist == other.artist and self.title == other.title

    def __repr__(self):
        return f"<{self.to_string()}>"

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
        return new_string.lower().split(" feat.")[0].split(" ft.")[0]

    def to_string(self):
        """Get string value for album or song"""
        return f"{self.artist}: {self.title}"
