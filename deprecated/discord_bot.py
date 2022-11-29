import asyncio, discord, uvicorn, os, requests, json, time, re
import utils.trello as trello
import utils.music_player as music_player
import utils.db as db
from pydantic import BaseModel
from fastapi import FastAPI, Header
from ast import alias
from discord.ext import commands
from dotenv import load_dotenv
from pprint import pprint

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

app = FastAPI()
bot = commands.Bot(command_prefix='-')





# --- FastAPI Methods ---

@app.on_event("startup")
async def startup_event(): 
    """ This function will run before the main API starts and begin the bot's connection with discord """
    asyncio.create_task(bot.start(TOKEN))
    music_player.setup(bot)
    await asyncio.sleep(0.5)

@app.head("/webhook")
async def create_webhook(user_agent: str | None = Header(default=None)):
    print(user_agent)
    print(Header)
    return {"response": 200}

@app.post("/webhook")
async def root(msg: dict): 
    """ API endpoint for sending a message to our discord channel upon receiving a trello webhook response """
    pprint(msg['action']['type'])
    
    try:
        if(msg['action']['type'] == 'addMemberToCard'):
            discord_message = await construct_bot_response(msg)

            # Send the constructed embed message to the discord channel
            await send_trello_notif(discord_message[0], discord_message[1])
            return {"status": 200}

    except:
        try:
            if(msg['action']['type'] == 'createCard' or msg['action']['type'] == 'updateCard'):
                await send_trello_notif(msg)
                return {"status": 200}
                
        except:
            channel = bot.get_channel(int(os.getenv('DISCORD_NOTIFICATION_CHANNEL_ID')))
            await channel.send(msg)
            return {"status": 200}

    return {"status": 200}



# -- Individual Functions for our bot ---

# Security measures to prevent unwanted people from using the bot
def check_authors(author_id):
    author_id = str(author_id)
    allowed_authors = ["323880953137332234", "344710120074248193", "259793695111512065"]

    # Only the associates may use this command
    if author_id not in allowed_authors:
        return False
    else:
        return True

def sanitize_users(discord_user):
    discord_user = discord_user.replace("<@", "")
    discord_user = discord_user.replace("!", "")
    discord_user = discord_user.replace(">", "")
    return discord_user

async def wait_for_response(bot, ctx, timeout = 60.0):
    """ Get the id of the selected item """
    # wait for a response from the original author
    selected_option = await bot.wait_for('message', timeout=timeout, check=lambda message: message.author == ctx.author)

    selected_id = selected_option.content
    return selected_id

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

async def find_mentions(ctx):
    """ Find all mentions in the message, extract them, and return them as a list """

    # Get the member's id
    regex = '<@[0-9]{1,25}>'

    mentions = re.findall(regex, ctx.message.content)     
    members = []

    for mention in mentions:
        # Remove all member mentions from the message
        ctx.message.content = ctx.message.content.replace(mention, "") 

        # Sanitize the member id
        member_id = sanitize_users(mention)
        if(db.check_if_discord_user_exists(member_id, "dbData.db") == False):
            await ctx.send(f'One of your mentioned users is not yet registered! ID: {member_id}')
            return
        members.append(member_id)
    
    return members

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
    await ctx.send(embed=embed)

async def send_trello_notif(constructed_message, url):
    """ Send a discord message to our trello-cmd channel when a trello webhook response is received """
    channel = bot.get_channel(int(os.getenv('DISCORD_NOTIFICATION_CHANNEL_ID')))

    # embed = discord.Embed(
    #     title=f'Trello has been updated!',
    #     description=f'{constructed_message}',
    #     color=0x00FF00,
    #     url=f'{url}'
    # )
    # await channel.send(embed=embed)

    await channel.send(constructed_message)
    
async def construct_bot_response(trello_payload):
    """ Construct a message to send to the discord channel """

    card_name = trello_payload['action']['data']['card']['name']
    card_link = trello_payload['action']['data']['card']['short_link']
    member_trello_id = trello_payload['model']['member']['id']

    # Get the discord ID from our DB relationship table
    discord_id = db.get_users_discord_id(member_trello_id, "dbData.db")
    message = f'<@{discord_id}> has been added to the card: **{card_name}**!'

    return [message, card_link]



# --- Discord Bot Commands ---

# Command to register an employee's discord id and trello username
@bot.command(name="register", help="Register an employee's trello and discord accounts")
async def register(ctx, discord_id = "", trello_id = ""):

    if(discord_id == ""):
        await send_embed(ctx, "Your discord ID is required", "Please try again", 0xFF0000)
        return

    # If the user didn't provide a trello id, ask for it
    if(trello_id == ""):
        await send_embed(ctx, "Trello ID required", "Please reply with your trello ID. To get it just use our Ludens Postman API", 0x00FF00, "https://cdn.discordapp.com/attachments/712062512966795389/1004340286211752028/unknown.png")
        
        try:
            # Get the user's response with their trello ID
            trello_id = await wait_for_response(bot, ctx)
        except asyncio.TimeoutError:
            # End the process since this field is required
            await ctx.send('You ran out of time to answer!')
            return

    discord_id = sanitize_users(discord_id)

    # Insert/Update our DB with the written users
    result = db.register_discord_and_trello_users(discord_id, trello_id, "dbData.db")

    # Return success message in the discord channel
    if(result == "insert"):
        await send_embed(ctx, "Registration", "Your users have been **linked**!")
    else:
        await send_embed(ctx, "Registration", "Your **trello user has been updated**!")



# - Webhook Commands -

# Command to create a webhook in Trello for our board
@bot.command(name="webhook", help="Create a webhook in Trello for one of our boards", aliases=["cwh", "wh", "createwh"])
async def webhook(ctx, webhook_name = ""):
    
    organization_id = os.getenv('TRELLO_ORGANIZATION_ID')
    if(organization_id == None):
        await ctx.send("Trello organization ID not found")
        return
    boards = trello.get_all_boards(organization_id)
    boards_list_response = ""

    for board in boards:
        boards_list_response += f"__{board['name']}__ | *ID:* " + f"**{board['id']}**\n"

    # Ask the user to select a board
    await send_embed(ctx, "Please select the board that the webhook will listen to by replying with said board's ID.", f'{boards_list_response}')

    try:
        # Get the user's response with the board's ID that we will listen to (this could be any model's ID though)
        board_id = await wait_for_response(bot, ctx)
        board_id = board_id.strip()
    except asyncio.TimeoutError:
        # End the process since this field is required
        await ctx.send('You ran out of time to answer!')
        return
    else:
        if(webhook_name != ""):
            webhook_name = ctx.message.content.replace("-webhook ", "").strip()
            webhook_name = webhook_name.replace("-cwh ", "").strip()
            webhook_name = webhook_name.replace("-wh ", "").strip()
            webhook_name = webhook_name.replace("-createwh ", "").strip()

            wh_id = trello.create_webhook(board_id, webhook_name)

            for board in boards:
                if(board["id"] == board_id):
                    board_name = board["name"]
                    break

            db.insert_wh(wh_id, board_name, "dbData.db", board_id)
            await send_embed(ctx, "Webhook created", f'Webhook with id **{wh_id}** created for {board_name}')

        else:

            # Ask the user to select a webhook name
            await send_embed(ctx, "Webhook creation", "If you wish to name this webhook, reply with a description (Optional).")

            try:
                # Get the user's response with the webhook name
                webhook_name = await wait_for_response(bot, ctx)
            except asyncio.TimeoutError:
                webhook_name = ""
                pass
            
            if(webhook_name.lower() == "no" or webhook_name.lower() == "skip"):
                webhook_name = ""

            wh_id = trello.create_webhook(board_id, webhook_name)

            for board in boards:
                if(board["id"] == board_id):
                    board_name = board["name"]
                    break

            db.insert_wh(wh_id, board_name, "dbData.db", board_id)
            await send_embed(ctx, "Webhook created", f'Webhook with id **{wh_id}** created for {board_name}')

# Command to delete a webhook
@bot.command(name="deletewebhook", help="Delete a Trello webhook", aliases=["dwh", "deletehook", "deletewh"])
async def delete(ctx, wh_id = ""):
    
    # If the user provides a webhook id, delete it
    if(wh_id != ""):
        try:
            trello.delete_webhook(wh_id)
            db.delete_webhook(wh_id, "dbData.db")
            await send_embed(ctx, "Webhook deleted", f'Webhook with id **{wh_id}** deleted', 0xFF0000)
            return
        except Exception as e:
            print(e)
            await ctx.send("Webhook not found")
            return
    else:

        active_webhooks = trello.get_all_webhooks()

        # If there are no webhooks, tell the user
        if(not active_webhooks[0]['webhooks']):
            await send_embed(ctx, "No webhooks found", "There are no active webhooks in Trello")
            return

        response_string = ""

        for webhook in active_webhooks:
            response_string += f"__{webhook['webhooks'][0]['description']}__ | *WH ID:* " + f"**{webhook['webhooks'][0]['id']}**\n"

        await send_embed(ctx, "Please reply with the webhook ID that you want to delete.", f'{response_string}')

        try:
            # Get the user's response with the webhook's ID
            wh_id = await wait_for_response(bot, ctx)
        except asyncio.TimeoutError:
            # End the process since this field is required
            await ctx.send('You ran out of time to answer!')
            return
        else:
            trello.delete_webhook(wh_id)
            db.delete_webhook(wh_id, "dbData.db")
            await send_embed(ctx, "Webhook deleted", f'Webhook with id **{wh_id}** deleted', 0xFF000)



# - Cards' commands -
@bot.command(name='cc', help='Trello creation of a list, card title, and its description')
async def disc_create_card(ctx, card_info = None):
    
    organization_id = os.getenv('TRELLO_ORGANIZATION_ID')
    if(organization_id == None):
        await ctx.send("Trello organization ID not found")
        return
    boards = trello.get_all_boards(organization_id)
    boards_list_response = ""

    # Construct response string with all the boards
    for board in boards:
        boards_list_response += f"__{board['name']}__ | *ID:* " + f"**{board['id']}**\n"

    # Get the message's image URL
    image_url = await get_image_url(ctx)
    
    # Find mentions in the message
    members = await find_mentions(ctx)

    # Now we must get the trello id equivalent to each of the discord ID's from our DB
    for count, member in enumerate(members):
        members[count] = db.get_users_trello_id(member, "dbData.db")




    # If the message has at least 1 argument, we can assume that the user wants to create a card
    if(len(ctx.message.content.split(' ')) > 0):

        # If the user sends both the card and its description separated by pips
        if(len(ctx.message.content.split('|')) >= 2 and len(ctx.message.content.split(' ')) >= 1):

            card_title = ctx.message.content.split('|')[0].split('-cc ')[1].strip()
            card_description = ctx.message.content.split('|')[1].strip()

            # Ask the user to select a board
            await send_embed(ctx, "Please select a board by replying with the ID of the board you want to use.", f'{boards_list_response}', 0xFF0000)

            try:
                # Get the user's response with the board's ID
                board_id = await wait_for_response(bot, ctx)
            except asyncio.TimeoutError:
                # End the process since this field is required
                await ctx.send('You ran out of time to answer!')
                return
            else:

                lists = trello.get_all_lists(board_id)
                if lists == None:
                    await send_embed(ctx, "Board not found", f"Board with id **{board_id}** not found", 0xFF0000)
                    return
                list_of_lists = []
                list_of_lists_response = ""

                for list in lists:
                    list_tuple = (list["id"], list["name"])
                    list_of_lists.append(list_tuple)
                    list_of_lists_response += f"__{list['name']}__ | *ID:* " + f"**{list['id']}**\n"

                # Ask the user to select a board
                await send_embed(ctx, "Please select a list by replying with the ID of the one you want to use.", f'{list_of_lists_response}', 0xFF0000)

                try:
                    # Get the user's response
                    list_id = await wait_for_response(bot, ctx)
                except asyncio.TimeoutError:
                    # End the process since this field is required
                    await ctx.send('You ran out of time to answer!')
                    return

                else:

                    # Create the card
                    card_info = trello.create_card_description(list_id, card_title, card_description, image_url, members)

                    # Send a message to the discord channel
                    await send_embed(ctx, "Trello Card Created", "Created a **card** with **description**", 0xFFFF11, "", f'{card_info["short_url"]}')

        else:

            # If the user sends just the card
            card_title = ctx.message.content.split('-cc ')[1].strip()
            
            # Ask the user to select a list
            await send_embed(ctx, "Please select a board by typing the number of the board you want to use.", f'{boards_list_response}', 0xFF0000)

            try:
                # Get the user's response with the board's ID
                board_id = await wait_for_response(bot, ctx)
            except asyncio.TimeoutError:
                # End the process since this field is required
                await ctx.send('You ran out of time to answer!')
                return
            else:

                lists = trello.get_all_lists(board_id)
                if lists == None:
                    await send_embed(ctx, "Board not found", f"Board with id **{board_id}** not found", 0xFF0000)
                    return
                list_of_lists = []
                list_of_lists_response = ""

                for list in lists:
                    list_tuple = (list["id"], list["name"])
                    list_of_lists.append(list_tuple)
                    list_of_lists_response += f"__{list['name']}__ | *ID:* " + f"**{list['id']}**\n"

                # Ask the user to select a list
                await send_embed(ctx, "Please select a list by replying with the ID of the one you want to use.", f'{list_of_lists_response}', 0xFF0000)

                try:
                    # Get the list that the user responded with
                    list_id = await wait_for_response(bot, ctx)
                except asyncio.TimeoutError:
                    # End the process since this field is required
                    await ctx.send('You ran out of time to answer!')
                    return
                else:
                    
                    # Ask the user to reply with the card's description
                    await send_embed(ctx, "Please reply with the card's description (optional).", "", 0xFF0000)

                    try:
                        # Get the user's response with the card's description
                        card_description = await wait_for_response(bot, ctx)
                    except asyncio.TimeoutError:
                        # Create the card since this field is optional
                        card_info = trello.create_card_description(list_id, card_title, "", image_url, members)

                        # Send a message to the discord channel
                        await send_embed(ctx, "Trello Card Created", "Created a **card**", 0xFFFF11, "", f'{card_info["short_url"]}',)

                    else:
                        if(card_description.lower() == "no" or card_description.lower() == "skip"):
                            card_description = ""

                        # Create the card
                        card_info = trello.create_card_description(list_id, card_title, card_description, image_url, members)

                        # Send a message to the discord channel
                        await send_embed(ctx, "Trello Card Created", "Created a **card** with **description**", 0xFFFF11, "", f'{card_info["short_url"]}')
    else:
        await ctx.send("Please enter a board name or the parameters separated by pipes")
        return


@bot.command(name='c3', help='Trello creation of a list, card title, and its description')
async def disc_create_list_card(ctx, list_name = None):

    organization_id = os.getenv('TRELLO_ORGANIZATION_ID')
    if(organization_id == None):
        await ctx.send("Trello organization ID not found")
        return
    boards = trello.get_all_boards(organization_id)
    boards_list_response = ""

    # Construct response string with all the boards
    for board in boards:
        boards_list_response += f"__{board['name']}__ | *ID:* " + f"**{board['id']}**\n"

    # Get the message's image URL
    image_url = await get_image_url(ctx)
    
    # Find mentions in the message
    members = await find_mentions(ctx)

    # Now we must get the trello id equivalent to each of the discord ID's from our DB
    for count, member in enumerate(members):
        members[count] = db.get_users_trello_id(member, "dbData.db")




    # If the message has 3 arguments separated by pipes, we can assume that the user wants to create a list and a card with description
    if(len(ctx.message.content.split('|')) >= 2 and list_name != None):

        # Ask the user to select a board
        await send_embed(ctx, "Please select a board by typing the number of the board you want to use.", f'{boards_list_response}')

        try:
            selected_board = await wait_for_response(bot, ctx)
        except asyncio.TimeoutError:
            # End the process since this field is required
            await ctx.send('You ran out of time to answer!')
            return
        else:
            for board in boards:
                if(board["id"] == selected_board.strip()):
                    board_id = board["id"]
                    break
        
        if not board_id:
            await ctx.send("Please enter a valid board ID")
            return

        # Get the list title
        list_name = ctx.message.content.split('|')[0]
        list_name = list_name.strip()

        # Get the card title
        card_title = ctx.message.content.split('|')[1].strip()

        # Create the board, list, and card
        card_info = trello.create_list_card_description(board_id, list_name, card_title, image_url, members)

        # Send a message to the discord channel
        await send_embed(ctx, "Trello Card Created", "Created a **list** and a **card** with **description**", 0xFFFF11, "", f'{card_info["short_url"]}')

    elif(list_name != None):

        list_name = ctx.message.content.split('|')[0].split('-c3 ')[1]
        list_name = list_name.strip()

        # Now ask for the board's name
        await send_embed(ctx, "Type the board's id in which your list will be inserted.", f'{boards_list_response}', 0x00FF11)

        try:
            board_id = await wait_for_response(bot, ctx)
        except asyncio.TimeoutError:
            # End the process since this field is required
            await ctx.send('You ran out of time to answer!')
            return
        else:

            # Since we received the list name, ask for the card title
            await ctx.send(f'Now send your card\'s title')

            try:
                card_title = await wait_for_response(bot, ctx)
            except asyncio.TimeoutError:
                # End the process since this field is required
                await ctx.send('You ran out of time to answer!')
                return
            else:

                # Since we received the list name, ask for the card description
                await ctx.send(f'Finally, type your card\'s description (optional)')

                try:
                    card_description = await wait_for_response(bot, ctx)
                except asyncio.TimeoutError:
                    
                    # End the process since this field is required
                    await ctx.send('You ran out of time to answer! Since this is an optional field, I\'ll create your card without a description.')

                    # Create the board, list, and card
                    card_info = trello.create_list_card_description(board_id, list_name, card_title, "", image_url, members)

                    await send_embed(ctx, "Trello Card Created", "Created a **list** and a **card** with **description**", 0xFFFF11, "", f'{card_info["short_url"]}')
                    return
                else:

                    if(card_description.lower() == "no" or card_description.lower() == "skip"):
                        card_description = ""
                
                    # Create the board, list, and card
                    card_info = trello.create_list_card_description(board_id, list_name, card_title, card_description, image_url, members)

                    await send_embed(ctx, "Trello Card Created", "Created a **list** and a **card** with **description**", 0xFFFF11, "", f'{card_info["short_url"]}')
                    return
    else:
        await ctx.send("Please enter a board name or the parameters separated by pipes")
        return


@bot.command(name='c4', help='Trello creation of a board, list, card title, and description')
async def disc_create_board_list_card_description(ctx, board_name = None):

    if(check_authors(ctx.message.author.id) == False):
        await send_embed(ctx, "Trello Board, List, and Card creation", "You are not authorized to use this command.", 0xFF0000)
        return


    organization_id = os.getenv("TRELLO_ORGANIZATION_ID")
    if(organization_id == None):
        await ctx.send("Trello organization ID not found")
        return

    # Get the message's image URL
    image_url = await get_image_url(ctx)
    
    # Find mentions in the message
    members = await find_mentions(ctx)

    # Now we must get the trello id equivalent to each of the discord ID's from our DB
    for count, member in enumerate(members):
        members[count] = db.get_users_trello_id(member, "dbData.db")




    # If the message has 4 arguments separated by pipes, we can assume that the user wants to create a board, a list, and a card
    if(len(ctx.message.content.split('|')) >= 4 and board_name != None):

        # Get the board name
        board_name = ctx.message.content.split('|')[0].split('-c4 ')[1]
        board_name = board_name.strip()

        # Get the list title
        list_name = ctx.message.content.split('|')[1].strip()

        # Get the card title
        card_title = ctx.message.content.split('|')[2].strip()

        # Get the card description
        card_description = ctx.message.content.split('|')[3].strip()

        # Create the board, list, and card
        card_info = trello.create_board_list_card_description(board_name, list_name, card_title, "", card_description, organization_id, image_url, members)

        # Send a message to the discord channel
        await send_embed(ctx, "Trello Card Created", "Created a **board**, a **list**, and a **card** with **description**", 0xFFFF11, "", f'{card_info["short_url"]}', )

    elif(board_name != None):

        board_name = ctx.message.content.split('|')[0].split('-c4 ')[1]
        board_name = board_name.strip()

        # Now ask for the list name
        await ctx.send("Write your list name.")

        try:
            list_name = await wait_for_response(bot, ctx)
        except asyncio.TimeoutError:
            # End the process since this field is required
            await ctx.send('You ran out of time to answer!')
            return
        else:

            # Since we received the list name, ask for the card title
            await ctx.send(f'Now send your card title')

            try:
                card_title = await wait_for_response(bot, ctx)
            except asyncio.TimeoutError:
                # End the process since this field is required
                await ctx.send('You ran out of time to answer!')
                return
            else:
                # Having received the card title, ask for the final field, the card description
                await ctx.send(f'Finally, reply with your card\'s description or type either "no" or "skip" to ignore this field.')

                try:
                    card_description = await wait_for_response(bot, ctx)
                except asyncio.TimeoutError:
                    # Send the info to Trello and respond to discord
                    await ctx.send('You ran out of time to answer!')
                    card_description = ""

                    # Create the board, list, and card
                    card_info = trello.create_board_list_card_description(board_name, list_name, card_title, "", card_description, organization_id, image_url, members)

                    await send_embed(ctx, "Trello Card Created", "Created a **board**, a **list**, and a **card** with **description**", 0xFFFF11, "", f'{card_info["short_url"]}')
                    return
                    
                else:
                    
                    if(card_description.lower() == "no" or card_description.lower() == "skip"):
                        card_description = ""

                    # Create the board, list, and card. Remember that everything except from the board name here is a discord message
                    card_info = trello.create_board_list_card_description(board_name, list_name, card_title, "", card_description, organization_id, image_url, members)

                    await send_embed(ctx, "Trello Card Created", "Created a **board**, a **list**, and a **card** with **description**", 0xFFFF11, "", f'{card_info["short_url"]}')
                    return
    else:
        await ctx.send("Please enter a board name or the parameters separated by pipes")
        return


@bot.command(name='c5', help='Trello creation of board with description, a list, card and its description')
async def disc_create_board__desc_list_card_description(ctx, board_name = None):

    if(check_authors(ctx.message.author.id) == False):
        await send_embed(ctx, "Trello **Board**, **List**, and **Card** creation", "You are not authorized to use this command.", 0xFF0000)
        return


    organization_id = os.getenv('TRELLO_ORGANIZATION_ID')
    if(organization_id == None):
        await ctx.send("Trello organization ID not found")
        return


    # Get the message's image URL
    image_url = await get_image_url(ctx)
    
    # Find mentions in the message
    members = await find_mentions(ctx)


    # Now we must get the trello id equivalent to each of the discord ID's from our DB
    for count, member in enumerate(members):
        members[count] = db.get_users_trello_id(member, "dbData.db")




    # If the message has 5 arguments separated by pipes, we can assume that the user wants to create a board, a list, and a card
    if(len(ctx.message.content.split('|')) >= 5 and board_name != None):

        # Get the board name
        board_name = ctx.message.content.split('|')[0].split('-c5 ')[1]
        board_name = board_name.strip()

        # Get the board description
        board_description = ctx.message.content.split('|')[1].strip()

        # Get the list title
        list_name = ctx.message.content.split('|')[2].strip()

        # Get the card title
        card_title = ctx.message.content.split('|')[3].strip()

        # Get the card description
        card_description = ctx.message.content.split('|')[4].strip()

        # Create the board, list, and card
        card_info = trello.create_board_list_card_description(board_name, list_name, card_title, board_description, card_description, organization_id, image_url, members)

        # Send a message to the discord channel
        await send_embed(ctx, "Trello Card Created", "Created a **board** with **title**, a **list**, and a **card** with **description**", 0xFFFF11, "", f'{card_info["short_url"]}')

    elif(board_name != None):

        board_name = ctx.message.content.split('|')[0].split('-c5 ')[1]
        board_name = board_name.strip()

        # Since we received the board name, ask for said board's optional description
        try:
            await ctx.send('Write down your board\'s description or send either "no" or "skip" to ignore this optional field.')
            board_description = await wait_for_response(bot, ctx)

        except asyncio.TimeoutError:

            # Since the board description was optional, ask for the list name after the timeout
            await ctx.send('You ran out of time to answer! **Please write your list name.**' )
            board_description = ""

            try:
                list_name = await wait_for_response(bot, ctx)
            except asyncio.TimeoutError:
                # End the process since this field is required
                await ctx.send('You ran out of time to answer!')
                return
            else:

                # Since we received the list name, ask for the card title
                await ctx.send(f'Now send your card title')

                try:
                    card_title = await wait_for_response(bot, ctx)
                except asyncio.TimeoutError:
                    # End the process since this field is required
                    await ctx.send('You ran out of time to answer!')
                    return
                else:
                    # Having received the card title, ask for the final field, the card description
                    await ctx.send(f'Finally, reply with your card\'s description or type either "no" or "skip" to ignore this field.')

                    try:
                        card_description = await wait_for_response(bot, ctx)
                    except asyncio.TimeoutError:
                        # Send the info to Trello and respond to discord
                        await ctx.send('You ran out of time to answer!')
                        card_description = ""

                        # Create the board, list, and card
                        card_info = trello.create_board_list_card_description(board_name, list_name, card_title, board_description, card_description, organization_id, image_url, members)

                        await send_embed(ctx, "Trello Card Created", "Created a **board** with **title**, a **list**, and a **card** with **description**", 0xFFFF11, "", f'{card_info["short_url"]}')
                        return
                        
                    else:

                        # Create the board, list, and card
                        card_info = trello.create_board_list_card_description(board_name, list_name, card_title, board_description, card_description, organization_id, image_url, members)

                        await send_embed(ctx, "Trello Card Created", "Created a **board** with **title**, a **list**, and a **card** with **description**", 0xFFFF11, "", f'{card_info["short_url"]}')
                        return

        else:

            if(board_description.lower() == 'no' or board_description.lower() == 'skip'):
                board_description = ""

            # Now ask for the list name
            await ctx.send("Write your list name.")

            try:
                list_name = await wait_for_response(bot, ctx)
            except asyncio.TimeoutError:
                # End the process since this field is required
                await ctx.send('You ran out of time to answer!')
                return
            else:

                # Since we received the list name, ask for the card title
                await ctx.send(f'Now send your card title')

                try:
                    card_title = await wait_for_response(bot, ctx)
                except asyncio.TimeoutError:
                    # End the process since this field is required
                    await ctx.send('You ran out of time to answer!')
                    return
                else:
                    # Having received the card title, ask for the final field, the card description
                    await ctx.send(f'Finally, reply with your card\'s description or type either "no" or "skip" to ignore this field.')

                    try:
                        card_description = await wait_for_response(bot, ctx)
                    except asyncio.TimeoutError:
                        
                        # Send the info to Trello and respond to discord
                        await ctx.send('You ran out of time to answer!')
                        card_description = ""

                        # Create the board, list, and card
                        card_info = trello.create_board_list_card_description(board_name, list_name, card_title, board_description, card_description, organization_id, image_url, members)

                        await send_embed(ctx, "Trello Card Created", "Created a **board** with **title**, a **list**, and a **card** with **description**", 0xFFFF11, "", f'{card_info["short_url"]}')
                        return
                        
                    else:

                        if(card_description.lower() == "no" or card_description.lower() == "skip"):
                            card_description = ""

                        # Create the board, list, and card. Remember that everything except from the board name here is a discord message
                        card_info = trello.create_board_list_card_description(board_name, list_name, card_title, board_description, card_description, organization_id, image_url, members)

                        await send_embed(ctx, "Trello Card Created", "Created a **board** with **title**, a **list**, and a **card** with **description**", 0xFFFF11, "", f'{card_info["short_url"]}')
                        return
    else:
        await ctx.send("Please enter a board name or the parameters separated by pipes")
        return



# - Agile Commands -
@bot.command(name="daily", help="Ask the daily questions on our discord channel")
async def daily(ctx):
    # Grab our daily questions from the SQLite database

    # Send the daily questions to the discord channel
    
    # Store the answers of each user in our database

    pass


@bot.command(name="report", help="Present daily or weekly reports to the discord channel")
async def report(ctx, period):
    # Get the done trello cards' name and link from our database

    # Send the cards to the discord channel as a report

    pass

@bot.command(name="feedback", aliases=["fb"], help="Generate feedback for the sprint")
async def daily(ctx):
    # Grab our feedback questions from the SQLite database

    # Send the feedback questions to the discord channel
    
    # Store the answers of each user in our database

    pass



# On ready
@bot.event
async def on_ready():
    """ On ready, print the bot's name"""
    print(f'{bot.user.name} has connected to Discord!\n')

# On resume
@bot.event
async def on_resumed():
    """On resume, prints the bot's name"""
    print(f'{bot.user.name} has reconnected to Discord!\n')

# Command to delete discord channel messages
@bot.command('delete', aliases=['del, clear'])
async def delete(ctx, amount=100):
    """Deletes the last X messages in the channel"""
    await ctx.channel.purge(limit=amount)
    await ctx.send(f'Deleted {amount} messages')

    # Delete the message that the bot sent
    time.sleep(0.1)
    await ctx.channel.purge(limit=amount)

# Command to remove a user from the voice channel
@bot.command('disconnect', aliases=['disc'])
async def remove(ctx, member: discord.Member):
    """Remove a user from the voice channel"""
    # Get the voice channel of the member
    if(member.voice.channel is not None):
        await member.move_to(None)
        send_embed(ctx, "User disconnection", "User has been disconnected from the voice channel", 0xFFFF11, f'{member.name}')
    else:
        send_embed(ctx, "User disconnection", "User is not in a voice channel", 0xFFFF11, f'{member.name}')
    
# Command to move a user to a voice channel
@bot.command('change', aliases=['con'])
async def move(ctx, member: discord.Member, channel: discord.VoiceChannel):
    """Move a user to a voice channel"""

    channel_text = ctx.message.content.split(' ')[2].strip()
    await member.move_to(channel_text)
    await ctx.send(f'{member} has been moved to {channel_text}')

# Command to deafen a user
@bot.command('deafen', aliases=['deaf'])
async def deafen(ctx, member: discord.Member):
    """Deafen a user"""
    await member.edit(deafen=True)
    await send_embed(ctx, "User Deafened", f"{member} has been deafened", 0xFFFF11)

# Command to undeafen a user
@bot.command('undeafen', aliases=['undeaf'])
async def undeafen(ctx, member: discord.Member):
    """Undeafen a user"""
    await member.edit(deafen=False)
    await send_embed(ctx, "Undeafen", f'{member} has been undeafened', 0xFFFF11)

# Command to mute a user
@bot.command('mute', aliases=['m'])
async def mute(ctx, member: discord.Member):
    """Mute a user"""
    await member.edit(mute=True)
    await send_embed(ctx, "User Muted", f"{member} has been muted", 0xFFFF11)

# Command to unmute a user
@bot.command('unmute', aliases=['unm'])
async def unmute(ctx, member: discord.Member):
    """Unmute a user"""
    await member.edit(mute=False)
    await send_embed(ctx, "User Unmuted", f"{member} has been unmuted", 0xFFFF11)

# Send a message to a channel with said channel's id
# @bot.command('channel')
# async def send(ctx):
#     """Send a the channel ID as a message to the channel"""
#     await ctx.send(f'{ctx.channel.id}')




# Main function
if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=80)
