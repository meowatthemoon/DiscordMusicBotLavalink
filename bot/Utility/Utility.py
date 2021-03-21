import re


def format_input(string):
    string = string.lower()  # -- Lower case
    string = string.replace("\'", "\'\'")  # -- Treat '

    # Remove ()
    string = re.sub(r'\(.*\)', '', string)
    # Remove []
    string = re.sub(r'\[.*\]', '', string)

    # Remove typical words
    typical_words = [',', '\"', '.avi', '.mp3', '.mp4', '.wmv', 'music video', 'lyrics', 'official', 'video']
    for typical_word in typical_words:
        string = string.replace(typical_word, "")

    # Remove blank spaces
    params = string.split(" ")
    while "" in params:
        params.remove("")
    string = ' '.join(params)
    return captitalize_words(string)


def captitalize_words(string):
    return string.title()


async def effiecent_sender(ctx, sentences):
    max_chars = 2000 - 1
    response = ""
    while len(sentences) > 0:
        if len(sentences[0]) > max_chars:
            await ctx.send("ERROR: String with way too many chars, weird?")
            return
        if len(response) + len(sentences[0]) > max_chars:
            await ctx.send(response)
            response = sentences.pop(0)
            continue
        response += sentences.pop(0)
    await ctx.send(response)


def format_seconds(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        time_response = '{:d}:{:02d}:{:02d}'.format(h, m, s)
    elif m > 0:
        time_response = '{:02d}:{:02d}'.format(m, s)
    else:
        print(s)
        time_response = '{:02d}'.format(round(s)) + "s"
    return time_response
