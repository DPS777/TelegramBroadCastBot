import os
from telethon.sync import TelegramClient
import telethon.errors
from dotenv import load_dotenv, set_key
from pathlib import Path
from enum import Enum
import asyncio
from telethon.tl.functions.messages import GetDialogFiltersRequest

CONFIG_FOLDER = 'config'
CHANNELS_FILE = os.path.join(CONFIG_FOLDER, 'channels.txt')
MESSAGE_FILE = os.path.join(CONFIG_FOLDER, 'message.txt')

# Define the required fields and their default values
required_fields = {
    'MESSAGE': '',
    'FILE': '',
}

class TelegramBot:
    def __init__(self, api_id, api_hash, phone_number):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.client = TelegramClient(os.path.join(CONFIG_FOLDER, 'session_' + phone_number), api_id, api_hash)

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

    async def list_folders(self):
        await self.client.connect()

        # Ensure you're authorized
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.phone_number)
            await self.client.sign_in(self.phone_number, input('Enter the code: '))

        # Get a list of all the folders
        folders_w_filters = await self.client(GetDialogFiltersRequest())
        folders = folders_w_filters.filters
        folders_file = open(str(os.path.join(CONFIG_FOLDER,f"folders_of_{self.phone_number}.txt")), "w", encoding="utf-8")
        # Print information about each folder
        for folder in folders[1:]:
            print(f"Folder ID: {folder.id}, Title: {folder.title}")
            folders_file.write(f"Folder ID: {folder.id}, Title: {folder.title} \n")
          
        print("List of folders printed successfully!")

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
    print("1. List Chats")
    print("2. List Folders")
    print("3. Broadcast Message")
    print("4. Exit")

    choice = input("Enter your choice: ")

    if choice == '1':
        await bot.list_chats()

    elif choice == '2':
        await bot.list_folders()
        
    elif choice == '3':

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
            channels = [int(line.strip()) for line in f]

        print(f'Broadcasting message to {len(channels)} channels...')

        await bot.broadcast_message(message, channels)
        
        return

    elif choice == '3':
        print("Exiting...")
        return
    else:
        print("Invalid choice. Exiting...")
        return

    await bot.client.disconnect()

# Start the event loop and run the main function
if __name__ == "__main__":
    asyncio.run(main())