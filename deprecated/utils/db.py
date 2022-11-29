import sqlite3
from pathlib import Path


# If this script is run directly
if __name__ == "__main__":
    DB_DIR = Path(__file__).cwd().parent / 'db/data.db'
else:
    DB_DIR = Path(__file__).resolve().parent / 'db/data.db' 


# --- Trello & Discord Logic ---
def check_if_discord_user_exists(discord_user, location=DB_DIR, table_name = "employee_users"):
    """ Check if a discord user exists in the DB """
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    # Get or create the user
    sql = f'''SELECT id, discord_user FROM {table_name} WHERE discord_user = "{discord_user}"'''
    result = cursor.execute(sql)
    return result.fetchone() is not None


def create_table_if_not_exists(location = DB_DIR, table_name = "employee_users"):
    """ Create a table if it does not already exist """
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''CREATE TABLE IF NOT EXISTS {table_name}(
        id INTEGER PRIMARY KEY,
        discord_user TEXT,
        trello_user TEXT
    )'''
    cursor.execute(sql)

    cursor.close()
    connection.close()


def insert_discord_and_trello_user(discord_user, trello_user, location=DB_DIR, table_name = "employee_users"):
    """ Insert an employee's discord and trello users """
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''INSERT INTO {table_name}(discord_user, trello_user) VALUES ("{discord_user}", "{trello_user}")'''
    cursor.execute(sql)

    connection.commit()
    cursor.close()
    connection.close()


def update_and_trello_user(discord_user, trello_user, location=DB_DIR, table_name = "employee_users"):
    """ Update an employee's trello user """
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''UPDATE {table_name} 
        SET trello_user = "{trello_user}"
        WHERE discord_user = "{discord_user}"
    '''
    cursor.execute(sql)

    connection.commit()
    cursor.close()
    connection.close()
    

def register_discord_and_trello_users(discord_user, trello_user, location=DB_DIR, table_name = "employee_users"):
    """ Insert or update an employee's discord and trello users into the DB """

    create_table_if_not_exists(location, table_name)
    user_exists = check_if_discord_user_exists(discord_user, location, table_name)

    if user_exists == False:
        # Insert if the user doesn't exist
        insert_discord_and_trello_user(discord_user, trello_user, location, table_name)
        return "insert"
    else:
        # Update if the user exists
        update_and_trello_user(discord_user, trello_user, location, table_name)
        return "update"


def get_users_trello_id(discord_user, location=DB_DIR, table_name = "employee_users"):
    """ Get the trello id of a discord user """
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT trello_user FROM {table_name} WHERE discord_user = "{discord_user}"'''
    result = cursor.execute(sql)
    return result.fetchone()[0]


def get_users_discord_id(trello_user, location=DB_DIR, table_name = "employee_users"):
    """ Get the discord id of a discord user """
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT discord_user FROM {table_name} WHERE trello_user = "{trello_user}"'''
    result = cursor.execute(sql)
    return result.fetchone()[0]





# --- Webhook logic ---
def create_wh_table_if_not_exists(location = DB_DIR, table_name = "webhooks"):
    """ Create the table if it does not already exist """
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''CREATE TABLE IF NOT EXISTS {table_name}(
        id INTEGER PRIMARY KEY,
        webhook_id TEXT,
        board_name TEXT,
        board_id TEXT
    )'''
    cursor.execute(sql)

    cursor.close()
    connection.close()

def insert_wh(wh_id, board_name, location = DB_DIR, board_id = "", table_name = "webhooks"):
    """ Insert a webhook id and board name into the DB """

    create_wh_table_if_not_exists(location, table_name)

    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''INSERT INTO {table_name}(webhook_id, board_name, board_id) VALUES ("{wh_id}", "{board_name}", "{board_id}")'''
    cursor.execute(sql)

    inserted_id = cursor.lastrowid

    connection.commit()
    cursor.close()
    connection.close()

    inserted_webhook = get_webhook(inserted_id, location, table_name)
    return inserted_webhook

def get_webhooks(location = DB_DIR, table_name = "webhooks"):
    """ Get all webhooks from the DB """
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT board_name, webhook_id FROM {table_name}'''
    result = cursor.execute(sql)
    return result.fetchall()

def get_webhook(wh_db_id, location = DB_DIR, table_name = "webhooks"):
    """ Get a webhook from the DB """
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''SELECT webhook_id FROM {table_name} WHERE id = "{wh_db_id}"'''

    result = cursor.execute(sql)
    result = result.fetchone()
    return result

def delete_webhook(wh_id, location = DB_DIR, table_name = "webhooks"):
    """ Delete a webhook from the DB """
    connection = sqlite3.connect(location)
    cursor = connection.cursor()

    sql = f'''DELETE FROM {table_name} WHERE webhook_id = "{wh_id}"'''
    cursor.execute(sql)

    connection.commit()
    cursor.close()
    connection.close()



# create_table_if_not_exists()
# create_wh_table_if_not_exists()