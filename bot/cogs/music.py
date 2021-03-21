import discord
import wavelink
from discord.ext import commands
import re
import bot.Utility.Database as Database
import random
import datetime as dt
import APIs.SpotifyAPI as Spotify
import APIs.LyricsGenius as Lyrics
import bot.Utility.Utility as Utility
import time
import os
import subprocess

URL_REGEX = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"

OPTIONS = {
    "1️⃣": 0,
    "2⃣": 1,
    "3⃣": 2,
    "4⃣": 3,
    "5⃣": 4,
    "6️⃣": 5,
    "7️⃣": 6,
    "8️⃣": 7,
    "9️⃣": 8,
    "🔟": 9
}


class Song:
    def __init__(self, track, search_query=None, author=None, name=None, album_name=None, year=None):
        self.track = track
        self.search_query = search_query
        # print(f"Duration = {track.duration}")  # in milliseconds
        # print(f"Author = {track.author}")  # youtube channel

        self.author = author
        self.name = name
        self.album_name = album_name
        self.year = year

        if not self.author or self.name or self.album_name or self.year:
            # Search Spotify for song information # Todo change from spotify to other song database cuz it gives extra crap
            spotify_data = Spotify.spotify.search(track.title)  # Using the video title
            if spotify_data['tracks']['items']:  # Spotify got results
                item = spotify_data['tracks']['items'][0]
                self.name = item['name']
                self.author = item['artists'][0]['name']
                self.album_name = item['album']['name']
                self.year = item['album']['release_date'][:4]
            elif search_query:
                spotify_data = Spotify.spotify.search(search_query)  # Using the query if exists
                if spotify_data['tracks']['items']:  # Spotify got results
                    item = spotify_data['tracks']['items'][0]
                    self.name = item['name']
                    self.author = item['artists'][0]['name']
                    self.album_name = item['album']['name']
                    self.year = item['album']['release_date'][:4]


class Queue:
    def __init__(self):
        self.queue = []
        self.position = -1

        self.queue_max_size = 1000

    def add_song_to_queue(self, track):
        self.queue.append(track)

        if len(self.queue) > self.queue_max_size:
            del self.queue[0]

    def next_song(self):
        if not self.queue:  # Queue is empty
            return None
        if self.position + 1 >= len(self.queue):  # If all songs have been played
            return

        self.position += 1
        return self.queue[self.position]

    def get_remaining_songs(self):
        return self.queue[self.position:]

    def get_previous_songs(self):
        return self.queue[:self.position]

    def shuffle(self):
        shuffled_songs = []
        while len(self.queue) > self.position + 1:
            index = random.randint(self.position + 1, len(self.queue) - 1)
            shuffled_songs.append(self.queue.pop(index))
        for song in shuffled_songs:
            self.queue.append(song)

    def get_current_song(self):
        if self.position + 1 > len(self.queue):
            return None
        return self.queue[self.position]


class Player(wavelink.Player):
    def __init__(self, *args, **kwargs, ):
        super().__init__(*args, **kwargs)
        self.voice = None
        self.queue = Queue()

        self.play_menu = None
        self.context = None

        self.menu_type = "NONE"
        self.menu_messages = []
        self.menu_content = []
        self.select_embed = None

        self.timestamp = 0
        self.accumulated_time = 0

        self.notifications = []
        self.embed = None

        self.wavelink = None

    def set_wavelink(self, wavelink):
        self.wavelink = wavelink

    async def clear_search_messages(self):
        while len(self.menu_messages) > 0:
            await self.menu_messages[0].delete()
            del self.menu_messages[0]

        if self.select_embed:
            try:
                await self.select_embed.delete()
            except discord.errors.NotFound:
                pass

        self.menu_content = []
        self.menu_type = "NONE"

    async def send_notifications(self, messages):
        for message in self.notifications:
            try:
                await message.delete()
            except discord.errors.NotFound:
                pass
        self.notifications = []

        if type(messages) is list:
            for message in messages:
                self.notifications.append(await self.context.send(message))
        else:
            self.notifications.append(await self.context.send(messages))

    async def send_embed(self, embed):
        if self.embed:
            await self.embed.delete()
        self.embed = self.context.send(embed=embed)

    async def join_channel(self, ctx):
        self.context = ctx
        if not ctx.author.voice:
            await self.send_notifications("> You are not in a voice channel.")
            return False

        channel = self.context.author.voice.channel
        await super().connect(channel.id)
        return True

    async def leave_channel(self):
        await self.destroy()

    async def play_song(self, query, ctx):
        self.context = ctx

        query = query.strip("<>")
        # If it is not a URL
        if re.match(URL_REGEX, query):
            tracks = await self.wavelink.get_tracks(query)
            await self.add_track_to_queue(ctx, tracks[0], query)
            return

        query = f"ytsearch:{query}"

        # Search and add the song to queue
        tracks = await self.wavelink.get_tracks(query)
        if not tracks:
            await self.send_notifications("> No songs found for that query.")
            return

        await self.clear_search_messages()
        self.menu_type = "SONG"

        for track in tracks[:min(len(OPTIONS), len(tracks))]:
            self.menu_content.append(track)

        embed = discord.Embed(
            title=f"Results found for {query}...",
            timestamp=dt.datetime.utcnow()
        )
        # embed.set_author(name =  "Query Results")
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")  # icon_url=ctx.author.avatar.url

        embed = discord.Embed(
            title=f"Choose the song:",
            description=(
                "\n".join(
                    f"**{i + 1}.** {t.title} ({t.length // 60000}:{str(t.length % 60).zfill(2)})"
                    for i, t in enumerate(tracks[:min(len(OPTIONS), len(tracks))])
                )
            ),
            colour=ctx.author.colour,
            timestamp=dt.datetime.utcnow()
        )

        self.select_embed = await ctx.send(embed=embed)
        for emoji in list(OPTIONS.keys())[:min(len(tracks), len(OPTIONS))]:
            try:
                await self.select_embed.add_reaction(emoji)
            except discord.errors.NotFound:
                pass

    async def add_track_to_queue(self, ctx, track, search_query):
        self.context = ctx
        if not track:
            await self.send_notifications("> No song found.")

        # Todo one day
        # if isinstance(tracks, wavelink.TrackPlaylist):
        #    self.queue.add(*tracks.tracks)
        song = Song(track=track, search_query=search_query)
        self.queue.add_song_to_queue(song)
        await self.send_notifications(f"> Added {track.title} to queue.")

        if not self.is_playing:
            await self.next_song(self.context)

    async def next_song(self, ctx=None):
        if ctx:
            self.context = ctx
        song = self.queue.next_song()
        if song:

            self.timestamp = time.time()
            self.accumulated_time = 0

            await self.play(song.track)

            if self.play_menu:
                await self.play_menu.delete()
            self.play_menu = await self.context.send(song.track.uri)
            await self.play_menu.add_reaction("⏸")
            await self.play_menu.add_reaction("▶")
            if self.queue.position > 0:
                await self.play_menu.add_reaction("⏮")

            try:
                await self.play_menu.add_reaction("⏭")
                await self.play_menu.add_reaction("⏹")
                await self.play_menu.add_reaction("🔄")
                await self.play_menu.add_reaction("🔀")
                await self.play_menu.add_reaction("💿")
                await self.play_menu.add_reaction("🎵")
                await self.play_menu.add_reaction("🔉")
                await self.play_menu.add_reaction("🔊")
                await self.play_menu.add_reaction("ℹ️")
            except discord.errors.NotFound:
                pass
        else:
            await self.send_notifications(f"> No more songs in queue.")

    async def shuffle_queue(self, ctx=None):
        if ctx:
            self.context = ctx
        self.queue.shuffle()
        await self.send_notifications("> Shuffled Queue.")

    async def pause(self, ctx=None):
        if ctx:
            self.context = ctx
        if not self.is_playing:
            await self.send_notifications("> No song playing.")
            return
        if self.is_paused:
            await self.send_notifications("> Already paused.")
            return

        self.accumulated_time = time.time() - self.timestamp
        self.timestamp = 0
        await self.set_pause(True)

    async def resume(self, ctx=None):
        if ctx:
            self.context = ctx
        if not self.is_playing:
            await self.send_notifications("> No song playing.")
            return
        if not self.is_paused:
            await self.send_notifications("> Already playing a song.")
            return

        self.timestamp = time.time()
        await self.set_pause(False)

    async def skip(self, ctx=None):
        if ctx:
            self.context = ctx
        if not self.is_playing:
            await self.send_notifications("> No song playing.")
            return
        await self.stop()
        await self.send_notifications("> Skipped.")

    async def back(self, ctx=None):
        if ctx:
            self.context = ctx

        if self.queue.position <= 0:
            await self.send_notifications("> No previous song to go back to.")
            return

        if not self.is_playing:
            await self.send_notifications("> No song playing.")
            return

        self.queue.position -= 2
        await self.stop()

    async def repeat(self, ctx=None):
        if ctx:
            self.context = ctx
        if not self.is_playing:
            await self.send_notifications("> No song playing.")
            return
        await self.seek(0)

    async def increase_volume(self, ctx=None, value=5):
        if ctx:
            self.context = ctx
        await self.set_volume(min(self.volume + value, 100))
        await self.send_notifications(f"> Set volume to {self.volume}.")

    async def decrease_volume(self, ctx=None, value=5):
        if ctx:
            self.context = ctx
        await self.set_volume(max(self.volume - value, 0))
        await self.send_notifications(f"> Set volume to {self.volume}.")

    async def define_volume(self, ctx, value):
        self.context = ctx
        await self.set_volume(max(min(value, 100), 0))
        await self.send_notifications(f"> Set volume to {self.volume}.")

    async def show_lyrics(self, ctx=None):
        if ctx:
            self.context = ctx
        song = self.queue.get_current_song()
        if not song:
            await self.send_notifications(f"> No song playing.")
            return
        if song.author and song.name:

            genius = Lyrics.get_genius()
            artist = genius.search_artist(song.author, max_songs=1)
            if artist:
                song = artist.song(song.name)
                if song:
                    lyrics = song.lyrics
                    embed = discord.Embed(
                        title=f"Lyrics for {song.author} - {song.name}",
                        timestamp=dt.datetime.utcnow()
                    )
                    # embed.set_author(name =  "Query Results")
                    embed.set_footer(text=f"Requested by {ctx.author.display_name}")  # icon_url=ctx.author.avatar.url
                    embed.add_field(name="", value=lyrics, inline=False)
                    await ctx.send(embed=embed)
                    return
        await self.send_notifications("> No lyrics found for current song.")

    async def now_playing(self, ctx=None):
        if ctx:
            self.context = ctx
        if not self.is_playing:
            await self.send_notifications("> No song playing.")
            return

        song = self.queue.get_current_song()
        if not song.name:
            video_title = song.track.title
            spotify_data = Spotify.spotify.search(video_title)

            if len(spotify_data['tracks']['items']) == 0:  # Spotify got results
                await self.send_notifications("> Couldn't get information about song to extract lyrics.")
                return
            item = spotify_data['tracks']['items'][0]
            song.name = item['name']
            song.author = item['artists'][0]['name']
            song.album_name = item['album']['name']
            song.year = item['album']['release_date'][:4]
            self.queue.queue[self.queue.position] = song

        seconds = self.accumulated_time
        if self.timestamp != 0:
            seconds += time.time() - self.timestamp

        passed = Utility.format_seconds(seconds)
        full = Utility.format_seconds(int(self.queue.queue[self.queue.position].track.duration / 1000))

        embed = discord.Embed(
            title=f"{song.author} - {song.name}",
            timestamp=dt.datetime.utcnow()
        )
        embed.add_field(name="Details", value=f"Album : {song.album_name}({song.year})\n Time : {passed} / {full}",
                        inline=False)
        await self.context.send(embed=embed)

    async def reset(self, ctx=None):
        if ctx:
            self.context = ctx

        self.queue.queue = []
        self.queue.position = -1
        self.timestamp = 0
        self.accumulated_time = 0
        if self.is_playing:
            await self.stop()

    async def full_reset(self, ctx=None):
        if ctx:
            self.context = ctx

        await self.reset()

        if self.is_connected:
            await self.disconnect()
        await self.send_notifications("> Queue emptied.")

    async def list_songs_in_queue(self, ctx):
        self.context = ctx
        songs = self.queue.get_remaining_songs()

        if len(songs) == 0:
            await self.send_notifications("> Queue is empty.")
            return
        embed = discord.Embed(
            title="Queue",
            timestamp=dt.datetime.utcnow()
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")  # icon_url=ctx.author.avatar.url
        embed.add_field(name="Currently Playing", value=songs[0].track.title, inline=False)
        if len(songs) > 1:
            embed.add_field(name="Next Up", value="\n".join(song.track.title for song in songs[1:]), inline=False)

        await self.send_embed(embed=embed)

    async def list_songs_in_history(self, ctx):
        self.context = ctx
        songs = self.queue.get_previous_songs()
        if len(songs) == 0:
            await self.send_notifications(">Queue is empty.")
            return
        embed = discord.Embed(
            title="Queue",
            timestamp=dt.datetime.utcnow()
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")  # icon_url=ctx.author.avatar.url
        embed.add_field(name="Next Up", value="\n".join(song.track.title for song in songs), inline=False)

        await self.send_embed(embed=embed)

    async def add_song_to_playlist(self, playlist_name, author_id, ctx=None):
        if ctx:
            self.context = ctx
        if not self.is_playing:
            await self.send_notifications("> No song currently playing to be added.")
            return

        playlists = Database.Database.get_playlists(author_id=author_id, playlist_name=playlist_name)
        if len(playlists) == 0:
            await self.send_notifications(f"> No playlist named {Utility.format_input(playlist_name)}.")
            return

        song = self.queue.get_current_song()
        added = Database.Database.insert_song_into_playlist(author_id=author_id, playlist_name=playlist_name,
                                                            video_id=song.track.ytid)
        if added:
            if song.name and song.author:
                await self.send_notifications(
                    f"> Added {Utility.format_input(song.author)} - {Utility.format_input(song.name)} to {Utility.format_input(playlist_name)}.")
            else:
                await self.send_notifications(
                    f"> Added {Utility.format_input(song.track.title)} to {Utility.format_input(playlist_name)}.")
        else:
            if song.name and song.author:
                await self.send_notifications(
                    f"> Failed to add {Utility.format_input(song.author)} - {Utility.format_input(song.name)} to {Utility.format_input(playlist_name)}.")
            else:
                await self.send_notifications(
                    f"> Failed to add {Utility.format_input(song.track.title)} to {Utility.format_input(playlist_name)}.")

    async def delete_song_from_playlist(self, playlist_name, author_id, ctx=None):
        if ctx:
            self.context = ctx
        if not self.is_playing:
            await self.send_notifications("> No song currently playing to be removed.")
            return

        playlists = Database.Database.get_playlists(author_id=author_id, playlist_name=playlist_name)
        if len(playlists) == 0:
            await self.send_notifications(f"> No playlist named {Utility.format_input(playlist_name)}.")
            return

        song = self.queue.get_current_song()
        added = Database.Database.delete_song_from_playlist(author_id=author_id, playlist_name=playlist_name,
                                                            video_id=song.track.ytid)
        if added:
            if song.name and song.author:
                await self.send_notifications(
                    f"> Deleted {Utility.format_input(song.author)} - {Utility.format_input(song.name)} from {Utility.format_input(playlist_name)}.")
            else:
                await self.send_notifications(
                    f"> Deleted {Utility.format_input(song.track.title)} from {Utility.format_input(playlist_name)}.")
        else:
            if song.name and song.author:
                await self.send_notifications(
                    f"> Failed to delete {Utility.format_input(song.author)} - {Utility.format_input(song.name)} from {Utility.format_input(playlist_name)}.")
            else:
                await self.send_notifications(
                    f"> Failed to delete {Utility.format_input(song.track.title)} from {Utility.format_input(playlist_name)}.")

    async def delete_song_from_queue(self, index, ctx):
        self.context = ctx

        try:
            index = int(index)
        except ValueError:
            await self.send_notifications("> You need to provide the index integer.")
            return

        if index <= 0:
            await self.send_notifications("> Index must be a positive value.")
            return

        index = index + self.queue.position
        if index > len(self.queue.queue) - 1:
            await self.send_notifications("> Index doesn't exist.")
            return
        del self.queue.queue[index]
        await self.send_notifications("> Removed song from Queue.")

    async def play_playlist(self, playlist_name, ctx=None, author_id=None):
        if ctx:
            self.context = ctx
            author_id = ctx.message.author.id
        else:
            if not author_id:
                await self.send_notifications("> Can't play playlist...")
                return

        await self.reset()

        if playlist_name == "":
            playlists = Database.Database.get_playlists(author_id=author_id, ordered=True)

            if len(playlists) == 0:
                await self.send_notifications("> You have no playlists yet.")
                return

            await self.clear_search_messages()
            self.menu_type = "PLAYLIST"

            # Show them
            for playlist in playlists:
                message = await self.context.send(f"> {playlist[0]}\n")
                self.menu_messages.append(message)
                self.menu_content.append(playlist[0])  # The name
                await message.add_reaction("➡️")
            self.menu_user_request_id = ctx.message.author.id
            return

        playlists = Database.Database.get_playlists(author_id=author_id, playlist_name=playlist_name)
        if len(playlists) == 0:
            await self.send_notifications(f"> No playlist named:{Utility.format_input(playlist_name)}.")
            return

        video_ids = Database.Database.get_songs_from_playlist(author_id=author_id,
                                                              playlist_name=playlist_name)
        if len(video_ids) == 0:
            await self.send_notifications(f"> {Utility.format_input(playlist_name)} has no songs.")
            return

        for video_id in video_ids:
            video_id = video_id[0]
            url = f"https://www.youtube.com/watch?v={video_id}"
            tracks = await self.wavelink.get_tracks(url)
            song = Song(track=tracks[0])
            self.queue.queue.append(song)

        await self.send_notifications(f"> Playing {Utility.format_input(playlist_name)} with {len(video_ids)} songs.")
        await self.next_song()

    async def list_playlists(self, ctx):
        self.context = ctx
        self.menu_user_request_id = ctx.message.author.id

        playlists = Database.Database.get_playlists(author_id=ctx.message.author.id, ordered=True)

        if len(playlists) == 0:
            await self.send_notifications("> You have no playlists yet.")
            return

        await self.clear_search_messages()
        self.menu_type = "PLAYLIST"

        # Show them
        for playlist in playlists:
            message = await ctx.send("> " + Utility.captitalize_words(playlist[0] + "\n"))
            self.menu_messages.append(message)

            self.menu_content.append(playlist[0])  # The name
            await message.add_reaction("➡️")
            await message.add_reaction("❌")

    async def save_queue_as_playlist(self, playlist_name, ctx):
        self.context = ctx
        if playlist_name == "":
            await self.send_notifications("> You forgot the name of the playlist.")
            return

        playlists = Database.Database.get_playlists(author_id=ctx.message.id, playlist_name=playlist_name)
        if len(playlists) != 0:
            await self.send_notifications("> Playlist already exists in database.")
            return

        inserted = Database.Database.insert_playlist(author_id=ctx.message.author.id, playlist_name=playlist_name)
        if inserted:
            await self.send_notifications(f"> Created playlist {Utility.format_input(playlist_name)}.")
        else:
            await self.send_notifications("> Failed to create playlist.")

        for index in range(self.queue.position, len(self.queue.queue)):
            Database.Database.insert_song_into_playlist(author_id=ctx.message.author.id,
                                                        video_id=self.queue.queue[index].video_id,
                                                        playlist_name=playlist_name)

    async def create_playlist(self, playlist_name, ctx):
        self.context = ctx
        if playlist_name == "":
            await self.send_notifications("> You forgot the name of the playlist.")
            return

        playlists = Database.Database.get_playlists(author_id=ctx.message.author.id, playlist_name=playlist_name)
        if len(playlists) != 0:
            await self.send_notifications("> Playlist already exists in database.")
            return

        inserted = Database.Database.insert_playlist(playlist_name, ctx.message.author.id)
        if inserted:
            await self.send_notifications(f"> Created playlist {playlist_name}.")
        else:
            await self.send_notifications("> Failed to create playlist.")

    async def rename_playlist(self, input, ctx):
        self.context = ctx
        params = input.split("->")

        if len(params) < 2:
            await self.send_notifications("> Please separate previous name and new name with \"->\".")
            return

        playlists = Database.Database.get_playlists(author_id=ctx.message.author.id, playlist_name=params[0])
        if len(playlists) == 0:
            await self.send_notifications(f"> No playlist named {params[0]}.")
            return

        Database.Database.rename_playlist(ctx.message.author.id, params[0], params[1])
        await self.send_notifications(f"> Renamed {params[0]} to {params[1]}.")

    async def delete_playlist(self, playlist_name, ctx=None):
        if ctx:
            self.context = ctx
        if playlist_name:
            playlists = Database.Database.get_playlists(author_id=ctx.message.author.id, playlist_name=playlist_name)
            if len(playlists) == 0:
                await self.context.send(f"> No playlist named {Utility.format_input(playlist_name)}.")

            Database.Database.delete_playlist(author_id=ctx.message.author.id, playlist_name=playlist_name)
            await self.send_notifications(f"> Deleted {Utility.format_input(playlist_name)}.")
        else:
            # TODO
            print("Implement me")

    async def list_playlists_to_add_remove_song(self, payload):
        if not self.is_playing:
            return

        self.menu_user_request_id = payload.user_id
        await self.clear_search_messages()

        playlists = Database.Database.get_playlists(author_id=self.menu_user_request_id, ordered=True)
        if len(playlists) == 0:
            await self.send_notifications("> You have no playlists yet.")
            return

        self.menu_type = "ADD_REMOVE_SONG_TO_PLAYLIST"
        # Show them
        for playlist in playlists:
            message = await self.context.send(f"> {playlist[0]}\n")
            self.menu_messages.append(message)

            self.menu_content.append(
                {"playlist_name": playlist[0], "video_id": self.queue.get_current_song().track.ytid})
            if Database.Database.song_in_playlist(author_id=self.menu_user_request_id, playlist_name=playlist[0],
                                                  video_id=self.queue.get_current_song().track.ytid):
                await message.add_reaction("❌")
            else:
                await message.add_reaction("✅")

    async def list_songs_in_playlist(self, playlist_name, ctx):
        self.context = ctx
        if playlist_name == "":
            await self.send_notifications("> Specify playlist's name.")
            return

        playlists = Database.Database.get_playlists(author_id=ctx.message.author.id, playlist_name=playlist_name)
        if len(playlists) == 0:
            await self.send_notifications("> Playlist does not exist.")
            return

        video_ids = Database.Database.get_songs_from_playlist(author_id=ctx.message.author.id,
                                                              playlist_name=playlist_name)
        if len(video_ids) == 0:
            await self.send_notifications(f"> {Utility.format_input(playlist_name)} has no songs.")
            return

        embed = discord.Embed(
            title=f"{playlist_name}",
            timestamp=dt.datetime.utcnow()
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        for song in video_ids:
            video_id = song[0]

            url = f"https://www.youtube.com/watch?v={video_id}"
            tracks = await self.wavelink.get_tracks(url)
            song = Song(track=tracks[0])
            title = tracks[0].title
            if song.author and song.name:
                title = f"{song.author} - {song.name}"
            value = ""
            if song.album_name:
                value += f"{song.album_name}"
            if song.year:
                value += f" ({song.year})"
            if not value:
                value = "album unknown"
            embed.add_field(name=title, value=value, inline=False)

        await self.context.send_notifications(embed=embed)

    async def play_album(self, album_name, ctx):
        self.context = ctx

        await self.clear_search_messages()

        if input == "":
            await self.send_notifications("> Specify album to search.")
            return

        spotify_data = Spotify.spotify.search_album(album_name)

        if len(spotify_data["albums"]["items"]) == 0:
            await self.send_notifications("> No results found.")
            return

        self.menu_type = "ALBUM"

        albums = spotify_data['albums']['items']
        albums = albums[:min(10, len(albums))]
        for album in albums:
            album_id = album['id']
            artist = album['artists'][0]['name']
            album_name = album['name']
            album_year = album['release_date'][:4]

            message = await self.context.send(
                f"{Utility.format_input(album_name)} ({album_year}) by {Utility.format_input(artist)}.")
            self.menu_messages.append(message)
            self.menu_content.append(
                {"artist": artist, "album": album_name, "album_year": album_year, "album_id": album_id})
            await message.add_reaction("➡️")

    async def search_select(self, payload):
        if self.context.message.author.voice:
            if not await self.join_channel(self.context):
                return

        content = None
        for index, message in enumerate(self.menu_messages):
            if message.id == payload.message_id:
                content = self.menu_content[index]
                break

        if self.menu_type == "SONG":

            index = OPTIONS[payload.emoji.name]
            song = Song(track=self.menu_content[index])
            await self.clear_search_messages()
            self.queue.queue.append(song)
            if not self.is_playing:
                await self.next_song()

        elif self.menu_type == "ALBUM":
            await self.clear_search_messages()
            await self.reset()

            tracks = Spotify.spotify.get_album(content["album_id"])['tracks']['items']
            for track in tracks:
                song_name = track['name']
                query = f"ytsearch:{content['artist']} - {song_name}"

                # Search and add the song to queue
                tracks = await self.wavelink.get_tracks(query)
                if not tracks:
                    await self.send_notifications(
                        f"> Couldn't find song: {Utility.format_input(content['artist'])} - {Utility.format_input(song_name)}.")
                    continue

                song = Song(track=tracks[0], name=song_name, author=content["artist"], album_name=content["album"],
                            year=content["album_year"])
                self.queue.queue.append(song)

            await self.send_notifications(
                F"> Playing {Utility.format_input(content['album'])} ({Utility.format_input(content['album_year'])}) by {Utility.format_input(content['artist'])}  with {len(self.queue.queue)} songs.")

            await self.next_song()

        elif self.menu_type == "PLAYLIST":
            await self.clear_search_messages()
            if payload.emoji.name == "➡️":
                await self.play_playlist(playlist_name=content, author_id=self.menu_user_request_id)
            elif payload.emoji.name == "❌":
                await self.delete_playlist(playlist_name=content)

        elif self.menu_type == "ADD_REMOVE_SONG_TO_PLAYLIST":
            await self.clear_search_messages()
            # author_id = payload.user_id
            if payload.emoji.name == "✅":
                playlists = Database.Database.get_playlists(author_id=self.menu_user_request_id,
                                                            playlist_name=content["playlist_name"])
                if len(playlists) == 0:
                    await self.send_notifications(
                        f"> No playlist named {Utility.format_input(content['playlist_name'])}.")
                    return

                video_id = content["video_id"]
                added = Database.Database.insert_song_into_playlist(author_id=self.menu_user_request_id,
                                                                    playlist_name=content["playlist_name"],
                                                                    video_id=video_id)
                if added:
                    await self.send_notifications(f"> Added song to {Utility.format_input(content['playlist_name'])}.")
                else:
                    await self.send_notifications(
                        f"> Song already exists in {Utility.format_input(content['playlist_name'])}.")
            elif payload.emoji.name == "❌":
                playlists = Database.Database.get_playlists(author_id=self.menu_user_request_id,
                                                            playlist_name=content["playlist_name"])
                if len(playlists) == 0:
                    await self.send_notifications(
                        f"> No playlist named {Utility.format_input(content['playlist_name'])}.")
                    return

                video_id = content["video_id"]
                removed = Database.Database.delete_song_from_playlist(author_id=self.menu_user_request_id,
                                                                      playlist_name=content["playlist_name"],
                                                                      video_id=video_id)
                if removed:
                    await self.send_notifications(
                        f"> Deleted song from {Utility.format_input(content['playlist_name'])}.")
                else:
                    await self.send_notifications(
                        f"> Song doesn't exist in {Utility.format_input(content['playlist_name'])}.")
        else:
            print("IMPLEMENT ME " + self.menu_type)

        await self.clear_search_messages()


class Music(commands.Cog, wavelink.WavelinkMixin):
    def __init__(self, bot):
        self.bot = bot
        self.wavelink = wavelink.Client(bot=bot)
        self.bot.loop.create_task(self.start_nodes())

    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self, node):
        print(f"Wavelink node {node.identifier} ready.")

    async def start_nodes(self):
        await self.bot.wait_until_ready()

        nodes = {
            "MAIN": {
                "host": "127.0.0.1",
                "port": 2333,
                "rest_uri": "http://127.0.0.1:2333",
                "password": "youshallnotpass",
                "identifier": "MAIN",
                "region": "europe"
            }
        }
        """
        nodes = {
            "MAIN":
            {
                "host": "test-lavalink.herokuapp.com",
                "port": 80,
                "rest_url": "http://alitamusicbot.herokuapp.com",
                "password": "youshallnotpass",
                "identifier": "MAIN",
                "region": "europe"
            }
        }
        """

        for node in nodes.values():
            await self.wavelink.initiate_node(**node)

    def get_player(self, obj):
        if isinstance(obj, commands.Context):
            player = self.wavelink.get_player(obj.guild.id, cls=Player, context=obj)
        elif isinstance(obj, discord.Guild):
            player = self.wavelink.get_player(obj.id, cls=Player)
        player.set_wavelink(self.wavelink)
        return player

    # Automatically leaves the channel if nobody is in it
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not member.bot and after.channel is None:
            if not [m for m in before.channel.members if not m.bot]:
                await self.get_player(member.guild).destroy()

    @wavelink.WavelinkMixin.listener("on_track_stuck")
    @wavelink.WavelinkMixin.listener("on_track_end")
    @wavelink.WavelinkMixin.listener("on_track_exception")
    async def on_player_stop(self, node, payload):
        await payload.player.next_song()

    @commands.command(name="join", aliases=["connect"])
    async def join_channel(self, ctx):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.join_channel(ctx)

    @commands.command(name="leave", aliases=["disconnect"])
    async def leave_channel(self, ctx):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.disconnect()

    @commands.command(name="Queue", aliases=['q'])
    async def list_tracks_in_queue(self, ctx):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.list_songs_in_queue(ctx)

    @commands.command(name="History", )
    async def list_tracks_in_history(self, ctx):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.list_songs_in_history(ctx)

    @commands.command(name="play")
    async def play(self, ctx, *, query):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.play_song(query, ctx)

    @commands.command(pass_context=True, aliases=['sh', 'shuffle'])
    async def shuffle_queue(self, ctx):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.shuffle_queue()

    @commands.command(pass_context=True)
    async def pause(self, ctx):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.pause(ctx)

    @commands.command(pass_context=True)
    async def resume(self, ctx):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.resume(ctx)

    @commands.command(pass_context=True)
    async def skip(self, ctx):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.skip(ctx)

    @commands.command(pass_context=True, aliases=['back', 'previous'])
    async def previous_song(self, ctx):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.back(ctx)

    @commands.command(pass_context=True)
    async def seek(self, ctx, *, query):
        player = self.get_player(ctx)
        print("Implement me")

    @commands.command(pass_context=True)
    async def repeat(self, ctx):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.repeat(ctx)

    @commands.command(pass_context=True)
    async def volume(self, ctx, value: int):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.define_volume(ctx, value)

    @commands.command(pass_context=True, aliases=['lyrics'])
    async def list_lyrics(self, ctx):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.show_lyrics(ctx)

    @commands.command(pass_context=True)
    async def reset(self, ctx):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.full_reset(ctx)

    @commands.command(pass_context=True, aliases=['np'])
    async def now_playing(self, ctx):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.now_playing(ctx)

    ##### PLAYLISTS #####
    @commands.command(pass_context=True, aliases=['cp'])
    async def create_playlist(self, ctx, *, playlist_name: str = ""):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.create_playlist(playlist_name=playlist_name, ctx=ctx)

    @commands.command(pass_context=True, aliases=['rp'])
    async def rename_playlist(self, ctx, *, input: str = ""):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.rename_playlist(input=input, ctx=ctx)

    @commands.command(pass_context=True, aliases=['dp'])
    async def delete_playlist(self, ctx, *, playlist_name: str = ""):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.delete_playlist(playlist_name=playlist_name, ctx=ctx)

    @commands.command(pass_context=True, aliases=['rsq', 'dsq', 'remove'])
    async def delete_song_from_queue(self, ctx, index: str):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.delete_song_from_queue(index=index, ctx=ctx)

    @commands.command(pass_context=True, aliases=['lp'])
    async def list_playlists(self, ctx):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.list_playlists(ctx)

    @commands.command(pass_context=True, aliases=['lsp'])
    async def list_songs_in_playlist(self, ctx, *, playlist_name: str = ""):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.list_songs_in_playlist(playlist_name=playlist_name, ctx=ctx)

    @commands.command(pass_context=True, aliases=['asp'])
    async def add_song_to_playlist(self, ctx, *, playlist_name: str):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.add_song_to_playlist(author_id=ctx.message.author.id, playlist_name=playlist_name, ctx=ctx)

    @commands.command(pass_context=True, aliases=['dsp', 'rsp'])
    async def delete_song_from_playlist(self, ctx, *, playlist_name: str):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.delete_song_from_playlist(playlist_name=playlist_name, author_id=ctx.message.author.id, ctx=ctx)

    @commands.command(pass_context=True, aliases=['playp'])
    async def play_playlist(self, ctx, *, playlist_name: str = ""):
        await ctx.message.delete()
        player = self.get_player(ctx)

        if not await player.join_channel(ctx):
            return

        await player.play_playlist(playlist_name=playlist_name, ctx=ctx)

    @commands.command(pass_context=True, aliases=['sq', 'save'])
    async def save_queue(self, ctx, *, playlist_name: str):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.save_queue_as_playlist(playlist_name=playlist_name, ctx=ctx)

    @commands.command(pass_context=True, aliases=['playa'])
    async def play_album(self, ctx, *, album_name: str):
        await ctx.message.delete()
        player = self.get_player(ctx)
        await player.play_album(album_name=album_name, ctx=ctx)

    # ---------------------- PROCESSING --------------------------#
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        await self.process_reaction(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        await self.process_reaction(payload)

    async def process_reaction(self, payload):
        if payload.member and payload.member.bot:
            return

        guild = self.bot.get_guild(payload.guild_id)
        player = self.get_player(guild)

        if payload.emoji.name == "⏭":
            await player.skip()
        elif payload.emoji.name == "⏸":
            await player.pause()
        elif payload.emoji.name == "▶":
            await player.resume()
        elif payload.emoji.name == "⏹":
            await player.full_reset()
        elif payload.emoji.name == "⏮":
            await player.back()
        elif payload.emoji.name == "🔀":
            await player.shuffle_queue()
        elif payload.emoji.name == "➡️":
            await player.search_select(payload)
        elif payload.emoji.name == "💿":
            await player.list_playlists_to_add_remove_song(payload)
        elif payload.emoji.name == "✅":
            await player.search_select(payload)
        elif payload.emoji.name == "❌":
            await player.search_select(payload)
        elif payload.emoji.name == "🎵":
            await player.show_lyrics()
        elif payload.emoji.name == "🔉":
            await player.decrease_volume()
        elif payload.emoji.name == "🔊":
            await player.increase_volume()
        elif payload.emoji.name == "🔄":
            await player.repeat()
        elif payload.emoji.name == "ℹ️":
            await player.now_playing()
        elif payload.emoji.name in ("1️⃣", "2⃣", "3⃣", "4⃣", "5⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"):
            await player.search_select(payload)
        else:
            print(payload.emoji.name)


def start():
    popen = subprocess.Popen(['java', '-jar', 'Lavalink.jar'], stdout=subprocess.PIPE, universal_newlines=True)
    for line in iter(popen.stdout.readline, ""):
        yield line
    popen.stdout.close()


def start_lavalink():
    os.chdir("./jdk/bin")
    for line in start():
        print(line)
        if "You can safely ignore" in line:
            break

    print("Started Lavalink")
    os.chdir("../../")


def setup(bot):
    start_lavalink()
    Database.Database.create_database()
    bot.add_cog(Music(bot))
