import os
from telethon.sync import TelegramClient
import telethon.errors
from dotenv import load_dotenv, set_key
from pathlib import Path
from enum import Enum
import asyncio
from telethon.tl.functions.messages import GetDialogFiltersRequest
from telethon.tl.functions.contacts import GetContactsRequest

CONFIG_FOLDER = 'config'
CHANNELS_FILE = os.path.join(CONFIG_FOLDER, 'channels.txt')
MESSAGE_FILE = os.path.join(CONFIG_FOLDER, 'message.txt')

# Define the required fields and their default values
required_fields = {
    'MESSAGE': '',
    'FILE': '',
}

class FolderTags(Enum):
    CONTACT = 0
    NON_CONTACT = 1
    GROUP = 2
    CHANNELS = 3
    BOT = 4

class TelegramBot:
    def __init__(self, api_id, api_hash, phone_number):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.client = TelegramClient(os.path.join(CONFIG_FOLDER, 'session_' + phone_number), api_id, api_hash)

    async def get_folders(self):
        await self.client.connect()
        
        # Ensure you're authorized
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.phone_number)
            await self.client.sign_in(self.phone_number, input('Enter the code: '))

        # Get a list of all the folders
        folders_w_filters = await self.client(GetDialogFiltersRequest())
        return folders_w_filters.filters[1:]

    async def get_folder(self, folder_id):
        await self.client.connect()

        # Ensure you're authorized
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.phone_number)
            await self.client.sign_in(self.phone_number, input('Enter the code: '))

        # Get a list of all the folders
        folders = await self.get_folders()
        return next((folder for folder in folders if int(folder_id) == folder.id), None)
    
    async def list_folders(self):

        folders_w_info = await self.get_folders()
        folders = [(folder.id, folder.title) for folder in folders_w_info]
        folders_file = open(str(os.path.join(CONFIG_FOLDER,f"folders_of_{self.phone_number}.txt")), "w", encoding="utf-8")
        # Print information about each folder
        for id, title in folders:
            print(f"Folder ID: {id}, Title: {title}")
            folders_file.write(f"Folder ID: {id}, Title: {title} \n")
          
        print("List of folders printed successfully!")
    
    async def get_peers_ids_from_folder(self, folder):
        if folder is not None:
            peers = []
            peers.extend(folder.pinned_peers)
            peers.extend(folder.include_peers)
            peers.extend(folder.exclude_peers)
            return [peer.channel_id if isinstance(peer, telethon.types.InputPeerChannel) else peer.user_id if isinstance(peer, telethon.types.InputPeerUser) else peer.chat_id if isinstance(peer, telethon.types.InputPeerChat) else None for peer in peers]
        else:
            return []
        
    async def get_folder_tags(self, folder):
        tags = []

        if folder.contacts:
            tags.append(FolderTags.CONTACT)
        if folder.non_contacts:
            tags.append(FolderTags.NON_CONTACT)
        if folder.groups:
            tags.append(FolderTags.GROUP)
        if folder.broadcasts:
            tags.append(FolderTags.CHANNELS)
        if folder.bots:
            tags.append(FolderTags.BOT)

        return tags

    async def get_chats_from_folder(self, folder_id):
        await self.client.connect()

        # Ensure you're authorized
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.phone_number)
            await self.client.sign_in(self.phone_number, input('Enter the code: '))

        chats = await self.client.get_dialogs()
        folder = await self.get_folder(folder_id)
        peers_ids = await self.get_peers_ids_from_folder(folder)
        folder_tags = await self.get_folder_tags(folder)

        chats_from_folder = [(chat.id, chat.title) for chat in chats for peer in peers_ids if str(peer) in str(chat.id)]

        if folder_tags.__contains__(FolderTags.CONTACT):
            chats_from_folder.extend([(chat.id, chat.title) for chat in chats if isinstance(chat.entity, telethon.types.User) and chat.entity.contact])

        if folder_tags.__contains__(FolderTags.NON_CONTACT):
            chats_from_folder.extend([(chat.id, chat.title) for chat in chats if isinstance(chat.entity, telethon.types.User) and not chat.entity.contact and not chat.entity.bot])

        if folder_tags.__contains__(FolderTags.GROUP):
            chats_from_folder.extend([(chat.id, chat.title) for chat in chats if (isinstance(chat.entity, telethon.types.Channel)) and chat.entity.megagroup])
            chats_from_folder.extend([(chat.id, chat.title) for chat in chats if (isinstance(chat.entity, telethon.types.Chat)) and not chat.entity.deactivated])

        if folder_tags.__contains__(FolderTags.CHANNELS):
            chats_from_folder.extend([(chat.id, chat.title) for chat in chats if isinstance(chat.entity, telethon.types.Channel) and not chat.entity.megagroup])

        if folder_tags.__contains__(FolderTags.BOT):
            chats_from_folder.extend([(chat.id, chat.title) for chat in chats if isinstance(chat.entity, telethon.types.User) and chat.entity.bot])

        chats_from_folder = list(set(chats_from_folder))

        return chats_from_folder
        
    async def list_chats_from_folder(self, folders, folder_id, fill=False):

        await self.client.connect()

        all_folders = False

        # Ensure you're authorized
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.phone_number)
            await self.client.sign_in(self.phone_number, input('Enter the code: '))
        
        if folder_id.lstrip("-").isdigit() and int(folder_id) == -1:
            dialogs_raw = await self.client(GetContactsRequest(hash=0))
            chats = [(user.id, f"{user.first_name} {user.last_name}" if user.last_name else user.first_name) for user in dialogs_raw.users]
        elif folder_id.isdigit() and (int(folder_id) == 0 or int(folder_id) == 1):
            dialogs_raw = await self.client.get_dialogs(folder=int(folder_id))
            chats = [(dialog.id, dialog.title) for dialog in dialogs_raw]
        elif folder_id.isdigit() and any(int(folder_id) == folder.id for folder in folders):
            chats = await self.get_chats_from_folder(folder_id)
        else:
            dialogs_raw = await self.client.get_dialogs()
            chats = [(dialog.id, dialog.title) for dialog in dialogs_raw]
            all_folders = True

        if fill:
            chats_file = open(str(CHANNELS_FILE), "a", encoding="utf-8")
            chats_file.write("\n")
            for id, title in chats:
                chats_file.write(f"{id}\n")

            print("\"channels.txt\" file filled successfully!")

        else:
            
            if all_folders:
                chats_file = open(str(os.path.join(CONFIG_FOLDER,f"chats_of_{self.phone_number}_from_all_folders.txt")), "w", encoding="utf-8")
            else:
                chats_file = open(str(os.path.join(CONFIG_FOLDER,f"chats_of_{self.phone_number}_from_folder_{folder_id}.txt")), "w", encoding="utf-8")

            # Print information about each chat
            for id, title in chats:
                print(f"Chat ID: {id}, Title: {title}")
                chats_file.write(f"Chat ID: {id}, Title: {title} \n")
          
            print("List of chats printed successfully!")


    async def list_chats(self):
        await self.client.connect()

        # Ensure you're authorized
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.phone_number)
            await self.client.sign_in(self.phone_number, input('Enter the code: '))

        # Get a list of all the dialogs (chats)
        dialogs = await self.client.get_dialogs()
        chats_file = open(str(os.path.join(CONFIG_FOLDER,f"chats_of_{self.phone_number}.txt")), "w", encoding="utf-8")
        # Print information about each chat
        for dialog in dialogs:
            print(f"Chat ID: {dialog.id}, Title: {dialog.title}")
            chats_file.write(f"Chat ID: {dialog.id}, Title: {dialog.title} \n")
          
        print("List of groups printed successfully!")

    async def broadcast_message(self, message, channels):
        await self.client.connect()

        # Ensure you're authorized
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.phone_number)
            await self.client.sign_in(self.phone_number, input('Enter the code: '))

        for channel in channels:
            try:
                # Send the message to the channel
                if message["FILE"] != "":
                    await self.client.send_file(channel, message["FILE"], caption=message["MESSAGE"])
                else:
                    await self.client.send_message(channel, message["MESSAGE"])
            except telethon.errors.rpcerrorlist.ChatAdminRequiredError:
                print(f"Skipping channel {channel} as you don't have admin permissions")

        print("Message sent successfully!")

# Function to read credentials from .env file
def read_credentials():
    try:
        load_dotenv(Path(os.path.join(CONFIG_FOLDER, ".env")))
        api_id = os.getenv('API_ID')
        api_hash = os.getenv('API_HASH')
        phone_number = os.getenv('PHONE_NUMBER')
        return api_id, api_hash, phone_number
    except Exception as e:
        print("Error reading .env file:", str(e))
        return None, None, None
    
# Function to write credentials to .env file
def write_credentials(api_id, api_hash, phone_number):
    env_file_path = Path(os.path.join(CONFIG_FOLDER, ".env"))
    env_file_path.touch(mode=0o600, exist_ok=False)
    set_key(dotenv_path=env_file_path, key_to_set="API_ID", value_to_set=api_id)
    set_key(dotenv_path=env_file_path, key_to_set="API_HASH", value_to_set=api_hash)
    set_key(dotenv_path=env_file_path, key_to_set="PHONE_NUMBER", value_to_set=phone_number)

def read_message():
    message = {}
    with open(MESSAGE_FILE, 'r') as f:
        for line in f:
            key, value = line.strip().split('=', 1)
            message[key] = value
    return message

def write_message(message):
    with open(MESSAGE_FILE, 'w') as f:
        for key, value in message.items():
            f.write(f'{key}={value}\n')

def validate_message(message):
    for key in required_fields:
        if key not in message:
            return False
    return True

def setup_message():
    config = {}
    for key in required_fields:
        value = input(f'Enter value for {key} (default: {required_fields[key]}): ') or required_fields[key]
        config[key] = value
    write_message(config)
    return config

async def main():

    # Create config folder if it doesn't exist
    if not os.path.exists(CONFIG_FOLDER):
        os.makedirs(CONFIG_FOLDER)

    # Attempt to read credentials from .env file
    api_id, api_hash, phone_number = read_credentials()

    # If credentials not found in .env file, prompt the user to input them
    if api_id is None or api_hash is None or phone_number is None:
        api_id = input("Enter your API ID: ")
        api_hash = input("Enter your API Hash: ")
        phone_number = input("Enter your phone number: ")
        # Write credentials to .env file for future use
        write_credentials(api_id, api_hash, phone_number)

    bot = TelegramBot(api_id, api_hash, phone_number)

    print("Choose an option:")
    print("1. List All Chats or From Folder")
    print("2. List Folders")
    print("3. Fill \"channesls.txt\" file with chat IDs from options 1")
    print("4. Broadcast Message")
    print("5. Exit")

    choice = input("Enter your choice: ")

    if choice == '1':

        print("ID: -2, will list all chats. If ID is not provided or incorrect this will be the default option.")
        print("ID: -1, will list all chats from your contact list, including those that you have not started a conversation with.")
        print("ID: 0, will list all chats that don’t belong to any folder (pinned chats included).")
        print("ID: 1, will list all arquived chats (pinned chats included).")

        folders_w_info = await bot.get_folders()
        for folder in folders_w_info:
            print(f"ID: {folder.id}, will list chats from {folder.title} folder.")

        folder_id = input("Enter the folder ID you want to list chats from: ")

        await bot.list_chats_from_folder(folders_w_info, folder_id)

    elif choice == '2':
        await bot.list_folders()
    
    elif choice == '3':

        print("Warning! This will ADD the chat IDs to \"channesls.txt\" file, not OVERWRITE them.")
        print("ID: -2, will fill \"channesls.txt\" file with all chats. If ID is not provided or incorrect this will be the default option.")
        print("ID: -1, will fill \"channesls.txt\" file with all chats from your contact list, including those that you have not started a conversation with.")
        print("ID: 0, will fill \"channesls.txt\" file with all chats that don’t belong to any folder (pinned chats included).")
        print("ID: 1, will fill \"channesls.txt\" file with all arquived chats (pinned chats included).")

        folders_w_info = await bot.get_folders()
        for folder in folders_w_info:
            print(f"ID: {folder.id}, will fill \"channesls.txt\" file with chats from {folder.title} folder.")

        folder_id = input("Enter the folder ID you want to list chats from: ")

        await bot.list_chats_from_folder(folders_w_info, folder_id, fill=True)

    elif choice == '4':

        # Check if message file exists
        if not os.path.exists(MESSAGE_FILE):
            print(f'{MESSAGE_FILE} not found. Creating a new one...')
            message = setup_message()
        else:
            message = read_message()
            if not validate_message(message):
                print(f'{MESSAGE_FILE} is missing required fields. Recreating...')
                message = setup_message()

        # Check if message[MESSAGE] is not empty
        if message["MESSAGE"] == "" and message["FILE"] == "":
            print(f'Message is empty. The message cannot be empty unless a file is provided. Please add a message or file path to {MESSAGE_FILE}.')
            return

        # Check if channels file exists
        if not os.path.exists(CHANNELS_FILE):
            print(f'{CHANNELS_FILE} not found. Creating a new one...')
            with open(CHANNELS_FILE, 'w') as f:
                pass
            print(f'{CHANNELS_FILE} created successfully! Please add channel IDs to it. One channel ID per line.')
            return

        # Check if channels file is not empty
        if os.path.getsize(CHANNELS_FILE) <= 0:
            print(f'{CHANNELS_FILE} is empty. Please add channel IDs to it. One channel ID per line.')
            return

        with open(CHANNELS_FILE, 'r') as f:
            channels = [int(line.strip()) for line in f if line.strip()]

        print(f'Broadcasting message to {len(channels)} channels...')

        await bot.broadcast_message(message, channels)
        
        return

    elif choice == '5':
        print("Exiting...")
        return
    else:
        print("Invalid choice. Exiting...")
        return

    await bot.client.disconnect()

# Start the event loop and run the main function
if __name__ == "__main__":
    asyncio.run(main())