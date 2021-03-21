import sqlite3
import bot.Utility.Utility as Utility


class Database:
    connection = None

    @staticmethod
    def create_database():
        Database.connection = sqlite3.connect('./database.db')

        cursor = Database.connection.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS PLAYLIST(ID INTEGER PRIMARY KEY AUTOINCREMENT, author_id INTEGER, name varchar(30))")
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS SONG_PLAYLIST(video_id varchar(11), playlist_id INT, PRIMARY KEY(video_id, playlist_id))")
        cursor.close()
        Database.connection.commit()

    @staticmethod
    def insert_playlist(playlist_name, author_id):
        playlist_name = Utility.format_input(playlist_name)

        cursor = Database.connection.cursor()
        cursor.execute(f"INSERT INTO PLAYLIST (author_id, name) VALUES ({author_id},'{playlist_name}')")
        cursor.close()

        Database.connection.commit()
        return True

    @staticmethod
    def get_playlists(author_id, playlist_name="", ordered=False):
        playlist_name = Utility.format_input(playlist_name)

        ordered_string = "" if not ordered else " order by name"

        cursor = Database.connection.cursor()
        if playlist_name == "":
            cursor.execute(f"SELECT name,ID FROM PLAYLIST where author_id={author_id}{ordered_string}")
        else:
            cursor.execute(
                f"SELECT name,ID FROM PLAYLIST where name='{playlist_name}' and author_id={author_id} {ordered_string}")
        playlists = cursor.fetchall()
        cursor.close()
        return playlists

    @staticmethod
    def delete_playlist(author_id, playlist_name):
        cursor = Database.connection.cursor()
        cursor.execute(
            f"delete from song_playlist where playlist_id = (select ID from playlist where name = '{playlist_name}' and author_id = {author_id})")
        cursor.execute(f"delete from playlist where name = '{playlist_name}' and author_id = {author_id}")
        cursor.close()
        Database.connection.commit()

    @staticmethod
    def rename_playlist(author_id, old_name, new_name):
        old_name = Utility.format_input(old_name)
        new_name = Utility.format_input(new_name)
        cursor = Database.connection.cursor()
        cursor.execute(f"update playlist set name='{new_name}' where name='{old_name}' and author_id = {author_id}")
        Database.connection.commit()
        cursor.close()

    @staticmethod
    def get_songs_from_playlist(author_id, playlist_name):
        playlist_name = Utility.format_input(playlist_name)

        cursor = Database.connection.cursor()
        cursor.execute(
            f"Select video_id from SONG_PLAYLIST where playlist_id = (Select id from PLAYLIST where name='{playlist_name}' and author_id = {author_id})")
        songs = cursor.fetchall()
        cursor.close()
        return songs

    @staticmethod
    def get_song_from_playlist(author_id, playlist_name, video_id):
        playlist_name = Utility.format_input(playlist_name)

        cursor = Database.connection.cursor()
        cursor.execute(
            f"Select video_id from SONG_PLAYLIST where video_id='{video_id}' and playlist_id = (Select id from PLAYLIST where name='{playlist_name}' and author_id = {author_id})")
        songs = cursor.fetchone()
        cursor.close()
        return songs

    @staticmethod
    def insert_song_into_playlist(author_id, video_id, playlist_name):
        playlists = Database.get_playlists(author_id=author_id, playlist_name=playlist_name)
        if len(playlists) == 0:
            return False

        cursor = Database.connection.cursor()
        try:
            cursor.execute(
                f"INSERT INTO SONG_PLAYLIST (video_id,playlist_id) VALUES ('{video_id}',{playlists[0][1]})")
        except sqlite3.IntegrityError:
            cursor.close()
            return False
        cursor.close()

        Database.connection.commit()
        return True

    @staticmethod
    def delete_song_from_playlist(author_id, playlist_name, video_id):
        playlists = Database.get_playlists(author_id=author_id, playlist_name=playlist_name)
        if len(playlists) == 0:
            return False

        song = Database.get_song_from_playlist(author_id, playlist_name, video_id)
        if not song:
            return False

        playlist_id = playlists[0][1]

        cursor = Database.connection.cursor()

        cursor.execute(f"delete from SONG_PLAYLIST where video_id='{video_id}' and playlist_id={playlist_id}")

        cursor.close()

        Database.connection.commit()
        return True

    @staticmethod
    def song_in_playlist(author_id, playlist_name, video_id):
        print(playlist_name)
        playlist_name = Utility.format_input(playlist_name)

        cursor = Database.connection.cursor()
        cursor.execute(
            f"Select video_id from SONG_PLAYLIST where playlist_id = (Select id from PLAYLIST where name='{playlist_name}' and author_id = {author_id})")
        song = cursor.fetchone()
        cursor.close()
        return song
