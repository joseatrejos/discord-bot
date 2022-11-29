import requests, os, json
from dotenv import load_dotenv

load_dotenv()
key = os.getenv('TRELLO_KEY')
token = os.getenv('TRELLO_TOKEN')
organization_id = os.getenv('TRELLO_ORGANIZATION_ID')


# --- Individual functions ---
def create_board(board_name, board_description, id_organization = "5effe6827fea25566f3760e9"):
    """Function to create a board in your organization"""
    url = "https://api.trello.com/1/boards/"
    
    querystring = {
        "name": board_name, 
        "desc": board_description,
        "idOrganization": id_organization,
        "key": key, 
        "token": token
    }

    response = requests.request("POST", url, params=querystring)
    board_id = response.json()["id"]
    return board_id


def get_all_boards(organization_id):
    """Function to get all boards' names and ids from an organization"""
    url = f"https://api.trello.com/1/organizations/{organization_id}/boards?fields=id,name"

    payload = json.dumps({
        "key": os.getenv('TRELLO_KEY'),
        "token": os.getenv('TRELLO_TOKEN')
    })
    headers = {'Content-Type': 'application/json'}

    try:
        boards = requests.request("GET", url, headers=headers, data=payload)
        if boards.status_code == 200:
            return boards.json()
    except:
        pass
    return None


def create_list(board_id, list_name):
    """Function to create a list in a board"""
    url = f"https://api.trello.com/1/boards/{board_id}/lists"

    querystring = {
        "name": list_name,
        "key": key,
        "token": token
    }

    response = requests.request("POST", url, params=querystring)
    list_id = response.json()["id"]
    return list_id


def get_all_lists(board_id):
    """Function to get all lists' names and ids from a board"""
    url = f"https://api.trello.com/1/boards/{board_id}/lists?fields=id,name"
    
    payload = json.dumps({
        "key": os.getenv('TRELLO_KEY'),
        "token": os.getenv('TRELLO_TOKEN')
    })
    headers = {'Content-Type': 'application/json'}

    try:
        lists = requests.request("GET", url, headers=headers, data=payload)
        if lists.status_code == 200:
            return lists.json()
    except:
        pass
    return None


def create_card(list_id, card_name, card_description, image_url = "", members = ""):
    url = f"https://api.trello.com/1/cards"

    querystring = {
        "name": card_name,
        "desc": card_description,
        "idList": list_id,
        "idMembers": members,
        "key": key,
        "token": token
    }
    print(querystring)
    response = requests.request("POST", url, params=querystring)

    if image_url != "":
        add_image_to_card(response.json()["id"], image_url)

    # Convert the response to a dictionary and return it
    card_id = response.json()["id"]
    short_url = response.json()["shortUrl"]
    response_dict = {"id":card_id, "short_url":short_url}
    return response_dict


def add_image_to_card(card_id, image_url = ""):
    """ Function to add an image to a card """
    for image in image_url:

        # After selecting your card in discord, we use the card's id to add an image to it
        url = f"https://api.trello.com/1/cards/{card_id}/attachments"

        querystring = {
            "url": image,
            "card_id": card_id,
            "key": key,
            "token": token
        }

        requests.request("POST", url, params=querystring)


# Webhooks
def create_webhook(board_id, description = "", callback_url = os.getenv('TRELLO_CALLBACK_URL')):
    """ Function to create a webhook """
    url = f"https://api.trello.com/1/webhooks"
    
    querystring = {
        "callbackURL": f"{callback_url}",
        "idModel": f'{board_id}',
        "key": os.getenv('TRELLO_KEY'),
        "token": os.getenv('TRELLO_TOKEN'),
        "description": description
    }
    #print(querystring)

    response = requests.request("POST", url, params=querystring)
    print(response.json())
    return response.json()["id"]

def delete_webhook(webhook_id):
    """ Function to delete a webhook """
    url = f"https://api.trello.com/1/webhooks/{webhook_id}"

    querystring = {
        "key": os.getenv('TRELLO_KEY'),
        "token": os.getenv('TRELLO_TOKEN')
    }

    response = requests.request("DELETE", url, params=querystring)
    return True

def get_all_webhooks():
    """ Function to get all webhooks """
    url = f"https://api.trello.com/1/members/me/tokens"

    payload = json.dumps({
        "key": os.getenv('TRELLO_KEY'),
        "token": os.getenv('TRELLO_TOKEN'),
        "webhooks": "true"
    })
    headers = {'Content-Type': 'application/json'}

    try:
        webhooks = requests.request("GET", url, headers=headers, data=payload)
        if webhooks.status_code == 200:
            return webhooks.json()
    except:
        pass
    return None

# --- Save functions ---

# Create a board-list-card-description
def create_board_list_card_description(board_name, list_name, card_title, board_description = "", card_description = "", id_org = organization_id, image_url = "", members = ""):
    """ Function to create a board-list-card-description """
    # After selecting your organization in discord, we use its id to create a board, a list and a card
    board_id = create_board(board_name, board_description, id_org)
    list_id = create_list(board_id, list_name)
    card_info = create_card(list_id, card_title, card_description, image_url, members)
    return card_info


# Get board and create list-card-description
def create_list_card_description(board_id, list_name, card_title, card_description = "", image_url = "", members = ""):
    """ Function to create a list, a card and said card's description """
    # After selecting yout board in discord, we use the board's id to create a list and a card
    list_id = create_list(board_id, list_name)
    card_info = create_card(list_id, card_title, card_description, image_url, members)
    return card_info

    
def create_card_description(list_id, card_title, card_description = "", image_url = "", members = ""):
    """ Function to create a card & its description """
    # After selecting your board and list in discord, we use the list's id to create a card
    card_info = create_card(list_id, card_title, card_description, image_url, members)
    return card_info
