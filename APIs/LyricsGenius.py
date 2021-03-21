import lyricsgenius

with open("./APIs/lyricsgenius_token.o", "r", encoding="utf-8") as f:
    TOKEN = f.read()


def get_genius():
    return lyricsgenius.Genius(TOKEN)

