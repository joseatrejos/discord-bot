import pytz, os
import sqlite3, datetime
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# If this script is run directly
if __name__ == "__main__":
    if os.getenv('DEBUG') == "False":
        DB_DIR = Path(__file__).cwd().parent / 'db/data.db'
    else:
        DB_DIR = Path(__file__).cwd().parent / 'db/data_dev.db'
else:
    if os.getenv("DEBUG") == "False":
        DB_DIR = Path(__file__).cwd().parent / 'db/data.db'
    else:
        DB_DIR = Path(__file__).cwd().parent / 'db/data_dev.db'


def create_table_if_not_exists(location = DB_DIR, table_name="employee_users"):
    """Create a table if it does not already exist"""
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    # sql = f'''DROP TABLE IF EXISTS recurring_meeting_hour'''
    # cursor.execute(sql)

    # Create user table
    sql = f'''CREATE TABLE IF NOT EXISTS {table_name}(
        id INTEGER PRIMARY KEY,
        name TEXT,
        nickname TEXT,
        discord_user TEXT,
        birthday DATE DEFAULT NULL
    )'''
    cursor.execute(sql)

    # Create playlist table
    sql = f'''CREATE TABLE IF NOT EXISTS playlist(
        id INTEGER PRIMARY KEY,
        name TEXT
    )'''
    cursor.execute(sql)

    # Create playlist_song table
    sql = f'''CREATE TABLE IF NOT EXISTS playlist_song(
        id INTEGER PRIMARY KEY,
        playlist_id INTEGER,
        song_name TEXT
    )'''
    cursor.execute(sql)

    # Create timer table
    sql = f'''CREATE TABLE IF NOT EXISTS timer(
        id INTEGER PRIMARY KEY,
        active INTEGER DEFAULT 0
    )'''
    cursor.execute(sql)

    # Create reminder table
    sql = f'''CREATE TABLE IF NOT EXISTS reminder(
        id INTEGER PRIMARY KEY,
        reminder TEXT,
        date DATE,
        time TEXT,
        user_id INTEGER
    )'''
    cursor.execute(sql)

    # Create meeting table
    sql = f'''CREATE TABLE IF NOT EXISTS meeting(
        id INTEGER PRIMARY KEY,
        meeting_name TEXT,
        date DATE,
        time TEXT
    )
    '''
    cursor.execute(sql)

    # Create meeting_attendees table
    sql = f'''CREATE TABLE IF NOT EXISTS meeting_attendees(
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        meeting_id INTEGER
    )
    '''
    cursor.execute(sql)

    # Create meeting_roles table
    sql = f'''CREATE TABLE IF NOT EXISTS meeting_roles(
        id INTEGER PRIMARY KEY,
        role TEXT,
        meeting_id INTEGER
    )
    '''
    cursor.execute(sql)

    # Create weekday table
    sql = f'''CREATE TABLE IF NOT EXISTS weekday(
        id INTEGER PRIMARY KEY,
        weekday TEXT
    )
    '''
    cursor.execute(sql)

    # Create recurring_meeting table
    sql = f'''CREATE TABLE IF NOT EXISTS recurring_meeting(
        id INTEGER PRIMARY KEY,
        meeting_name TEXT,
        weekday_id INTEGER,
        time TEXT
    )
    '''
    cursor.execute(sql)

    # Create recurring_meeting_attendees table
    sql = f'''CREATE TABLE IF NOT EXISTS recurring_meeting_attendees(
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        recurring_meeting_id INTEGER
    )
    '''
    cursor.execute(sql)

    # Create recurring_meeting_roles table
    sql = f'''CREATE TABLE IF NOT EXISTS recurring_meeting_roles(
        id INTEGER PRIMARY KEY,
        role TEXT,
        recurring_meeting_id INTEGER
    )
    '''
    cursor.execute(sql)
    
    # Create notes table
    sql = f'''CREATE TABLE IF NOT EXISTS notes(
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        note TEXT,
        note_id INTEGER,
        subject TEXT DEFAULT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    '''
    cursor.execute(sql)

    cursor.close()
    connection.close()

def seed_tables(location = DB_DIR):
    """Seed all tables with the necessary default data"""
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    # Insert a default timer if it does not yet exist
    sql = f'''SELECT * FROM timer WHERE id = 1'''
    result = cursor.execute(sql)
    result = result.fetchone()
    
    if result == None:
        sql = f'''INSERT INTO "timer"(active) VALUES (0)'''
        result = cursor.execute(sql)
        connection.commit()
    
    # Update the first timer if it already exists
    sql = f'''UPDATE timer SET active = 0 WHERE id = 1'''
    result = cursor.execute(sql)
    connection.commit()

    # Insert weekdays
    sql = f'''SELECT weekday FROM weekday'''
    result = cursor.execute(sql)
    result = result.fetchall()
    
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    if len(result) == 0:
        for weekday in weekdays:
            sql = f'''INSERT INTO "weekday"(weekday) VALUES ("{weekday}")'''
            result = cursor.execute(sql)
            connection.commit()
    
    cursor.close()
    connection.close()

def sanitize_string(string):
    """Sanitize a string to prevent SQL injection"""
    if(type(string) == str):
        string = string.replace('"', '""').replace("'", "''")
    return string

# --- Discord Logic ---
def check_if_discord_user_exists(discord_user, location=DB_DIR, table_name="employee_users"):
    """Check if a discord user exists in the DB"""
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    # Get or create the user
    sql = f'''SELECT id, discord_user FROM {table_name} WHERE discord_user = "{discord_user}"'''
    result = cursor.execute(sql)
    result = result.fetchone()

    cursor.close()
    connection.close()
    return result is not None

def insert_discord_user(discord_user, name, nickname, location=DB_DIR, table_name="employee_users"):
    """Insert an employee's discord user"""
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    # Insert the user if it does not exist
    if not check_if_discord_user_exists(discord_user, location):
        sql = f'''INSERT INTO {table_name}(name, nickname, discord_user) VALUES ("{name}", "{nickname}", "{discord_user}")'''
        result = cursor.execute(sql)
        connection.commit()
        result = cursor.lastrowid
    else:
        result = None

    cursor.close()
    connection.close()
    return result

def register_discord_user(discord_user, name, nickname, birthday=None, location=DB_DIR, table_name="employee_users"):
    """Insert an employee's discord user or update his/her birthday into the DB"""

    create_table_if_not_exists(location, table_name)
    user_exists = check_if_discord_user_exists(discord_user, location, table_name)

    if user_exists == False:
        # Insert if the user doesn't exist
        insert_discord_user(discord_user, name, nickname, location, table_name)
        return "insert"
    else:
        if birthday is not None:
            # Update if the user exists
            update_user_birthday(discord_user, birthday, location, table_name)
            return "update"
        else:
            return "exists"

def just_get_user_by_discord_id(discord_id, location=DB_DIR, table_name="employee_users"):
    """Get the DB id of a discord user"""

    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT id FROM {table_name} WHERE discord_user = "{discord_id}"'''
    result = cursor.execute(sql)
    try:
        result = result.fetchone()[0]
    except:
        result = None

    cursor.close()
    connection.close()
    return result

def get_or_createuser_by_discord_id(author_dict, location=DB_DIR, table_name="employee_users"):
    """Get the DB id of a discord user"""

    author_id = author_dict["author_id"]
    author_name = author_dict["author_name"]
    author_nickname = author_dict["author_nickname"]

    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT id FROM {table_name} WHERE discord_user = "{author_id}"'''
    result = cursor.execute(sql)

    try:
        result = result.fetchone()[0]
    except:
        sql = f'''INSERT INTO {table_name}(name, nickname, discord_user) VALUES ("{author_name}", "{author_nickname}", "{author_id}")'''
        cursor.execute(sql)
        connection.commit()
        result = cursor.lastrowid        

    cursor.close()
    connection.close()
    return result

def get_user_by_id(user_id, location=DB_DIR, table_name="employee_users"):
    """
    Get the info of a user by id

    Returns: [name, nickname, discord_user, birthday]
    """
    
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT name, nickname, discord_user, birthday FROM {table_name} WHERE id = {user_id}'''
    result = cursor.execute(sql)
    result = result.fetchone()

    cursor.close()
    connection.close()
    return result


# Birthdays
def get_user_birthday(discord_user, location=DB_DIR, table_name="employee_users"):
    """Get the birthday of a discord user"""
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT birthday FROM {table_name} WHERE discord_user = "{discord_user}"'''
    result = cursor.execute(sql)

    try:
        result = result.fetchone()[0]
        cursor.close()
        connection.close()
        return result
    except:
        cursor.close()
        connection.close()
        return None

def get_today_birthdays(location=DB_DIR, table_name="employee_users"):
    """Get the birthday of a discord user"""
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    # Get all users whose birthday day and month matches
    current_date = datetime.now().strftime('%d/%m/%Y')
    if "/" not in current_date:
        current_date = f"{current_date}".replace("-", "/").split("/")
        current_date = f"{current_date[0]}/{current_date[1]}/"
    else:
        current_date = f"{current_date}".split("/")
        current_date = f"{current_date[0]}/{current_date[1]}/"

    sql = f'''SELECT name, nickname FROM {table_name} WHERE birthday LIKE "{current_date}%"'''
    result = cursor.execute(sql)
    result = result.fetchall()

    cursor.close()
    connection.close()
    return result

def get_all_user_birthdays(location=DB_DIR, table_name="employee_users"):
    """Get all the birthdays of the users"""
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT name, nickname, birthday FROM {table_name} ORDER BY birthday'''
    result = cursor.execute(sql)
    result = result.fetchall()
    
    cursor.close()
    connection.close()
    return result

def update_user_birthday(discord_user, birthday, location=DB_DIR, table_name="employee_users"):
    """Update an employee's trello user"""
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''UPDATE {table_name} 
        SET birthday = "{birthday}"
        WHERE discord_user = "{discord_user}"
    '''
    cursor.execute(sql)

    connection.commit()
    cursor.close()
    connection.close()

def get_users_by_birthday(location=DB_DIR, table_name="employee_users"):
    """Get the discord id of a discord user by birthday"""
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    # Get the current date in Arizona timezone
    current_date = datetime.now(pytz.timezone('US/Arizona')).strftime('%d/%m/%Y')

    if "/" not in current_date:
        current_date = f"{current_date}".replace("-", "/").split("/")
        current_date = f"{current_date[0]}/{current_date[1]}/"
    else:
        current_date = f"{current_date}".split("/")
        current_date = f"{current_date[0]}/{current_date[1]}/"

    # Get all users whose birthday day and month matches
    sql = f'''SELECT discord_user FROM {table_name} WHERE birthday LIKE "{current_date}%"'''
    result = cursor.execute(sql)
    result = result.fetchall()
    return result

def register_birthday(discord_user, name, nickname, birthday, location=DB_DIR, table_name="employee_users"):
    """Insert or update an employee's discord and birthday into the DB"""

    create_table_if_not_exists(location, table_name)
    user_exists = check_if_discord_user_exists(discord_user, location, table_name)

    if user_exists == False:
        # Insert if the user doesn't exist
        insert_discord_user(discord_user, name, nickname, birthday, location, table_name)
        return "insert"
    else:
        # Update if the user exists
        update_user_birthday(discord_user, birthday, location, table_name)
        return "update"


# Playlists
def save_playlist(playlist_name, playlist_songs, location=DB_DIR, table_name="playlist"):
    """Save a playlist to the DB"""

    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    # Check if the playlist already exists
    sql = f'''SELECT id FROM {table_name} WHERE name = "{playlist_name}"'''
    result = cursor.execute(sql)
    result = result.fetchone()

    if result == None:
        # Insert if the playlist doesn't exist
        sql = f'''INSERT INTO {table_name}(name) VALUES ("{playlist_name}")'''
        cursor.execute(sql)
        connection.commit()
        result = cursor.lastrowid
    else:
        # Update if the playlist exists
        sql = f'''UPDATE {table_name} 
            SET name = "{playlist_name}"
            WHERE id = {result[0]}
        '''
        cursor.execute(sql)
        connection.commit()
        result = result[0]

    # Clear the playlist songs
    sql = f'''DELETE FROM playlist_song WHERE playlist_id = {result}'''
    cursor.execute(sql)
    connection.commit()

    # Save the new playlist songs
    for song in playlist_songs:
        song = f"{song}"
        song = sanitize_string(song)
        
        sql = f'''INSERT INTO playlist_song(playlist_id, song_name) VALUES ({result}, "{song}")'''
        cursor.execute(sql)
        connection.commit()
    
    cursor.close()
    connection.close()
    return result

def get_playlist_songs(playlist_name, location=DB_DIR, table_name="playlist_song"):
    """Get the songs of a playlist"""
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    try:
        # Get the playlist id of the given playlist name
        sql = f'''SELECT id FROM playlist WHERE name = "{playlist_name}"'''
        result = cursor.execute(sql)
        result = result.fetchone()[0]
    except:
        return None

    try:
        sql = f'''SELECT song_name FROM {table_name} WHERE playlist_id = {result}'''
        result = cursor.execute(sql)
        result = result.fetchall()
    except:
        return []

    cursor.close()
    connection.close()
    return result

def get_all_playlists(location=DB_DIR, table_name="playlist"):
    """Get all the playlists"""
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT name FROM {table_name} ORDER BY id DESC'''
    result = cursor.execute(sql)
    result = result.fetchall()

    cursor.close()
    connection.close()
    return result

def delete_playlist(playlist_name, location=DB_DIR, table_name="playlist"):
    """Delete a playlist"""

    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    try:
        sql = f'''SELECT id FROM {table_name} WHERE name = "{playlist_name}"'''
        result = cursor.execute(sql)
        playlist_id = result.fetchone()[0]
    except:
        return None

    sql = f'''DELETE FROM {table_name} WHERE id = "{playlist_id}"'''
    cursor.execute(sql)
    connection.commit()

    sql = f'''DELETE FROM playlist_song WHERE playlist_id = {playlist_id}'''
    cursor.execute(sql)
    connection.commit()

    cursor.close()
    connection.close()

    return True


# Timer
def toggle_timer(location=DB_DIR, table_name="timer"):
    """Activate the timer"""
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT active FROM {table_name} WHERE id = 1'''
    result = cursor.execute(sql)
    status = result.fetchone()[0]

    if status == 0:
        sql = f'''UPDATE {table_name} SET active = 1'''
        cursor.execute(sql)
    elif status == 1:
        sql = f'''UPDATE {table_name} SET active = 0'''
        cursor.execute(sql)

    connection.commit()
    
    cursor.close()
    connection.close()

def get_timer_status(location=DB_DIR, table_name="timer"):
    """Get the timer status"""
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT active FROM {table_name}'''
    result = cursor.execute(sql)

    result = result.fetchone()[0]
    
    cursor.close()
    connection.close()
    return result


# Notes
def save_note(author_id, author_name, author_nickname, subject, note, location=DB_DIR, table_name="notes"):
    """Save a note"""

    author_dict = {
        "author_id": author_id,
        "author_name": author_name,
        "author_nickname": author_nickname
    }

    note = sanitize_string(note)
    subject = sanitize_string(subject)

    # Get the author's id
    user_id = get_or_createuser_by_discord_id(author_dict, location)

    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    # Get the note with the biggest note_id for the author
    sql = f'''SELECT note_id FROM {table_name} WHERE user_id = {user_id} ORDER BY note_id DESC LIMIT 1'''
    result = cursor.execute(sql)
    result = result.fetchone()

    if result is None:
        note_id = 1
    else:
        note_id = result[0] + 1

    sql = f'''INSERT INTO {table_name}(note, user_id, note_id, subject) VALUES ("{note}", {user_id}, {note_id}, "{subject}")'''
    cursor.execute(sql)
    connection.commit()
    
    cursor.close()
    connection.close()

def get_user_notes(user_id, location=DB_DIR, table_name="notes"):
    """Get all notes"""
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT note, subject, created_at FROM {table_name} WHERE user_id = {user_id} ORDER BY note_id ASC'''
    result = cursor.execute(sql)
    result = result.fetchall()

    cursor.close()
    connection.close()
    return result

def get_notes_by_subject(subject, location=DB_DIR, table_name="notes"):
    """Get all notes by subject"""
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT note, created_at FROM {table_name} WHERE subject="{subject}" ORDER BY id ASC'''
    result = cursor.execute(sql)
    result = result.fetchall()

    cursor.close()
    connection.close()
    return result

def delete_note_by_id(note_id, author_id, location=DB_DIR, table_name="notes"):
    """Delete a note by id"""
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT id FROM employee_users WHERE discord_user = {author_id}'''
    result = cursor.execute(sql)

    try:
        user_id = result.fetchone()[0]
    except TypeError:
        return "inexistent_user"

    sql = f'''SELECT id FROM {table_name} WHERE note_id = {note_id} AND user_id = {user_id}'''
    result = cursor.execute(sql)

    try:
        id = result.fetchone()[0]
    except TypeError:
        return "inexistent_note"

    sql = f'''DELETE FROM {table_name} WHERE id = {id}'''
    cursor.execute(sql)
    connection.commit()

    sql = f'''SELECT id, note_id FROM {table_name} WHERE note_id > {note_id} AND user_id = {user_id} ORDER BY note_id ASC'''
    result = cursor.execute(sql)
    result = result.fetchall()

    for note in result:
        id = note[0]
        new_index = note[1] - 1
        sql = f'''UPDATE {table_name} SET note_id = {new_index} WHERE id = {id}'''
        cursor.execute(sql)
        connection.commit()

    cursor.close()
    connection.close()

def delete_all_user_notes(author_id, location=DB_DIR, table_name="notes"):
    """Delete every note of a user"""
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT id FROM employee_users WHERE discord_user = {author_id}'''
    result = cursor.execute(sql)
    user_id = result.fetchone()[0]

    sql = f'''DELETE FROM {table_name} WHERE user_id = {user_id}'''
    cursor.execute(sql)
    connection.commit()

    cursor.close()
    connection.close()


# Reminders
def save_reminder(author_dict, reminder_time, reminder_topic, location=DB_DIR, table_name="reminder"):
    """Save a reminder"""
    
    # Get the author's id
    user_id = get_or_createuser_by_discord_id(author_dict, location)

    # Sanitize the reminder topic
    reminder_topic = sanitize_string(reminder_topic)

    # Now add the number of minutes to the current time
    reminder_time = datetime.now(pytz.timezone('US/Arizona')) + timedelta(minutes=int(reminder_time))

    # Convert the time to strings (date and time)
    reminder_date = reminder_time.strftime("%Y-%m-%d")
    reminder_time = reminder_time.strftime("%H:%M")

    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''INSERT INTO {table_name}(reminder, user_id, time, date) VALUES ("{reminder_topic}", {user_id}, "{reminder_time}", "{reminder_date}")'''
    cursor.execute(sql)
    connection.commit()
    
    cursor.close()
    connection.close()

def get_user_reminders(user_id, location=DB_DIR, table_name="reminder"):
    """Get all reminders"""
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT reminder, time FROM {table_name} WHERE user_id = {user_id} ORDER BY id ASC'''
    result = cursor.execute(sql)
    result = result.fetchall()

    cursor.close()
    connection.close()
    return result

def get_all_current_reminders(location=DB_DIR, table_name="reminder"):
    """
    Get all reminders
    
    Returns: [id, reminder, time, user_id]
    """
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    # Get the current time
    current_time = datetime.now(pytz.timezone('US/Arizona')).strftime("%H:%M")

    sql = f'''SELECT id, reminder, time, user_id FROM {table_name} WHERE time = "{current_time}" ORDER BY id ASC'''
    result = cursor.execute(sql)
    result = result.fetchall()

    cursor.close()
    connection.close()
    return result

def delete_reminder_by_id(reminder_id, location=DB_DIR, table_name="reminder"):
    """Delete a reminder by id"""

    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''DELETE FROM {table_name} WHERE id = {reminder_id}'''
    cursor.execute(sql)
    connection.commit()

    cursor.close()
    connection.close()

def delete_reminders_before_today(location=DB_DIR, table_name="reminder"):
    """Delete all reminders from the last day"""

    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    # Get the current date
    current_date = datetime.now(pytz.timezone('US/Arizona')).strftime("%Y-%m-%d")

    sql = f'''SELECT id, reminder FROM {table_name} WHERE date < "{current_date}" ORDER BY id ASC'''
    result = cursor.execute(sql)
    reminders = result.fetchall()
    
    sql = f'''DELETE FROM {table_name} WHERE date < "{current_date}"'''
    cursor.execute(sql)
    connection.commit()

    cursor.close()
    connection.close()
    
    reminders_string = ""
    for i, reminder in enumerate(reminders):
        reminders_string += f"{i+1}. {reminder[1]}\n"

    return reminders_string


# Meetings
def save_meeting(meeting_date, meeting_time, meeting_name, attendees, roles, location=DB_DIR, table_name="meeting"):
    """Save the meeting"""

    # Sanitize the meeting name
    meeting_name = sanitize_string(meeting_name)

    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''INSERT INTO {table_name}(date, time, meeting_name) VALUES ("{meeting_date}", "{meeting_time}", "{meeting_name}")'''
    cursor.execute(sql)
    connection.commit()
    
    meeting_id = cursor.lastrowid
    for attendee in attendees:
        sql = f'''INSERT INTO meeting_attendees(meeting_id, user_id) VALUES ({meeting_id}, {attendee})'''
        cursor.execute(sql)
        connection.commit()
    
    for role in roles:
        sql = f'''INSERT INTO meeting_roles(meeting_id, role) VALUES ({meeting_id}, "{role}")'''
        cursor.execute(sql)
        connection.commit()

    cursor.close()
    connection.close()

def get_user_meetings(discord_user_id, location=DB_DIR, table_name="meeting"):
    """Get the meetings"""

    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    # Gotta make a left join to get the user's name
    sql =   f'''SELECT date, time, meeting_name, meeting.id FROM {table_name}
                LEFT JOIN meeting_attendees ON meeting.id = meeting_attendees.meeting_id
                LEFT JOIN employee_users ON employee_users.id = meeting_attendees.user_id
                WHERE employee_users.discord_user = "{discord_user_id}"
            '''
    meetings = cursor.execute(sql)
    meetings = meetings.fetchall()

    meetings_list = []
    for meeting in meetings:
        sql = f'''
        SELECT employee_users.discord_user FROM meeting_attendees
        LEFT JOIN employee_users ON employee_users.id = meeting_attendees.user_id
        WHERE meeting_attendees.meeting_id = {meeting[3]}
        '''
        users = cursor.execute(sql)
        users = users.fetchall()

        meetings_dict = {
            "date": meeting[0],
            "time": meeting[1],
            "meeting_name": meeting[2],
            "users": users
        }
        meetings_list.append(meetings_dict)
            
    cursor.close()
    connection.close()
    return meetings_list

def get_day_meetings(meeting_date, location=DB_DIR, table_name="meeting"):
    """Get the meeting"""
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT date, time FROM {table_name} WHERE date = "{meeting_date}"'''
    result = cursor.execute(sql)

    result = result.fetchall()
    cursor.close()
    connection.close()
    return result

def get_all_current_meetings(location=DB_DIR, table_name="meeting"):
    """
    Get all meetings
    
    Returns: [id, date, time]
    """

    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    # Get the current time
    current_time = datetime.now(pytz.timezone('US/Arizona')).strftime("%H:%M")
    current_date = datetime.now(pytz.timezone('US/Arizona')).strftime("%d/%m/%Y")

    sql = f'''SELECT id, meeting_name, date, time FROM {table_name} WHERE time = "{current_time}" and date = "{current_date}" ORDER BY id ASC'''
    result = cursor.execute(sql)
    result = result.fetchall()

    cursor.close()
    connection.close()
    return result

def get_meeting_attendees(meeting_id, location=DB_DIR, table_name="meeting_attendees"):
    """
    Get the meeting attendees
    
    Returns: [discord_user]
    """
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT user_id FROM {table_name} WHERE meeting_id = {meeting_id}'''
    result = cursor.execute(sql)
    result = result.fetchall()

    attendees = []
    for attendee in result:
        sql = f'''SELECT discord_user FROM employee_users WHERE id = {attendee[0]}'''
        result = cursor.execute(sql)
        result = result.fetchone()
        attendees.append(result[0])

    cursor.close()
    connection.close()
    return attendees

def get_meeting_roles(meeting_id, location=DB_DIR, table_name="meeting_roles"):
    """
    Get the meeting roles
    
    Returns: [role]
    """
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT role FROM {table_name} WHERE meeting_id = {meeting_id}'''
    result = cursor.execute(sql)
    result = result.fetchall()

    roles = []
    for role_result in result:
        roles.append(role_result[0])

    cursor.close()
    connection.close()
    return roles

def delete_meeting_by_id(meeting_id, location=DB_DIR, table_name="meeting"):
    """Delete a meeting as well as all of its attendees and roles"""
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''DELETE FROM {table_name} WHERE id = "{meeting_id}"'''
    cursor.execute(sql)
    connection.commit()

    # Delete the meeting attendees
    sql = f'''DELETE FROM meeting_attendees WHERE meeting_id = "{meeting_id}"'''
    cursor.execute(sql)
    connection.commit()

    # Delete the meeting roles
    sql = f'''DELETE FROM meeting_roles WHERE meeting_id = "{meeting_id}"'''
    cursor.execute(sql)
    connection.commit()
    
    cursor.close()
    connection.close()

def delete_meetings_before_today(location=DB_DIR, table_name="meeting"):
    """Delete all meetings before today"""
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    # Get the current date
    current_date = datetime.now(pytz.timezone('US/Arizona')).strftime("%d/%m/%Y")

    sql = f'''SELECT id, meeting_name FROM {table_name} WHERE date < "{current_date}"'''
    result = cursor.execute(sql)
    result = result.fetchall()

    deleted_meetings_string = ''
    for i, meeting in enumerate(result):
        delete_meeting_by_id(meeting[0], location)
        deleted_meetings_string += f"{i+1}. {meeting[1]}\n"

    cursor.close()
    connection.close()

    return deleted_meetings_string

def delete_all_meetings(location=DB_DIR, table_name="meeting"):
    """Delete all meetings as well as all of the attendees and roles"""
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT id, meeting_name FROM {table_name}'''
    result = cursor.execute(sql)
    result = result.fetchall()

    deleted_meetings_string = ''
    for i, meeting in enumerate(result):
        delete_meeting_by_id(meeting[0], location)
        deleted_meetings_string += f"{i+1}. {meeting[1]}\n"

    # Delete any leftover meeting attendees
    sql = f'''DELETE FROM meeting_attendees'''
    cursor.execute(sql)
    connection.commit()

    # Delete any leftover meeting roles
    sql = f'''DELETE FROM meeting_roles'''
    cursor.execute(sql)
    connection.commit()
    
    cursor.close()
    connection.close()

    return deleted_meetings_string

# Recurring meetings
def save_recurring_meeting(meeting_days, meeting_time, meeting_name, attendees, roles, location=DB_DIR, table_name="recurring_meeting"):
    """Save a recurring meeting"""

    # Sanitize the meeting name
    meeting_name = sanitize_string(meeting_name)

    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    # Get the weekdays ids
    weekdays = []
    for day in meeting_days:
        sql = f'''SELECT id FROM weekday WHERE weekday = "{day}"'''
        result = cursor.execute(sql)
        result = result.fetchone()
        weekdays.append(result[0])
    
    # Save the recurring meeting
    for weekday_id in weekdays:
        sql = f'''INSERT INTO {table_name}(meeting_name, weekday_id, time) VALUES ("{meeting_name}", {weekday_id}, "{meeting_time}")'''
        cursor.execute(sql)
        connection.commit()

        # Get the recurring meeting id
        meeting_id = cursor.lastrowid

        # Save the meeting attendees
        for attendee in attendees:
            sql = f'''INSERT INTO recurring_meeting_attendees(recurring_meeting_id, user_id) VALUES ({meeting_id}, {attendee})'''
            cursor.execute(sql)
            connection.commit()

        for role in roles:
            sql = f'''INSERT INTO recurring_meeting_roles(recurring_meeting_id, role) VALUES ({meeting_id}, "{role}")'''
            cursor.execute(sql)
            connection.commit()
    
    cursor.close()
    connection.close()

def get_current_recurring_meetings(location=DB_DIR, table_name="recurring_meeting"):
    """
    Get all current recurring meetings
    
    Returns: [id, meeting_name, time]
    """

    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    # Get the current time
    current_time = datetime.now(pytz.timezone('US/Arizona')).strftime("%H:%M")
    current_day = datetime.now(pytz.timezone('US/Arizona')).strftime("%A")

    sql = f'''
    SELECT recurring_meeting.id, meeting_name, time FROM {table_name}
    LEFT JOIN weekday ON weekday.id = recurring_meeting.weekday_id
    WHERE recurring_meeting.time = "{current_time}" and weekday.weekday = "{current_day}" 
    ORDER BY recurring_meeting.id ASC
    '''
    result = cursor.execute(sql)
    result = result.fetchall()

    cursor.close()
    connection.close()
    return result

def get_recurring_meeting_attendees(meeting_id, location=DB_DIR, table_name="recurring_meeting_attendees"):
    """
    Get the meeting attendees
    
    Returns: [discord_user]
    """

    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT user_id FROM {table_name} WHERE recurring_meeting_id = {meeting_id}'''
    result = cursor.execute(sql)
    result = result.fetchall()

    attendees = []
    for attendee in result:
        sql = f'''SELECT discord_user FROM employee_users WHERE id = {attendee[0]}'''
        result = cursor.execute(sql)
        result = result.fetchone()
        attendees.append(result[0])

    cursor.close()
    connection.close()
    return attendees

def get_recurring_meeting_roles(meeting_id, location=DB_DIR, table_name="recurring_meeting_roles"):
    """
    Get the meeting roles
    
    Returns: [role]
    """

    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT role FROM {table_name} WHERE recurring_meeting_id = {meeting_id}'''
    result = cursor.execute(sql)
    result = result.fetchall()

    roles = []
    for role_result in result:
        roles.append(role_result[0])

    cursor.close()
    connection.close()
    return roles

def get_all_recurring_meetings(location=DB_DIR, table_name="recurring_meeting"):
    """
    Get all recurring meetings
    
    Returns: [id, meeting_name, time]
    """

    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT id, weekday_id, meeting_name, time FROM {table_name} ORDER BY weekday_id ASC'''
    result = cursor.execute(sql)
    recurring_meetings = result.fetchall()

    meetings = []
    for recurring_meeting in recurring_meetings:
        sql = f'''SELECT weekday FROM weekday WHERE id = {recurring_meeting[1]}'''
        weekday = cursor.execute(sql)
        weekday = weekday.fetchone()[0]

        sql = f'''SELECT user_id FROM recurring_meeting_attendees WHERE recurring_meeting_id = {recurring_meeting[0]}'''
        users = cursor.execute(sql)
        users = users.fetchall()

        meeting_users = []
        for user in users:
            sql = f'''SELECT discord_user FROM employee_users WHERE id = {user[0]}'''
            result = cursor.execute(sql)
            result = result.fetchone()[0]
            meeting_users.append(result)

        sql = f'''SELECT role FROM recurring_meeting_roles WHERE recurring_meeting_id = {recurring_meeting[0]}'''
        roles = cursor.execute(sql)
        roles = roles.fetchall()

        meeting_roles = []
        for role in roles:
            meeting_roles.append(role[0])
        
        meeting = {
            'id': recurring_meeting[0],
            'weekday': weekday,
            'meeting_name': recurring_meeting[2],
            'time': recurring_meeting[3],
            'users': meeting_users,
            'roles': meeting_roles
        }
        meetings.append(meeting)

    cursor.close()
    connection.close()
    return meetings

def delete_recurring_meeting_by_id(meeting_id, location=DB_DIR, table_name="recurring_meeting"):
    """Delete a recurring meeting"""

    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    # Delete the recurring meeting
    sql = f'''DELETE FROM {table_name} WHERE id = {meeting_id}'''
    cursor.execute(sql)
    connection.commit()

    # Delete the recurring meeting attendees
    sql = f'''DELETE FROM recurring_meeting_attendees WHERE recurring_meeting_id = {meeting_id}'''
    cursor.execute(sql)
    connection.commit()

    # Delete the recurring meeting roles
    sql = f'''DELETE FROM recurring_meeting_roles WHERE recurring_meeting_id = {meeting_id}'''
    cursor.execute(sql)
    connection.commit()
    
    cursor.close()
    connection.close()

def delete_recurring_meetings(location=DB_DIR, table_name="recurring_meeting"):
    """Delete all recurring meetings as well as all of its attendees and roles"""

    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT meeting_name FROM {table_name}'''
    result = cursor.execute(sql)
    meeting_names = result.fetchall()

    sql = f'''DELETE FROM {table_name}'''
    cursor.execute(sql)
    connection.commit()

    sql = f'''DELETE FROM recurring_meeting_attendees'''
    cursor.execute(sql)
    connection.commit()

    sql = f'''DELETE FROM recurring_meeting_roles'''
    cursor.execute(sql)
    connection.commit()
    
    cursor.close()
    connection.close()

    return meeting_names

# Check meetings and reminders
def check_events(location=DB_DIR):
    """Check for any meetings or reminders that need to be sent in the current minute"""

    # Get all reminders that need to be sent
    reminders = get_all_current_reminders(location)                                         # id, reminder, time, user_id

    # Get all meetings that need to be sent
    meetings = get_all_current_meetings(location)                                           # id, date, time

    # Get all recurring meetings that need to be sent
    recurring_meetings = get_current_recurring_meetings(location)                           # id, meeting_name, time

    # Construct a list of all the events that need to be sent
    events = []

    for reminder in reminders:
        user_id = get_user_by_id(reminder[3], location)     # name, nickname, discord_user, birthday
        events.append({
            'event_type': 'reminder',
            'event': reminder,              # id, reminder, time, user_id
            'user_id': user_id[2]
        })
    
    for meeting in meetings:
        discord_users = get_meeting_attendees(meeting[0], location)                         # discord_user
        discord_roles = get_meeting_roles(meeting[0], location)                             # role
        events.append({
            'event_type': 'meeting',
            'event': meeting,               # id, date, time
            'attendees': discord_users,
            'roles': discord_roles
        })

    for recurring_meeting in recurring_meetings:
        discord_users = get_recurring_meeting_attendees(recurring_meeting[0], location)     # discord_user
        discord_roles = get_recurring_meeting_roles(recurring_meeting[0], location)         # role
        events.append({
            'event_type': 'recurring_meeting',
            'event': recurring_meeting,             # id, meeting_name, time
            'attendees': discord_users,
            'roles': discord_roles
        })

    return events



if __name__ == "__main__":
    create_table_if_not_exists()
    seed_tables()