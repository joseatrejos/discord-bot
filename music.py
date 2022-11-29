import asyncio, discord, json, os, Paginator, random, re, requests, wavelink
from wavelink.ext import spotify
from utils import db
from posixpath import split
from discord.ext import commands
from dotenv import load_dotenv
from datetime import datetime
from bs4 import BeautifulSoup

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
LAVALINK_PASSWORD = os.getenv('LAVALINK_PASSWORD')


if(os.getenv('DEBUG') == 'False'):
    PATH = 'db/data.db'
    PREFIX = '-'
    TIME_CHECK = 60
else:
    PATH = 'db/data_dev.db'
    PREFIX = '*'
    TIME_CHECK = 10

if(TOKEN == None or LAVALINK_PASSWORD == None):
    print("Invalid .env!")
    exit()



# -- Individual Functions for our bot ---

# Security measures to prevent unwanted people from using the bot
def check_admin_authors(author_id):
    author_id = str(author_id)
    allowed_authors = ["323880953137332234", "344710120074248193", "259793695111512065"]

    # Only the associates may use this command
    if author_id not in allowed_authors:
        return False
    else:
        return True

def get_mention_ids(message):
    """ Get the ids of the mentioned users """

    mention_ids = []
    mentions = message.split('<@')
    for mention in mentions:
        if mention != '' and mention is not None:
            mention_ids.append(mention.split('>')[0])
            
    return mention_ids

async def get_image_url(ctx):
    """ Get the image urls from the discord message and return them as a list """

    image_url = []

    # Get the message's image URL
    if ctx.message.attachments:
        for attachment in ctx.message.attachments:
            image_url.append(attachment.url)
    else:
        image_url = ""
    return image_url

async def send_embed(ctx, title, description, color = 0x00FF00, image = None, url = ""):
    """ Send an embed message to the discord channel """

    embed = discord.Embed(
        title=f'{title}',
        description=f'{description}',
        color=color,
        url=url
    )
    if image:
        embed.set_image(url=f'{image}')
    return await ctx.send(embed=embed)

async def send_queue_embed(ctx, queue, color = 0x0000FF):
    """Send an embed message with every song in the queue"""

    page_count = 1
    embeds = []
    embed_count = 0
    
    title = f'Queue Page {page_count}'
    description = f''
    string_length = len(title)
    total_embed_length = 0
    
    # Iterate through the queue and add the songs in several embeds
    for i in range(len(queue)):
        # TODO: This function could be broken if the song's title is too long (over 4096 characters)      

        # Now add the song information into the currently inserted embed
        description += f'**{i+1}. {queue[i].title}** - {convert_seconds_to_time(queue[i].length)}\n'
        string_length += len(f'**{i+1}. {queue[i].title}** - {convert_seconds_to_time(queue[i].length)}\n') + 2
        total_embed_length = len(description) + len(title) + 2
        
        if(string_length > 800 or i == len(queue) - 1):
            # Insert our template embed into the embeds list and then modify it with the constructed values
            embed = discord.Embed(
                title=title,
                description=f'{description}',
                color=color
            )
            embeds.append(embed)

            title = f'Queue Page {page_count+1}'
            page_count += 1
            embed_count += 1
            string_length = 0
            description = ''

        # As long as there's still another iteration left, check if we'll exceed discord's max length on our next iteration
        if i + 1 < len(queue):
            if (total_embed_length + len(f'**{i+2}. {queue[i+1].title}** - {convert_seconds_to_time(queue[i+1].length)}\n') + 2) > 5700:
                # If we'll exceed discord's max length on our next iteration, break the loop
                break

    # Create a paginator object and send the embeds
    return await Paginator.Simple().start(ctx, pages=embeds)

async def send_past_queue_embed(ctx, queue, color = 0x0000FF):
    """Send an embed message with every song in the queue"""

    page_count = 1
    embeds = []
    embed_count = 0
    
    title = f'Queue Page {page_count}'
    description = f''
    string_length = len(title)
    total_embed_length = 0
    
    counter = 0
    # Iterate through the queue in reverse and add the songs in several embeds
    for i in range( (len(queue) - 1), -1, -1):

        # Now add the song information into the currently inserted embed
        description += f'**{counter+1}.** {queue[i]}\n'
        string_length += len(f'**{counter+1}.** {queue[i]}\n') + 2
        total_embed_length = len(description) + len(title) + 2
        
        if(string_length > 800 or i == 0):
            # Insert our template embed into the embeds list and then modify it with the constructed values
            embed = discord.Embed(
                title=title,
                description=f'{description}',
                color=color
            )
            embeds.append(embed)

            title = f'Queue Page {page_count+1}'
            page_count += 1
            embed_count += 1
            string_length = 0
            description = ''

        # As long as there's still another iteration left, check if we'll exceed discord's max length on our next iteration
        if i - 1 >= 0:
            if total_embed_length + len(f'**{counter+2}.** {queue[i-1]}') > 5700:
                # If we'll exceed discord's max length on our next iteration, construct the last sent embed
                embed = discord.Embed(
                    title=title,
                    description=f'{description}',
                    color=color
                )
                embeds.append(embed)
                title = f'Queue Page {page_count+1}'
                
                # Now delete the rest of the queue elements and break the loop
                while i >= 0:
                    del queue[i]
                    i -= 1
                break
        
        counter += 1
        i -= 1

    # Create a paginator object and send the embeds
    return await Paginator.Simple().start(ctx, pages=embeds)

async def send_note_pagination(ctx, notes, color = 0x0000FF):
    """Send an embed message with every note for the user"""

    page_count = 1
    embeds = []
    embed_count = 0
    
    title = f'{ctx.author.name}\'s Notes\' Page {page_count}'
    description = f''
    string_length = len(title)
    total_embed_length = 0
    
    # Iterate through the notes and add them in several embeds
    for i, note_tuple in enumerate(notes):
        
        note = note_tuple[0]
        created_at = note_tuple[2]

        if note_tuple[1] == "None":
            subject = ""
        else:
            subject = f"__{note_tuple[1]}:__\n"
        
        if string_length + len(note) > 4096:
            max_length = 3850 - string_length
            note = note[0:max_length] + '...**(unfinished)**'

        # Now add the note's information into the currently inserted embed
        description += f'**{i+1}.** {subject}{note}\n**Created at:** *{created_at}*\n\n'
        string_length += len(f'**{i+1}.** {subject}{note}\n**Created at:** *{created_at}*\n\n') + 2
        total_embed_length = len(description) + len(title) + 2
        
        if(string_length > 800 or i == len(notes) - 1):
            # Insert our template embed into the embeds list and then modify it with the constructed values
            embed = discord.Embed(
                title=title,
                description=f'{description}',
                color=color
            )
            embeds.append(embed)

            title = f'Note\'s Page {page_count+1}'
            page_count += 1
            embed_count += 1
            string_length = 0
            description = ''

        # As long as there's still another iteration left, check if we'll exceed discord's max length on our next iteration
        if i + 1 < len(notes):
            if (total_embed_length + len(f'**{i+2}.** {notes[i+1][1]}{notes[i+1][0]}\n**Created at:** *{notes[i+1][2]}*\n\n') + 2) > 5700:
                # If we'll exceed discord's max length on our next iteration, then just send the constructed values and break the loop
                remaining_length = 5700 - total_embed_length
                if (remaining_length > 4096):
                    remaining_length = 3850
                
                if notes[i+1][1] == "None":
                    subject = ""
                else:
                    subject = f"__{note_tuple[1]}:__\n"

                description += f'**{i+2}.** {subject}{notes[i+1][0][0:remaining_length]}...**(unfinished)**\n**Created at:** *{notes[i+1][2]}*\n\n'
                title = f'Note\'s Page {page_count+1}'

                embed = discord.Embed(
                    title=title,
                    description=f'{description}',
                    color=color
                )
                embeds.append(embed)
                break

    # Create a paginator object and send the embeds
    return await Paginator.Simple().start(ctx, pages=embeds)

async def send_subject_pagination(ctx, subject, notes, color = 0x0000FF):
    """Send an embed message with every note in the subject"""
    
    page_count = 1
    embeds = []
    embed_count = 0
    
    title = f'{subject} Notes\' Page {page_count}'
    description = f''
    string_length = len(title)
    total_embed_length = 0
    
    # Iterate through the notes and add them in several embeds
    for i, note_tuple in enumerate(notes):
        
        note = note_tuple[0]
        created_at = note_tuple[1]

        if string_length + len(note) > 4096:
            max_length = 3850 - string_length
            note = note[0:max_length] + '...**(unfinished)**'

        # Now add the note's information into the currently inserted embed
        description += f'**{i+1}.** {note}\n**Created at:** *{created_at}*\n\n'
        string_length += len(f'**{i+1}.** {note}\n**Created at:** *{created_at}*\n\n') + 2
        total_embed_length = len(description) + len(title) + 2
        
        if(string_length > 800 or i == len(notes) - 1):
            # Insert our template embed into the embeds list and then modify it with the constructed values
            embed = discord.Embed(
                title=title,
                description=f'{description}',
                color=color
            )
            embeds.append(embed)

            title = f'{subject} Notes\' Page {page_count+1}'
            page_count += 1
            embed_count += 1
            string_length = 0
            description = ''

        # As long as there's still another iteration left, check if we'll exceed discord's max length on our next iteration
        if i + 1 < len(notes):
            if (total_embed_length + len(f'**{i+2}.** {notes[i+1][0]}\n**Created at:** *{notes[i+1][1]}*\n\n') + 2) > 5700:
                # If we'll exceed discord's max length on our next iteration, then just send the constructed values and break the loop
                remaining_length = 5700 - total_embed_length
                if (remaining_length > 4096):
                    remaining_length = 3850
                    
                description = f'**{i+2}.** {notes[i+1][0][0:remaining_length]}...**(unfinished)\nCreated at:** *{notes[i+1][1]}*\n\n'
                title = f'{subject} Notes\' Page {page_count+1}'

                embed = discord.Embed(
                    title=title,
                    description=f'{description}',
                    color=color
                )
                embeds.append(embed)
                break

    # Create a paginator object and send the embeds
    return await Paginator.Simple().start(ctx, pages=embeds)

async def send_meetings_pagination(ctx, meetings, color = 0x0000FF):
    """Send an embed message with every meeting for the user"""

    page_count = 1
    embeds = []
    embed_count = 0
    
    title = f'Meetings\' Page {page_count}'
    description = f''
    string_length = len(title)
    total_embed_length = 0
    
    # Iterate through the meetings and add them in several embeds
    for i, meeting_dict in enumerate(meetings):
        
        date = meeting_dict['date']
        time = meeting_dict['time']
        meeting_name = meeting_dict['meeting_name']
        users = meeting_dict['users']

        users_string = ""
        for user in users:
            users_string += f'<@{user[0]}> '

        if string_length + len(meeting_name) > 4096:
            max_length = 3850 - string_length
            meeting_name = meeting_name[0:max_length] + '...**(unfinished)**'

        # Now add the meeting information into the currently inserted embed
        description += f'**{i+1}.** __{meeting_name}__\nMeeting will start on _**{date}**_ at _**{time}**_ with {users_string}\n\n'
        string_length += len(f'**{i+1}.** __**{meeting_name}**__\nMeeting will start on _**{date}**_ at _**{time}**_ with {users_string}\n\n') + 2
        total_embed_length = len(description) + len(title) + 2
        
        if(string_length > 800 or i == len(meetings) - 1):
            # Insert our template embed into the embeds list and then modify it with the constructed values
            embed = discord.Embed(
                title=title,
                description=f'{description}',
                color=color
            )
            embeds.append(embed)

            title = f'Meetings\' Page {page_count+1}'
            page_count += 1
            embed_count += 1
            string_length = 0
            description = ''

        # As long as there's still another iteration left, check if we'll exceed discord's max length on our next iteration
        if i + 1 < len(meetings):
            if (total_embed_length + len(f'''**{i+2}.** __**{meetings[i+1]['date']}**__ will start on _**{meetings[i+1]['date']}**_ at _**{meetings[i+1]['time']}**_ with {users_string}\n\n''') + 2) > 5700:
                # If we'll exceed discord's max length on our next iteration, then just send the constructed values and break the loop
                remaining_length = 5500 - total_embed_length
                
                title = f'Meetings\' Page {page_count+1}'
                description = f'''**{i+2}.** __{meetings[i+1]['date'][0:remaining_length]}__...**(unfinished)**\nMeeting will start on _**{meetings[i+1]['date']}**_ at _**{meetings[i+1]['time']}**_ with {users_string}\n\n'''

                embed = discord.Embed(
                    title=title,
                    description=f'{description}',
                    color=color
                )
                embeds.append(embed)
                break

    return await Paginator.Simple().start(ctx, pages=embeds)

async def send_recurring_meetings_pagination(ctx, meetings, color = 0x0000FF):
    """Send an embed message with every meeting for the user"""

    page_count = 1
    embeds = []
    embed_count = 0
    
    title = f'Recurring Meetings\' Page {page_count}'
    description = f''
    string_length = len(title)
    total_embed_length = 0
    
    # Iterate through the meetings and add them in several embeds
    for i, meeting_dict in enumerate(meetings):
        
        date = meeting_dict['weekday']
        time = meeting_dict['time']
        meeting_name = meeting_dict['meeting_name']
        users = meeting_dict['users']

        users_string = ''
        for user in users:
            users_string += f'<@{user}> '

        if string_length + len(meeting_name) > 4096:
            max_length = 3850 - string_length
            meeting_name = meeting_name[0:max_length] + '...**(unfinished)**'

        # Now add the meeting information into the currently inserted embed
        description += f'**{i+1}.** __{meeting_name}__\nMeeting will start on _**{date}**_ at _**{time}**_ with {users_string}\n\n'
        string_length += len(f'**{i+1}.** __**{meeting_name}**__\nMeeting will start on _**{date}**_ at _**{time}**_ with {users_string}\n\n') + 2
        total_embed_length = len(description) + len(title) + 2
        
        if(string_length > 800 or i == len(meetings) - 1):
            # Insert our template embed into the embeds list and then modify it with the constructed values
            embed = discord.Embed(
                title=title,
                description=f'{description}',
                color=color
            )
            embeds.append(embed)

            title = f'Recurring Meetings\' Page {page_count+1}'
            page_count += 1
            embed_count += 1
            string_length = 0
            description = ''

        # As long as there's still another iteration left, check if we'll exceed discord's max length on our next iteration
        if i + 1 < len(meetings):
            if (total_embed_length + len(f'''**{i+2}.** __**{meetings[i+1]['meeting_name']}**__ will start on _**{meetings[i+1]['weekday']}**_ at _**{meetings[i+1]['time']}**_ with {users_string}\n\n''') + 2) > 5700:
                # If we'll exceed discord's max length on our next iteration, then just send the constructed values and break the loop
                remaining_length = 5500 - total_embed_length

                title = f'Recurring Meetings\' Page {page_count+1}'
                description = f''''**{i+2}.** __{meetings[i+1]['meeting_name'][0:remaining_length]}__...**(unfinished)**\nMeeting will start on _**{meetings[i+1]['weekday']}**_ at _**{meetings[i+1]['time']}**_ with {users_string}\n\n'''

                embed = discord.Embed(
                    title=title,
                    description=f'{description}',
                    color=color
                )
                embeds.append(embed)
                break

    return await Paginator.Simple().start(ctx, pages=embeds)

async def send_reminders_pagination(ctx, reminders, color = 0x0000FF):
    """Send an embed message with every meeting for the user"""

    page_count = 1
    embeds = []
    embed_count = 0
    
    title = f'{ctx.author.name}\'s Reminders\' Page {page_count}'
    description = f''
    string_length = len(title)
    total_embed_length = 0
    
    # Iterate through the reminders and add them in several embeds
    for i, reminder_tuple in enumerate(reminders):
        
        reminder = reminder_tuple[0]
        time = reminder_tuple[1]

        if string_length + len(reminder) > 4096:
            max_length = 3850 - string_length
            reminder = reminder[0:max_length] + '...**(unfinished)**'

        # Now add the meeting information into the currently inserted embed
        description += f'**{i+1}.** __{reminder}__ will start at _**{time}**_\n\n'
        string_length += len(f'**{i+1}.** __{reminder}__ will start at _**{time}**_\n\n') + 2
        total_embed_length = len(description) + len(title) + 2
        
        if(string_length > 800 or i == len(reminders) - 1):
            # Insert our template embed into the embeds list and then modify it with the constructed values
            embed = discord.Embed(
                title=title,
                description=f'{description}',
                color=color
            )
            embeds.append(embed)

            title = f'{ctx.author.name}\'s Reminders\' Page {page_count+1}'
            page_count += 1
            embed_count += 1
            string_length = 0
            description = ''

        # As long as there's still another iteration left, check if we'll exceed discord's max length on our next iteration
        if i + 1 < len(reminders):
            if (total_embed_length + len(f'**{i+2}.** __{reminders[i+1][0]}__ will start at _**{reminders[i+1][1]}**_\n\n') + 2) > 5700:
                # If we'll exceed discord's max length on our next iteration, then just send the constructed values and break the loop
                remaining_length = 5700 - total_embed_length
                
                title = f'{ctx.author.name}\'s Reminders\' Page {page_count+1}'
                description = f'**{i+2}.** __{reminders[i+1][0][0:remaining_length]}__...**(unfinished)** will start at _**{reminders[i+1][1]}**_\n\n'

                embed = discord.Embed(
                    title=title,
                    description=f'{description}',
                    color=color
                )
                embeds.append(embed)
                break

    return await Paginator.Simple().start(ctx, pages=embeds)

async def send_lyrics_pagination(ctx, lyrics_dict, color = 0x0000FF):
    """Send an embed message with the lyrics of the song"""

    lyrics = lyrics_dict['lyrics']
    song = lyrics_dict['song']
    artist = lyrics_dict['artist']
    
    page_count = 1
    embeds = []
    embed_count = 0
    
    title = f'Lyrics of {song} by {artist} page {page_count}'
    description = f''
    string_length = len(title)
    total_embed_length = 0
    
    # Separate the lyrics into strophes
    strophes = lyrics.split('\n\n')
    
    for i, strophe in enumerate(strophes):
        
        # Now add the song information into the currently inserted embed
        description += f'{strophe}\n\n'
        string_length += len(f'{strophe}\n\n') + 2
        total_embed_length = len(description) + len(title) + 2
        
        if(string_length > 800 or i == len(strophes) - 1):
            # Insert our template embed into the embeds list and then modify it with the constructed values
            embed = discord.Embed(
                title=title,
                description=f'{description}',
                color=color,
                url=lyrics_dict['url']
            )
            embeds.append(embed)

            title = f'Lyrics of {song} by {artist} page {page_count+1}'
            page_count += 1
            embed_count += 1
            string_length = 0
            description = ''

        # As long as there's still another iteration left, check if we'll exceed discord's max length on our next iteration
        if i + 1 < len(strophes):
            if (total_embed_length + len(strophes[i+1]) > 5950):
                # If we'll exceed discord's max length on our next iteration, then just send the constructed values
                remaining_length = 5950 - total_embed_length
                description = f'{strophes[i+1][0:remaining_length]}...**(unfinished)**\n\n'
                title = f'Lyrics of {song} by {artist} page {page_count+1}'
                
                if(string_length + len(description) > 4050):
                    remaining_length = 4050 - string_length
                    description = f'{strophes[i+1][0:remaining_length]}...**(unfinished)**\n\n'
                
                embed = discord.Embed(
                    title=title,
                    description=f'{description}',
                    color=color,
                    url=lyrics_dict['url']
                )
                embeds.append(embed)
                break

    # Create a paginator object and send the embeds (with 1 minute timeout)
    return await Paginator.Simple(timeout=90).start(ctx, pages=embeds)

async def send_playlist_pagination(ctx, playlist_name, playlist_songs, color = 0x0000FF):
    """Send an embed message with the songs of the playlist"""
    
    page_count = 1
    embeds = []
    embed_count = 0
    
    title = f'{playlist_name}\'s songs page {page_count}'
    description = f''
    string_length = len(title)
    total_embed_length = 0
        
    for i, song in enumerate(playlist_songs):
        
        # Now add the song information into the currently inserted embed
        description += f'**{i+1}**. {song}\n\n'
        string_length += len(f'**{i+1}**. {song}\n\n') + 2
        total_embed_length = len(description) + len(title) + 2
        
        if(string_length > 800 or i == len(playlist_songs) - 1):
            # Insert our template embed into the embeds list and then modify it with the constructed values
            embed = discord.Embed(
                title=title,
                description=f'{description}',
                color=color
            )
            embeds.append(embed)

            title = f'{playlist_name}\'s songs page {page_count+1}'
            page_count += 1
            embed_count += 1
            string_length = 0
            description = ''

        # As long as there's still another iteration left, check if we'll exceed discord's max length on our next iteration
        if i + 1 < len(playlist_songs):
            if (total_embed_length + len(playlist_songs[i+1]) > 5950):
                # If we'll exceed discord's max length on our next iteration, then just send the constructed values
                remaining_length = 5950 - total_embed_length
                description = f'**{i+2}**. {playlist_songs[i+1][0:remaining_length]}...**(unfinished)**\n\n'
                title = f'{playlist_name}\'s songs page {page_count+1}'
                
                if(string_length + len(description) > 4050):
                    remaining_length = 4050 - string_length
                    description = f'**{i+2}**. {playlist_songs[i+1][0:remaining_length]}...**(unfinished)**\n\n'
                
                embed = discord.Embed(
                    title=title,
                    description=f'{description}',
                    color=color
                )
                embeds.append(embed)
                break

    # Create a paginator object and send the embeds (with 1 minute timeout)
    return await Paginator.Simple(timeout=90).start(ctx, pages=embeds)

async def send_playlists_pagination(ctx, playlists, color = 0x0000FF):
    """Send an embed message with every existing playlist"""
    
    page_count = 1
    embeds = []
    embed_count = 0
    
    title = f'Playlists page {page_count}'
    description = f''
    string_length = len(title)
    total_embed_length = 0
        
    for i, playlist_name in enumerate(playlists):
        
        # Now add the song information into the currently inserted embed
        description += f'**{i+1}**. {playlist_name[0]}\n\n'
        string_length += len(f'**{i+1}**. {playlist_name[0]}\n\n') + 2
        total_embed_length = len(description) + len(title) + 2
        
        if(string_length > 800 or i == len(playlists) - 1):
            # Insert our template embed into the embeds list and then modify it with the constructed values
            embed = discord.Embed(
                title=title,
                description=f'{description}',
                color=color
            )
            embeds.append(embed)

            title = f'Playlists page {page_count+1}'
            page_count += 1
            embed_count += 1
            string_length = 0
            description = ''

        # As long as there's still another iteration left, check if we'll exceed discord's max length on our next iteration
        if i + 1 < len(playlists):
            if (total_embed_length + len(playlists[i+1]) > 5950):
                # If we'll exceed discord's max length on our next iteration, then just send the constructed values
                remaining_length = 5950 - total_embed_length
                description = f'**{i+2}**. {playlists[i+1][0][0:remaining_length]}...**(unfinished)**\n\n'
                title = f'Playlists page {page_count+1}'
                
                if(string_length + len(description) > 4050):
                    remaining_length = 4050 - string_length
                    description = f'**{i+2}**. {playlists[i+1][0][0:remaining_length]}...**(unfinished)**\n\n'
                
                embed = discord.Embed(
                    title=title,
                    description=f'{description}',
                    color=color
                )
                embeds.append(embed)
                break

    # Create a paginator object and send the embeds (with 1 minute timeout)
    return await Paginator.Simple(timeout=90).start(ctx, pages=embeds)

async def send_birthday_pagination(ctx, birthday_list):
    """Send an embed message with every birthday in the database"""

    page_count = 1
    embeds = []
    embed_count = 0
    
    title = f'Birthday Page {page_count}'
    description = f''
    string_length = len(title)
    total_embed_length = 0
    
    # Iterate through the list and add the birthdays in several embeds
    for i, user in enumerate(birthday_list):
        # 0 = name, 1 = nickname, 2 = birthday

        # Now construct the embed item with birthday information
        description += f'**{i+1}. {user[1]}**\'s birthday is on __{user[2]}__\n'
        string_length += len(f'**{user[1]}**\'s birthday is on {user[2]}\n')
        total_embed_length = len(description) + len(title)

        if(string_length > 800 or i == len(birthday_list) - 1):
            # Insert our template embed into the embeds list and then modify it with the constructed values
            embed = discord.Embed(
                title=title,
                description=f'{description}',
                color=0x00FF00
            )
            embeds.append(embed)

            title = f'Birthday Page {page_count+1}'
            page_count += 1
            embed_count += 1
            string_length = 0
            description = ''

        # As long as there's still another iteration left, check if we'll exceed discord's max length on our next iteration
        if i + 1 < len(birthday_list):
            if (total_embed_length + len(birthday_list[i+1]) > 5700):
                # If we'll exceed discord's max length on our next iteration, then just send the constructed values
                title = f'Birthday Page {page_count+1}'
                embed = discord.Embed(
                    title=title,
                    description=f'{description}',
                    color=0x00FF00
                )
                embeds.append(embed)
                break

    # Create a paginator object and send the embeds
    return await Paginator.Simple().start(ctx, pages=embeds)

async def send_music_embed(ctx, search, color = 0x00FF00):
    """Send an embed message to the discord channel when a music command is used"""

    embed = discord.Embed(
        title=search.title,
        description=f'Song has been added to the queue in __{ctx.voice_client.channel}__',
        color=color,
        url=search.uri
    )
    embed.set_image(url=search.thumbnail)

    await ctx.send(embed=embed)

async def spotify_embed(ctx, search, color = 0x00FF00):
    """Send an embed message to the discord channel when a music command is used"""

    embed = discord.Embed(
        title=f"Spotify song added to the queue",
        description=f'Song has been added to the queue in __{ctx.voice_client.channel}__',
        color=color,
        url=search
    )

    await ctx.send(embed=embed)

async def check_user_vc(ctx):
    try:
        ctx.author.voice.channel
        return True
        
    except AttributeError:
        await send_embed(ctx, 'You are not connected to a voice channel.', 'Please connect to a voice channel before calling me', 0xFF0000)
        return False

async def check_user_bot_vc(ctx):
    try:
        if ctx.author.voice.channel != ctx.voice_client.channel:
            await send_embed(ctx, 'You are not connected to my voice channel.', 'Please connect to my voice channel before calling me', 0xFF0000)
            return False

        return True

    except AttributeError:
        await send_embed(ctx, 'You are not connected to a voice channel.', 'Please connect to a voice channel before calling me', 0xFF0000)
        return False

async def convert_song_list_to_wavelink_track(song_list):
    """ Convert a list of song urls to a list of wavelink.Track objects """
    track_list = []

    for song in song_list:
        track_list.append(await wavelink.YouTubeTrack.search(query=song, return_first=True))
    return track_list

async def convert_song_list_of_tuples_to_wavelink_tracks(song_list):
    """ Convert a list of song tuples to a list of wavelink.Track objects """
    track_list = []

    for song in song_list:
        track_list.append(await wavelink.YouTubeTrack.search(query=song[0], return_first=True))
    return track_list

async def validate_index(ctx, i):
    """ Validate the index"""
    real_index = ctx.message.content.split(' ')[i]
    if(real_index.isdigit()):
        real_index = int(real_index) - 1
        return real_index
    else:
        return None

async def wait_for_response(bot, ctx, timeout = 60.0):
    """ Get the id of the selected item """
    # Wait for a response from the original author
    response = await bot.wait_for('message', timeout=timeout, check=lambda message: message.author == ctx.author)

    response = response.content.strip()
    return response

def convert_seconds_to_time(seconds):
    """ Convert seconds to time """
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    
    if (len(f'{minutes}') == 1):
        minutes = f'0{minutes}'
    if (len(f'{seconds}') == 1):
        seconds = f'0{seconds}'

    return f'{minutes}:{seconds}'

def validate_time(time):
    """ Validate the time """

    time_regex = '^[0-2][0-9]:[0-6][0-9]$'
    if(re.search(time_regex, time) is None):
        return False

    return True

def format_date(date_received):
    date = date_received.split('/')
    if(len(date[0]) == 1):
        date[0] = f'0{date[0]}'
    if(len(date[1]) == 1):
        date[1] = f'0{date[1]}'
    date = f'{date[0]}/{date[1]}/{date[2]}'
    return date

def format_time(time_received):
    time = time_received.split(':')
    if(len(time[0]) == 1):
        time[0] = f'0{time[0]}'
    if(len(time[1]) == 1):
        time[1] = f'0{time[1]}'
    time = f'{time[0]}:{time[1]}'
    return time

def construct_author_dict(ctx, type="author"):
    """Construct the author dictionary"""
    if(type == "author"):
        author_dict = {
            'author_id': ctx.author.id,
            'author_name': ctx.author.name,
            'author_nickname': ctx.author.nick
        }
        return author_dict
    elif(type == "mention"):
        mention = ctx
        author_dict = {
            'author_id': mention.id,
            'author_name': mention.name,
            'author_nickname': mention.nick
        }
        return author_dict

def manage_reminder(event, url, payload, files, headers):
    """Manage an event for a reminder"""
    payload={
        "content": f"<@{event['user_id']}> you have a reminder",
        
        "embeds": [
            {
                "title": f"Reminder scheduled for {event['event'][2]}",
                "description": f"{event['event'][1]}",
                "color": 0x00FF00
            }
        ]
    }
    requests.request("POST", url, headers=headers, data=json.dumps(payload), files=files)

    # Delete the alert from the DB
    db.delete_reminder_by_id(event['event'][0], PATH)

def manage_meeting(event, url, payload, files, headers):
    """Manage an event for a meeting"""

    users = ""
    iterated_users = []
    iterated_roles = []

    for attendee in event['attendees']:
        if attendee not in iterated_users:
            users += f"<@{attendee}> "
            iterated_users.append(attendee)

    for role in event['roles']:
        if role not in iterated_users:
            users += f"<@{role}> "
            iterated_roles.append(role)

    payload={
        "content": f"{users} you have a meeting",
        
        "embeds": [
            {
                "title": f"Meeting scheduled for {event['event'][2]} at {event['event'][3]}",
                "description": f"{event['event'][1]}",
                "color": 0x00FF00
            }
        ]
    }

    requests.request("POST", url, headers=headers, data=json.dumps(payload), files=files)

    # Delete the alert from the DB
    db.delete_meeting_by_id(event['event'][0], PATH)

def manage_recurring_meeting(event, url, payload, files, headers):
    """Manage an event for a recurring meeting"""

    users = ""
    iterated_users = []
    iterated_roles = []
    current_day = datetime.now().strftime("%A")

    for attendee in event['attendees']:
        if attendee not in iterated_users:
            users += f"<@{attendee}> "
            iterated_users.append(attendee)

    for role in event['roles']:
        if role not in iterated_users:
            users += f"<@{role}> "
            iterated_roles.append(role)

    payload={
        "content": f"{users}you have a meeting",
        
        "embeds": [
            {
                "title": f"Recurring meeting scheduled for *{current_day}s* at *{event['event'][2]}*",
                "description": f"__{event['event'][1]}__",
                "color": 0x00FF00
            }
        ]
    }

    requests.request("POST", url, headers=headers, data=json.dumps(payload), files=files)

    # Delete the alert from the DB during development
    if os.getenv('DEBUG_THREADS') == 'True':
        db.delete_recurring_meeting_by_id(event['event'][0], PATH)

def send_message_to_webhook(webhook_data, content, embed_title, embed_description="", embed_color=0x00FF00):

    payload={
        "content": content,
        
        "embeds": [
            {
                "title": embed_title,
                "description": embed_description,
                "color": embed_color
            }
        ]
    }

    requests.request("POST", webhook_data['url'], headers=webhook_data['headers'], data=json.dumps(payload), files=webhook_data['files'])

async def get_lyrics(song_title, song_artist = None):
    """ Get the lyrics of a song """
    song = song_title.replace(' ', '+')

    # Get a better API call in order to actually find the lyrics of songs
    url = f'https://some-random-api.ml/lyrics?title={song}'
    if(song_artist != None):
        url += f'&author={song_artist}'
    response = requests.get(url)
    response = response.json()
    try:
        lyrics_info = {
            'lyrics': response['lyrics'],
            'song': response['title'],
            'artist': response['author'],
            'url': response['links']['genius']
        }
        return lyrics_info
    except KeyError:
        return None

    # Get the lyrics from the genius API
    url = f'https://api.genius.com/search?q={song_title}'
    genius_token = os.getenv('GENIUS_TOKEN')
    headers = {'Authorization': 'Bearer ' + genius_token}
    response = requests.get(url, headers=headers)
    response = response.json()

    # Get the first song from the search results
    try:
        lyrics_url = response['response']['hits'][0]['result']['url']
        artist = response['response']['hits'][0]['result']['primary_artist']['name']
        song = response['response']['hits'][0]['result']['title']

    except IndexError:
        return None
    
    # Get the lyrics from the song_url
    response = requests.get(lyrics_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    lyrics = soup.find(attrs={"data-lyrics-container": "true"}).get_text(separator="\n")
    lyrics = lyrics.replace('[', '\n**[').replace(']', ']**')

    lyrics_info = {
        'lyrics': lyrics,
        'artist': artist,
        'song': song,
        'url': lyrics_url
    }
    return lyrics_info

async def birthday_check():
    """Check if it's someone's birthday"""

    # Get all the birthdays from the database
    users_birthdays = db.get_users_by_birthday(PATH)

    url = os.getenv('BIRTHDAY_WEBHOOK_URL')
    payload = {}
    files={}
    headers = {"Content-Type": "application/json"}

    if(len(users_birthdays) == 0):
        # Now send discord a webhook to the birthday channel
        payload={
            "content": f"Today is no one's birthday :(",
            
            "embeds": [
                {
                    "title": "No birthdays today",
                    "description": "Maybe tomorrow?",
                    "color": 0xFF0000
                }
            ]
        }
        requests.request("POST", url, headers=headers, data=json.dumps(payload), files=files)
    else:
        content = ""
        for i, user in enumerate(users_birthdays):
            content += f"{i+1}. Happy birthday <@{user[0]}>!\n"

        # Now send discord a webhook to the birthday channel
        payload={
            "content": f"Happy birthday to all of you!",
            "embeds": [
                {
                    "title": "Today is someone's birthday!",
                    "description": content,
                    "color": 0x00FF00,
                    "thumbnail": {
                        "url": "https://hips.hearstapps.com/hmg-prod/images/birthday-cake-with-happy-birthday-banner-royalty-free-image-1656616811.jpg?crop=0.668xw:1.00xh;0.0255xw,0"
                    }
                }
            ]
        }
        requests.request("POST", url, headers=headers, data=json.dumps(payload), files=files)

def validate_weekdays(meeting_days):
    """Validate the weekdays"""

    valid_days = {
        "monday": ["monday","mon", "lunes", "lun"],
        "tuesday": ["tuesday","tue", "martes", "mar"],
        "wednesday": ["wednesday","wed", "miércoles", "miercoles", "mie", "mié"],
        "thursday": ["thursday","thu", "jueves", "jue"],
        "friday": ["friday","fri", "viernes", "vie"],
        "saturday": ["saturday","sat", "sábado", "sabado", "sab"],
        "sunday": ["sunday","sun", "domingo", "dom"]
    }
    iterated_days = []
    correct_days = []

    # Validate the days
    for i, day in enumerate(meeting_days):

        meeting_days[i] = day.strip().lower()

        if meeting_days[i] in valid_days["monday"]:
            if "monday" not in iterated_days:
                iterated_days.append("monday")
                correct_days.append("Monday")
            else:
                return False

        elif meeting_days[i] in valid_days["tuesday"]:
            if "tuesday" not in iterated_days:
                iterated_days.append("tuesday")
                correct_days.append("Tuesday")
            else:
                return False

        elif meeting_days[i] in valid_days["wednesday"]:
            if "wednesday" not in iterated_days:
                iterated_days.append("wednesday")
                correct_days.append("Wednesday")
            else:
                return False

        elif meeting_days[i] in valid_days["thursday"]:
            if "thursday" not in iterated_days:
                iterated_days.append("thursday")
                correct_days.append("Thursday")
            else:
                return False

        elif meeting_days[i] in valid_days["friday"]:
            if "friday" not in iterated_days:
                iterated_days.append("friday")
                correct_days.append("Friday")
            else:
                return False

        elif meeting_days[i] in valid_days["saturday"]:
            if "saturday" not in iterated_days:
                iterated_days.append("saturday")
                correct_days.append("Saturday")
            else:
                return False

        elif meeting_days[i] in valid_days["sunday"]:
            if "sunday" not in iterated_days:
                iterated_days.append("sunday")
                correct_days.append("Sunday")
            else:
                return False

        else:
            return ("invalid_weekday", day)

    return correct_days

# WaveLink Queue class
class CustomPlayer(wavelink.Player):
    def __init__(self):
        super().__init__()
        self.queue = wavelink.Queue()
        self.loop = False
        self.shuffle = False
        self.past_queue = []

    def toggle_loop(self):
        self.loop = not self.loop
        return self.loop

    def get_loop(self):
        return self.loop

    def toggle_shuffle(self):
        self.shuffle = not self.shuffle
        return self.shuffle

    def get_shuffle(self):
        return self.shuffle


# --- Bot Startup and Commands ---
bot = commands.Bot(command_prefix=PREFIX, intents=discord.Intents.all())

# On ready
@bot.event
async def on_ready():
    """ On ready, print the bot's name"""
    print(f'{bot.user.name} has connected to Discord!\n')
    bot.loop.create_task(connect_nodes())

# On resume
@bot.event
async def on_resumed():
    """On resume, prints the bot's name"""
    print(f'{bot.user.name} has reconnected to Discord!\n')

# Helper function to connect to Lavalink server/node
async def connect_nodes():
    await bot.wait_until_ready()
    await wavelink.NodePool.create_node(
        bot=bot,
        host='localhost',
        port=2333,
        password=LAVALINK_PASSWORD,

        spotify_client=spotify.SpotifyClient(
            client_id=os.getenv('SPOTIFY_CLIENT_ID'),
            client_secret=os.getenv('SPOTIFY_CLIENT_SECRET')
        )
    )

# Event that executes once the bot is connected to the Lavalink server
@bot.event
async def on_wavelink_node_ready(node: wavelink.Node):
    print(f'Node {node.identifier} is ready!')

@bot.event
async def on_wavelink_track_end(player: CustomPlayer, track: wavelink.Track, reason):

    # Append the finished track to the past queue TODO: Check the max size
    player.past_queue.append(f"**Title:** __{track}__\n**URL:** {track.uri}\n")

    if player.get_loop():
        await player.play(track)

    elif player.get_shuffle():
        queue_length = len(player.queue) - 1
        song_index = random.randint(0, queue_length)
        await player.play(player.queue[song_index])
        del player.queue[song_index]

    elif not player.queue.is_empty:
        next_track = player.queue.get()
        await player.play(next_track)



# --- Music Commands ---
@bot.command('play', aliases=['p'], help='Play a song')
async def play(ctx):
    """Plays a song from youtube"""

    try:
        search = ctx.message.content.split(' ', 1)[1]
    except IndexError:
        search = ''
    finally:
        if '.com' in search and '&list=' in search:
            await send_embed(ctx, 'Playlist detected', 'Please use the -playlist command to play a playlist', 0xFF0000)
            return

        elif 'spotify.com' in search:
            await send_embed(ctx, 'Spotify link detected', 'Please use the -spotify command to play a Spotify link', 0xFF0000)
            return

        else:

            # Check if the user is in a voice channel before calling the bot
            user_in_vc = await check_user_vc(ctx)
            if not user_in_vc:
                return
            
            if search != '':
                search = await wavelink.YouTubeTrack.search(query=search, return_first=True)

            # Get the bot's voice channel service (unique per server)
            bot_vc = ctx.voice_client


            # Check if there is no song provided to just resume the song (in case that the user is in the same voice channel as our bot)
            if (search is None or search == ''):

                if (bot_vc.is_paused()):
                    await bot_vc.resume()
                    return await send_embed(ctx, 'Resumed song', 'Music playing resumed', 0x00FF00)
                elif (bot_vc is None):
                    return await send_embed(ctx, 'No song provided.', 'Please provide a song to play', 0xFF0000)
                else:
                    try:
                        return await bot_vc.move_to(ctx.author.voice.channel)
                    except:
                        return await send_embed("Unknown error", "An unknown error happened and the system didn't know what to do.", 0xFF0000)


            # If the bot's voice client isn't active, activate it, connect the bot to the author's voice channel and begin playing.
            if not bot_vc:

                custom_player = CustomPlayer()
                bot_vc: CustomPlayer = await ctx.author.voice.channel.connect(cls=custom_player)
                await bot_vc.play(search)

                # Send an embed message to the discord channel
                return await send_music_embed(ctx, search, 0x00FF00)

            else:

                # If the bot is paused, resume the song
                if bot_vc.is_paused():

                    # Resume the song
                    await bot_vc.resume()

                    # Add the song to the queue
                    bot_vc.queue.put(item=search)
                    
                    # Send an embed message to the discord channel
                    return await send_music_embed(ctx, search, 0x0000FF)

                # If the bot is connected to a voice channel, add the song to the queue
                elif hasattr(bot_vc, 'channel'):

                    if(bot_vc.channel is not None):
                        if bot_vc.is_playing():
                            bot_vc.queue.put(item=search)
                            await bot_vc.move_to(ctx.author.voice.channel)
                            return await send_music_embed(ctx, search, 0x0000FF)

                        else:
                            await bot_vc.play(search)
                            await bot_vc.move_to(ctx.author.voice.channel)
                            return await send_music_embed(ctx, search, 0x00FF00)

                    else:
                        await bot_vc.stop()
                        await bot_vc.move_to(ctx.author.voice.channel)
                        await bot_vc.play(search)
                        return await send_music_embed(ctx, search, 0xFFFFFF)

                else:
                    if bot_vc.is_playing():
                        bot_vc.stop()
                        bot_vc.queue.put(item=search)
                        await bot_vc.move_to(ctx.author.voice.channel)
                        await bot_vc.play()
                        return await send_music_embed(ctx, search, 0x00FF00)
                    else:
                        await bot_vc.move_to(ctx.author.voice.channel)
                        await bot_vc.play(search)
                        return await send_music_embed(ctx, search, 0x00FF00)
                

@bot.command('playlist', aliases=['pl'], help='Play all songs in a playlist')
async def play(ctx, *, search: wavelink.YouTubePlaylist):
    """Adds playlist songs to the queue"""

    arguments = ctx.message.content.split(' ', 1)[1]
    if ('.com' in arguments == False) and ('&list=' in arguments == False):
        await send_embed(ctx, 'Playlist not sent', 'Please send a valid playlist to use this command.', 0xFF0000)
        return

    # Get the bot's voice channel service (unique per server)
    bot_vc = ctx.voice_client

    # Check if the user is in a voice channel to return a message saying that he/she must connect before calling the bot
    user_in_vc = await check_user_vc(ctx)
    if not user_in_vc:
        return


    # If the bot's voice client isn't active, activate it, connect the bot to the author's voice channel and begin playing.
    if not bot_vc:

        custom_player = CustomPlayer()
        bot_vc: CustomPlayer = await ctx.author.voice.channel.connect(cls=custom_player)
        
        # Add the song or playlist songs to the queue
        for i, song in enumerate(search.tracks):
            if(i == 0):
                await bot_vc.play(song)
            else:
                bot_vc.queue.put(item=song)


        # Send an embed message to the discord channel
        return await send_music_embed(ctx, search.tracks[0], 0x00FF00)

    else:
        
        for i, song in enumerate(search.tracks):
            bot_vc.queue.put(item=song)

        if bot_vc.is_paused():
            await bot_vc.resume()
        elif not bot_vc.is_playing():
            await bot_vc.play()

        await bot_vc.move_to(ctx.author.voice.channel)

        # Send an embed message to the discord channel
        return await send_music_embed(ctx, search.tracks[0], 0x00FF00)


@bot.command('spotify', aliases=['sp'], help='Play a song from a Spotify link')
async def play(ctx, *, search):
# async def play(ctx, *, search: wavelink.SpotifyTrack):
    """Play a song from a Spotify link"""
    
    if 'spotify.com' not in search:
        await send_embed(ctx, 'Spotify link not sent', 'Please send a valid Spotify link to use this command.', 0xFF0000)
        return

    # Get the bot's voice channel service (unique per server)
    bot_vc = ctx.voice_client

    # Check if the user is in a voice channel to return a message saying that he/she must connect before calling the bot
    user_in_vc = await check_user_vc(ctx)
    if not user_in_vc:
        return


    # If the bot's voice client isn't active, activate it, connect the bot to the author's voice channel and begin playing.
    if not bot_vc:

        custom_player = CustomPlayer()
        bot_vc: CustomPlayer = await ctx.author.voice.channel.connect(cls=custom_player)

        decoded = spotify.decode_url(search)

        if decoded['type'] == decoded['type'].playlist:
            counter = 0
            async for partial in spotify.SpotifyTrack.iterator(query=search):
                if counter == 0:
                    await bot_vc.play(partial)
                    counter += 1
                else:
                    bot_vc.queue.put(item=partial)
                    
        elif decoded['type'] == decoded['type'].track:
            track = await spotify.SpotifyTrack.search(query=search, return_first=True)
            await bot_vc.play(track)
        
        # Send an embed message to the discord channel
        return await spotify_embed(ctx, search, 0x00FF00)

    else:

        decoded = spotify.decode_url(search)
        if decoded['type'] == decoded['type'].playlist:
            counter = 0
            async for partial in spotify.SpotifyTrack.iterator(query=search):
                bot_vc.queue.put(item=partial)
        
        elif decoded['type'] == decoded['type'].track:
            track = await spotify.SpotifyTrack.search(query=search, return_first=True)

        # If the bot is paused, resume the song
        if bot_vc.is_paused():

            # Resume the song
            await bot_vc.resume()

            # Add the song to the queue
            bot_vc.queue.put(item=track)
            
            # Send an embed message to the discord channel
            return await spotify_embed(ctx, search, 0x0000FF)

        # If the bot is connected to a voice channel, add the song to the queue
        elif hasattr(bot_vc, 'channel'):

            if(bot_vc.channel is not None):
                if bot_vc.is_playing():
                    bot_vc.queue.put(item=track)
                    await bot_vc.move_to(ctx.author.voice.channel)
                    return await spotify_embed(ctx, search, 0x0000FF)

                else:
                    await bot_vc.play(track)
                    await bot_vc.move_to(ctx.author.voice.channel)
                    return await spotify_embed(ctx, search, 0x00FF00)

            else:
                await bot_vc.stop()
                await bot_vc.move_to(ctx.author.voice.channel)
                await bot_vc.play(track)
                return await spotify_embed(ctx, search, 0xFFFFFF)

        else:
            if bot_vc.is_playing():
                bot_vc.stop()
                bot_vc.queue.put(item=track)
                await bot_vc.move_to(ctx.author.voice.channel)
                await bot_vc.play()
                return await spotify_embed(ctx, search, 0x00FF00)


@bot.command('stop', help='Stop the music player')
async def stop(ctx):
    """Stops the music player"""

    bot_vc = ctx.voice_client
    if not bot_vc:
        return await send_embed(ctx, 'I am not connected to a voice channel.', 'Please connect to a voice channel before calling me', 0xFF0000)

    await bot_vc.disconnect()
    return await send_embed(ctx, 'Stopped playing music', 'I have disconnected from the voice channel', 0xFFFFFF)


@bot.command('skip', aliases=["next"], help='Skip the current song')
async def skip(ctx):
    """Skips the current song"""
    
    bot_vc = ctx.voice_client

    if bot_vc:
        if not bot_vc.is_playing():
            return await send_embed(ctx, 'Nothing is playing.', 'I can\'t skip songs if nothing is playing.', 0xFF0000)
        
        if bot_vc.queue.is_empty:
            await bot_vc.stop()
            return await send_embed(ctx, 'Skipped song', 'I have skipped the current song', 0x0000FF)

        await bot_vc.seek(bot_vc.track.length * 1000)
        await send_embed(ctx, 'Skipped song', 'I have skipped the current song', 0x0000FF)

        if bot_vc.is_paused():
            return await bot_vc.resume()

    elif(not bot_vc):
        return await send_embed(ctx, 'I\'m not connected to any voice channel.', 'I can\'t skip songs if I\'m not even connected to a channel.', 0xFF0000)


@bot.command('pause', help='Pause the current song')
async def pause(ctx):
    """Pauses the current song"""

    bot_vc = ctx.voice_client
    if bot_vc:
        if bot_vc.is_playing() and not bot_vc.is_paused():
            await bot_vc.pause()
            return await send_embed(ctx, 'Song paused', 'The song has been paused', 0x00FF00)
        else:
            return await send_embed(ctx, 'Nothing is playing.', 'I can\'t pause songs if nothing is playing.', 0xFF0000)

    return await send_embed(ctx, 'I\'m not connected to any voice channel.', 'I can\'t pause songs if I\'m not even connected to a channel.', 0xFF0000)


@bot.command('resume', help='Resume the current song')
async def resume(ctx):
    """Resumes the current song"""

    bot_vc = ctx.voice_client
    if bot_vc:
        if bot_vc.is_paused():
            await bot_vc.resume()
            return await send_embed(ctx, 'Song resumed', 'Music playing has been resumed', 0x00FF00)
        else:
            return await send_embed(ctx, 'Nothing is playing.', 'I can\'t resume playing songs if there\'s nothing in queue.', 0xFF0000)

    return await send_embed(ctx, 'I\'m not connected to any voice channel.', 'I can\'t resume playing songs if I\'m not even connected to a channel.', 0xFF0000)


@bot.command('queue', aliases=['q'], help='Show the current queue')
async def queue(ctx):
    """Shows the current queue"""

    bot_vc = ctx.voice_client
    if bot_vc:
        if bot_vc.queue.is_empty:
            return await send_embed(ctx, 'Nothing in queue.', 'I can\'t show a queue when there\'s nothing in queue.', 0xFF0000)
        else:
            # Send an embed message to the discord channel
            return await send_queue_embed(ctx, bot_vc.queue, 0x0000FF)
    
    return await send_embed(ctx, 'I\'m not connected to any voice channel.', 'I can\'t show the queue if I\'m not even connected to a channel.', 0xFF0000)


@bot.command('past_queue', aliases=["pq", "pastq", "past_q"], help="Show the past queue of already played songs")
async def past_queue(ctx):
    """Shows the past queue"""

    bot_vc = ctx.voice_client
    if bot_vc:
        if bot_vc.past_queue == []:
            return await send_embed(ctx, 'Nothing in past queue.', 'I can\'t show a past queue when there\'s nothing in it.', 0xFF0000)
        else:
            # Send an embed message to the discord channel
            return await send_past_queue_embed(ctx, bot_vc.past_queue, 0x0000FF)
    
    return await send_embed(ctx, 'I\'m not connected to any voice channel.', 'I can\'t show the past queue if I\'m not even connected to a channel.', 0xFF0000)


@bot.command('loop', help='Loop the current song')
async def loop(ctx):
    """Loops the current song"""

    bot_vc = ctx.voice_client
    if bot_vc:
        if bot_vc.is_playing() and not bot_vc.is_paused():

            is_loop = bot_vc.toggle_loop()
            
            if is_loop:
                return await send_embed(ctx, 'Loop enabled.', 'The current song will be looped.', 0x00FF00)
            else:
                return await send_embed(ctx, 'Loop disabled.', 'The current song will no longer be looped.', 0xFF0000)

        return await send_embed(ctx, 'Nothing is playing.', 'I can\'t loop songs if nothing is playing.', 0xFF0000)
    return await send_embed(ctx, 'I\'m not connected to any voice channel.', 'I can\'t loop songs if I\'m not even connected to a channel.', 0xFF0000)


@bot.command('shuffle', help='Shuffle the current queue')
async def shuffle(ctx):
    """Shuffles the current queue"""

    bot_vc = ctx.voice_client
    if bot_vc:
        if bot_vc.is_playing() and not bot_vc.is_paused():

            is_shuffled = bot_vc.toggle_shuffle()

            if is_shuffled:
                return await send_embed(ctx, 'Queue shuffled.', 'The current queue has been shuffled.', 0x00FF00)
            else:
                return await send_embed(ctx, 'Queue unshuffled.', 'The current queue has been unshuffled.', 0xFF0000)

        return await send_embed(ctx, 'Nothing is playing.', 'I can\'t shuffle songs if nothing is playing.', 0xFF0000)
    return await send_embed(ctx, 'I\'m not connected to any voice channel.', 'I can\'t shuffle songs if I\'m not even connected to a channel.', 0xFF0000)


@bot.command('seek', help='Seek to a specific time in the current song')
async def seek(ctx, time):
    """Seeks to a specific time in the current song"""

    bot_vc = ctx.voice_client
    if bot_vc:
        if bot_vc.is_playing() and not bot_vc.is_paused():
            if time.isdigit():
                await bot_vc.seek(int(time) * 1000)
                return await send_embed(ctx, 'Seeked to ' + time + ' seconds.', 'I have seeked to ' + time + ' seconds.', 0x00FF00)

            return await send_embed(ctx, 'Invalid time.', 'Please enter a valid integer time.', 0xFF0000)
        return await send_embed(ctx, 'Nothing is playing.', 'I can\'t seek inside songs if nothing is playing.', 0xFF0000)
    return await send_embed(ctx, 'I\'m not connected to any voice channel.', 'I can\'t seek inside songs if I\'m not even connected to a channel.', 0xFF0000)


@bot.command('fastforward', aliases=['ff'], help='Fast forward the current song in seconds')
async def fastforward(ctx, time):
    """Fast forwards the current song"""

    bot_vc = ctx.voice_client
    if bot_vc:
        if bot_vc.is_playing() and not bot_vc.is_paused():
            if time.isdigit():
                await bot_vc.seek(bot_vc.position + int(time) * 1000)
                return await send_embed(ctx, 'Fast forwarded ' + time + ' seconds.', 'I have fast forwarded ' + time + ' seconds.', 0x00FF00)
            
            return await send_embed(ctx, 'Invalid time.', 'Please enter a valid integer time.', 0xFF0000)
        return await send_embed(ctx, 'Nothing is playing.', 'I can\'t fast forward songs if nothing is playing.', 0xFF0000)
    return await send_embed(ctx, 'I\'m not connected to any voice channel.', 'I can\'t fast forward songs if I\'m not even connected to a channel.', 0xFF0000)


@bot.command('rewind', aliases=['rw', 'back'], help='Rewind the current song in seconds')
async def rewind(ctx, time):
    """Rewinds the current song"""

    bot_vc = ctx.voice_client
    if bot_vc:
        if bot_vc.is_playing() and not bot_vc.is_paused():
            if time.isdigit():
                await bot_vc.seek(bot_vc.position - int(time) * 1000)
                return await send_embed(ctx, 'Rewinded ' + time + ' seconds.', 'I have rewinded ' + time + ' seconds.', 0x00FF00)

            return await send_embed(ctx, 'Invalid time.', 'Please enter a valid integer time.', 0xFF0000)
        return await send_embed(ctx, 'Nothing is playing.', 'I can\'t rewind songs if nothing is playing.', 0xFF0000)
    return await send_embed(ctx, 'I\'m not connected to any voice channel.', 'I can\'t rewind songs if I\'m not even connected to a channel.', 0xFF0000)


@bot.command('volume', aliases=["vol"], help='Change the bot\'s volume')
async def volume(ctx, volume):
    """Changes the volume of the bot"""

    bot_vc = ctx.voice_client
    if bot_vc:
        if bot_vc.channel is not None:
            if volume.isdigit():
                await bot_vc.set_volume(int(volume))
                return await send_embed(ctx, 'Volume changed to ' + volume + '%.', 'I have changed the volume to ' + volume + '%.', 0x00FF00)
            elif volume == 'reset':
                await bot_vc.set_volume(100)
                return await send_embed(ctx, 'Volume reset to 100%.', 'I have reset the volume to 100%.', 0x00FF00)
            
            return await send_embed(ctx, 'Invalid volume.', 'Please enter a valid integer volume.', 0xFF0000)
        return await send_embed(ctx, 'Nothing is playing.', 'I can\'t change the volume if I\'m not playing anything.', 0xFF0000)
    return await send_embed(ctx, 'I\'m not connected to any voice channel.', 'I can\'t change the volume if I\'m not even connected to a channel.', 0xFF0000)


@bot.command('copy', aliases=["cp"], help='Reinsert the song in a new index')
async def copy(ctx):
    """Reinsert the song in a new index"""

    real_index_1 = await validate_index(ctx, 1)
    if real_index_1 == None:
        return await send_embed(ctx, 'Invalid first index.', 'Please enter a valid integer index.', 0xFF0000)

    real_index_2 = await validate_index(ctx, 2)
    if real_index_2 == None:
        return await send_embed(ctx, 'Invalid second index.', 'Please enter a valid integer index.', 0xFF0000)

    bot_vc = ctx.voice_client
    if bot_vc:
        if bot_vc.is_playing() and not bot_vc.is_paused():
            if(real_index_1 < len(bot_vc.queue) and real_index_2 < len(bot_vc.queue) + 1):
                bot_vc.queue.put_at_index(real_index_2, bot_vc.queue[real_index_1])
                return await send_embed(ctx, 'Reinserted song.', f'I have copied the song **{bot_vc.queue[real_index_1]}** to __index #{real_index_2 + 1}__.', 0x00FF00)
            
            return await send_embed(ctx, 'Invalid index.', 'Please enter an index that doesn\'t exceed the queue\'s length.', 0xFF0000)
        return await send_embed(ctx, 'Nothing is playing.', 'I can\'t swap songs if nothing is playing.', 0xFF0000)
    return await send_embed(ctx, 'I\'m not connected to any voice channel.', 'I can\'t swap songs if I\'m not even connected to a channel.', 0xFF0000)


@bot.command('swap', alias=['switch'], help='Swap the song with the index of another song')
async def swap(ctx):
    """Reinsert the song in a new index"""

    real_index_1 = await validate_index(ctx, 1)
    if real_index_1 == None:
        return await send_embed(ctx, 'Invalid first index.', 'Please enter a valid integer index.', 0xFF0000)

    real_index_2 = await validate_index(ctx, 2)
    if real_index_2 == None:
        return await send_embed(ctx, 'Invalid second index.', 'Please enter a valid integer index.', 0xFF0000)

    bot_vc = ctx.voice_client
    if bot_vc:
        if bot_vc.is_playing() and not bot_vc.is_paused():
            if(real_index_1 < len(bot_vc.queue) and real_index_2 < len(bot_vc.queue)):
                if real_index_1 < real_index_2:
                    song_1 = bot_vc.queue[real_index_1]
                    song_2 = bot_vc.queue[real_index_2]

                    del bot_vc.queue[real_index_2]
                    bot_vc.queue.put_at_index(real_index_2, song_1)
                    
                    del bot_vc.queue[real_index_1]
                    bot_vc.queue.put_at_index(real_index_1, song_2)

                elif real_index_1 > real_index_2:
                    song_1 = bot_vc.queue[real_index_1]
                    song_2 = bot_vc.queue[real_index_2]

                    del bot_vc.queue[real_index_1]
                    bot_vc.queue.put_at_index(real_index_1, song_2)
                    
                    del bot_vc.queue[real_index_2]
                    bot_vc.queue.put_at_index(real_index_2, song_1)

                else:
                    return await send_embed(ctx, 'Invalid indexes.', 'Please enter two different indexes.', 0xFF0000)
                return await send_embed(ctx, 'Swapped songs.', f'I have swapped the song **{song_1}** in __index {real_index_1 + 1}__ for **{song_2}** in __index {real_index_2 + 1}__.', 0x00FF00)

            return await send_embed(ctx, 'Invalid index.', 'Please enter an index that doesn\'t exceed the queue\'s length.', 0xFF0000)
        return await send_embed(ctx, 'Nothing is playing.', 'I can\'t swap songs if nothing is playing.', 0xFF0000)
    return await send_embed(ctx, 'I\'m not connected to any voice channel.', 'I can\'t swap songs if I\'m not even connected to a channel.', 0xFF0000)


@bot.command('remove', aliases=["rm", "del", "delete"], help='Remove the given index of a song from the queue')
async def remove(ctx, index):
    """Removes the given index of a song from the queue"""

    real_index = await validate_index(ctx, 1)
    if real_index == None:
        return await send_embed(ctx, 'Invalid index.', 'Please enter a valid integer index.', 0xFF0000)

    bot_vc = ctx.voice_client
    if bot_vc:
        if bot_vc.is_playing() and not bot_vc.is_paused():
            if(real_index < len(bot_vc.queue)):
                song = bot_vc.queue[real_index]
                del bot_vc.queue[real_index]
                return await send_embed(ctx, f'Removed song. I have removed the song {song}.', 'Index {index} of the queue removed', 0x00FF00)
            
            return await send_embed(ctx, 'Invalid index.', 'Please enter an index that doesn\'t exceed the queue\'s length.', 0xFF0000)
        return await send_embed(ctx, 'Nothing is playing.', 'I can\'t remove songs if nothing is playing.', 0xFF0000)
    return await send_embed(ctx, 'I\'m not connected to any voice channel.', 'I can\'t remove songs if I\'m not even connected to a channel.', 0xFF0000)


@bot.command('current_song', aliases=["current", "actual", "song", "currentsong", "currentSong", "cs"], help='Displays the current song\'s information')
async def current_song(ctx):
    """Displays the current song's information"""

    bot_vc = ctx.voice_client
    if bot_vc:
        if bot_vc.is_playing():
            song = bot_vc.track
            # Convert the duration to minutes and seconds
            current_time = convert_seconds_to_time(bot_vc.position)
            total_time = convert_seconds_to_time(song.length)
            return await send_embed(ctx, f'**Now playing: {song.title}**', f'Playing in **{bot_vc.channel}** voice channel\n\nBy __{song.author}__\n\n*Duration:* **{current_time}** / **{total_time}**', 0x00FF00, song.thumbnail, song.uri)

        return await send_embed(ctx, 'Nothing is playing.', 'I can\'t display the current song if nothing is playing.', 0xFF0000)
    return await send_embed(ctx, 'I\'m not connected to any voice channel.', 'I can\'t display the current song if I\'m not even connected to a channel.', 0xFF0000)


@bot.command('lyrics', aliases=["lyric", "ly"], help='Displays the lyrics of the current song')
async def lyrics(ctx):
    """Displays the lyrics of the current song"""

    parameter_sent = True

    try:
        song_title = ctx.message.content.split(' ', 1)[1]
        song_title = song_title.strip()

    except:
        parameter_sent = False

    finally:

        try:
            song_title = song_title.split('|', 1)[0].strip()
            song_artist = song_title.split('|', 1)[1].strip()
        except:
            song_artist = None

        bot_vc = ctx.voice_client
        if bot_vc:
            if bot_vc.is_playing() and not bot_vc.is_paused():
                
                # If the user didn't send a parameter, then the lyrics of the current song will be displayed
                if parameter_sent == False:
                    song = bot_vc.track
                    song_title = song.title

                lyrics = await get_lyrics(song_title, song_artist)
                if lyrics == None:
                    return await send_embed(ctx, 'Lyrics not found.', f'I couldn\'t find the lyrics of the song: *{song_title}* in __some-random-api.ml__.', 0xFF0000)
                
                return await send_lyrics_pagination(ctx, lyrics)
            return await send_embed(ctx, 'Nothing is playing.', 'I can\'t display the lyrics if nothing is playing.', 0xFF0000)
        return await send_embed(ctx, 'I\'m not connected to any voice channel.', 'I can\'t display the lyrics if I\'m not even connected to a channel.', 0xFF0000)


@bot.command('clearqueue', aliases=["clean", "cq", "c"], help='Clears the queue')
async def clearqueue(ctx):
    """Clears the queue"""

    bot_vc = ctx.voice_client
    if bot_vc:
        if len(bot_vc.queue) > 0:
            bot_vc.queue.clear()
            return await send_embed(ctx, 'Queue cleared.', 'I have cleared the queue.', 0x00FF00)

        return await send_embed(ctx, 'Nothing is playing.', 'I can\'t clear the queue if nothing is playing.', 0xFF0000)
    return await send_embed(ctx, 'I\'m not connected to any voice channel.', 'I can\'t clear the queue if I\'m not even connected to a channel.', 0xFF0000)


@bot.command('save_playlist', aliases=["save_p", "savep", "saveplaylist", "savePlaylist"], help='Saves the current queue as a playlist')
async def save_playlist(ctx):
    """Saves the current queue as a playlist"""

    try:
        playlist_name = ctx.message.content.split(' ', 1)[1].strip()
    except:
        return await send_embed(ctx, 'Invalid playlist name.', 'Please enter a valid playlist name.', 0xFF0000)
    bot_vc = ctx.voice_client

    if bot_vc:
        if len(bot_vc.queue) > 0:
            playlist = bot_vc.queue
            db.save_playlist(playlist_name, playlist, PATH)
            return await send_embed(ctx, 'Playlist saved.', f'I have saved the queue as a playlist: *{playlist_name}*', 0x00FF00)

        return await send_embed(ctx, 'Nothing is playing.', 'I can\'t save the queue if nothing is playing.', 0xFF0000)
    return await send_embed(ctx, 'I\'m not connected to any voice channel.', 'I can\'t save the queue if I\'m not even connected to a channel.', 0xFF0000)


@bot.command('get_playlist', aliases=["get_p", "getp", "getpl", "getplaylist", "getplay", "get_play"], help='Gets the given playlist')
async def get_playlist(ctx):
    """Gets the given playlist"""

    try:
        playlist_name = ctx.message.content.split(' ', 1)[1].strip()
    except:
        return await send_embed(ctx, 'No playlist name sent.', 'Please enter a valid playlist name.', 0xFF0000)

    playlist = db.get_playlist_songs(playlist_name, PATH)
    if playlist is not None:
        if playlist != []:
            return await send_playlist_pagination(ctx, playlist_name, playlist)
    return await send_embed(ctx, 'Playlist not found.', f'I couldn\'t find the playlist: *{playlist_name}* in the database.', 0xFF0000)


@bot.command('get_playlists', aliases=["playlists", "get_plays", "getplays", "getpls", "get_ps"], help='Gets all the playlists')
async def get_playlists(ctx):
    """Gets all the playlists"""

    playlists = db.get_all_playlists(PATH)
    if playlists is not None:
        if playlists != []:
            return await send_playlists_pagination(ctx, playlists)
    return await send_embed(ctx, 'No playlists found.', f'I couldn\'t find any playlists in the database.', 0xFF0000)


@bot.command('play_playlist', aliases=["play_p", "playp", "playplaylist", "playplay", "play_play", "play_pl", "playpl"], help='Plays the given playlist')
async def play_playlist(ctx):
    """Plays the given playlist"""

    try:
        playlist_name = ctx.message.content.split(' ', 1)[1].strip()
    except:
        return await send_embed(ctx, 'No playlist name sent.', 'Please enter a valid playlist name.', 0xFF0000)

    playlist = db.get_playlist_songs(playlist_name, PATH)
    if playlist is not None:
        if playlist != []:
            bot_vc = ctx.voice_client
            vc_active = True
            if not bot_vc:
                custom_player = CustomPlayer()
                bot_vc: CustomPlayer = await ctx.author.voice.channel.connect(cls=custom_player)
                vc_active = False
            
            for i, song in enumerate(playlist):
                track = await wavelink.YouTubeTrack.search(query=f"{song[0]}", return_first=True)
                
                if i == 0 and vc_active == False:
                    await bot_vc.play(track)
                else:
                    bot_vc.queue.put(track)

            # Send an embed message to the discord channel
            return await send_embed(ctx, 'Playlist added to the queue.', f'I have added the playlist: *{playlist_name}* to the queue.', 0x00FF00)

        return await send_embed(ctx, 'Playlist is empty.', f'The playlist: *{playlist_name}* is empty.', 0xFF0000)
    return await send_embed(ctx, 'Playlist not found.', f'I couldn\'t find the playlist: *{playlist_name}* in the database.', 0xFF0000)


@bot.command('delete_playlist', aliases=["delete_p", "deletep", "deleteplaylist", "deletePlaylist", "delp", "del_p"], help='Deletes the given playlist')
async def delete_playlist(ctx, playlist_name):
    """Deletes the given playlist"""

    playlist = db.delete_playlist(playlist_name, PATH)

    if playlist is not None:
        return await send_embed(ctx, 'Playlist deleted.', f'I have deleted the playlist: *{playlist_name}* from the database.', 0x00FF00)
    
    return await send_embed(ctx, 'Playlist not found.', f'I couldn\'t find the playlist: *{playlist_name}* in the database.', 0xFF0000)



# Error handling
@play.error
async def play_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        return await send_embed(ctx, 'Could not find track.', '', 0x00FF00)



# Command to delete discord channel messages
@bot.command('clear', aliases=["clr", "cls"], help='Delete N messages from a text channel')
async def clear(ctx, amount):
    """Deletes the last X messages in the channel"""
    if(amount.isdigit()):
        await ctx.channel.purge(limit=int(amount))
        deletion_embed = await send_embed(ctx, 'Message deletion', 'I have deleted ' + amount + ' messages.', 0x00FF00)
        await asyncio.sleep(4.5)
        return await deletion_embed.delete()
    else:
        return await send_embed(ctx, 'Invalid amount.', 'Please enter a valid integer amount.', 0xFF0000)

# Command to disconnect a user from the voice channel
@bot.command('disconnect', aliases=['disc'], help='Disconnect tagged user from the voice channel')
async def disconnect(ctx, member: discord.Member):
    """Disconnect a user from the voice channel"""
    # Get the voice channel of the member
    if(member.voice.channel is not None):
        await member.move_to(None)
        return await send_embed(ctx, "User disconnection", f"User {member.name} has been disconnected from the voice channel", 0xFFFF11)
    else:
        return await send_embed(ctx, "User disconnection", f"User {member.name} is not in a voice channel", 0xFFFF11)

# Command to deafen a user
@bot.command('deafen', aliases=['deaf'], help='Deafen tagged user')
async def deafen(ctx, member: discord.Member):
    """Deafen a user"""
    await member.edit(deafen=True)
    return await send_embed(ctx, "User Deafened", f"{member} has been deafened", 0xFFFF11)

# Command to undeafen a user
@bot.command('undeafen', aliases=['undeaf'], help='Undeafen tagged user')
async def undeafen(ctx, member: discord.Member):
    """Undeafen a user"""
    await member.edit(deafen=False)
    return await send_embed(ctx, "Undeafen", f'{member} has been undeafened', 0xFFFF11)

# Command to mute a user
@bot.command('mute', aliases=['m'], help='Mute tagged user')
async def mute(ctx, member: discord.Member):
    """Mute a user"""
    await member.edit(mute=True)
    return await send_embed(ctx, "User Muted", f"{member} has been muted", 0xFFFF11)

# Command to unmute a user
@bot.command('unmute', aliases=['unm'], help='Unmute tagged user')
async def unmute(ctx, member: discord.Member):
    """Unmute a user"""
    await member.edit(mute=False)
    return await send_embed(ctx, "User Unmuted", f"{member} has been unmuted", 0xFFFF11)

# Command to move a user to a voice channel
@bot.command('change', aliases=['move'], help='Move tagged user to another voice channel')
async def move(ctx, member: discord.Member or str):
    """Move a user to a voice channel"""
    
    if type(member) is discord.Member:

        # Get a list of all the voice channels
        voice_channels = ctx.guild.voice_channels
        channel_name = ctx.message.content.split('>', 1)[1].strip()

        for voice_channel in voice_channels:
            if(channel_name.lower() in voice_channel.name.lower() and voice_channel.name != 'Socios Ludens'):
                await member.move_to(voice_channel)
                return await send_embed(ctx, "User moved", f"{member} has been moved to {voice_channel}", 0xFFFF11)
        
        return await send_embed(ctx, "Channel not found", f"{member} has not been moved to {channel_name} because it was not found", 0xFFFF11)
    return await send_embed(ctx, "No discord member received", "Please tag a discord member", 0xFF0000)

# Command to invoke a user into your voice channel
@bot.command('invoke', aliases=['invocacion', 'invocación'], help='Invoke tagged user by moving him/her to many voice channels')
async def move(ctx, member: discord.Member or str, amount=10):
    """Move a user accross many voice channels"""
    
    if type(member) is discord.Member:

        # Get a list of all the voice channels
        voice_channels = ctx.guild.voice_channels
        author_channel = ctx.author.voice.channel

        if amount > 15:
            amount = 15

        # Move the user to random voice channels a certain number of times
        for j in range(amount):
            if member.voice.channel is not None:
                if(j == amount - 1):
                    await member.move_to(author_channel)
                    return await send_embed(ctx, "User moved", f"{member} has been invoked", 0xFFFF11)
                else:
                    random_index = random.randint(0, len(voice_channels) - 1)
                    await member.move_to(voice_channels[random_index])
            else:
                return await send_embed(ctx, "User disconnected", f"{member} isn't connected in any voice channel", 0xFFFF11)
            
    return await send_embed(ctx, "No discord member received", "Please tag a discord member", 0xFF0000)

# Command to get a cat picture
@bot.command('miau', aliases=['meow', 'meeau', 'meaw'])
async def miau(ctx):
    """Meow back"""
    # Randomize a number of strings that say meow
    meow_strings = ['Meow', 'Miau', 'Meeau', 'Meaw', 'Miau Miau', 'Meeau Meeau', 'Meaw Meaw', 'Miau Miau Miau', 'Meeau Meeau Meeau', 'Meaw Meaw Meaw']
    random_index = random.randint(0, len(meow_strings) - 1)

    # Get random cat image from an API call
    response = requests.request("GET", "https://aws.random.cat/meow", headers={}, data={})
    return await send_embed(ctx, meow_strings[random_index], '', 0xffff11, image=response.json()['file'])

# Command to turn off bot
@bot.command('off', help='Restart the bot in case it gets buggy')
async def off(ctx):
    """Turn off the bot"""
    if(check_admin_authors(ctx.author.id)):
        await ctx.send("Turning off...")
        exit()
    else:
        await ctx.send("You don\'t have permission to do that.")

# Run the bot and the birthday check loop
async def main():
    """Run the bot and the event check loop"""

    async with bot:

        # Start the bot
        await bot.start(TOKEN)
        

asyncio.run(main())