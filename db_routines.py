import requests
import os
import sys
import subprocess
import argparse
import psycopg2
import re
import time
from dotenv import load_dotenv

load_dotenv()

import re

def sanitize_string(input_string):
    # ansi_escape_sequence = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]')
    # emoji_pattern = re.compile("["
    #     u"\U0001F600-\U0001F64F"  # emoticons
    #     u"\U0001F300-\U0001F5FF"  # symbols & pictographs
    #     u"\U0001F680-\U0001F6FF"  # transport & map symbols
    #     u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
    #                        "]+", flags=re.UNICODE)
    # input_string = ansi_escape_sequence.sub(r'', input_string)
    # return emoji_pattern.sub(r'', input_string)
    return re.sub(r'[^\w\s]', '', input_string)


def clean_db(target, table_name):
    conn_str = os.getenv(f"{target}_DB_CONN")
    conn = psycopg2.connect(conn_str)
    print(f"Cleaning {table_name} in {target} environment")
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {table_name} WHERE content IS NULL OR content = ''")
    conn.commit()
    cursor.close()
    conn.close()

def update_discord_usernames(target):
    conn_str = os.getenv(f"{target}_DB_CONN")
    conn = psycopg2.connect(conn_str)
    cursor = conn.cursor()

    # Get a set of all discord_user_ids that are already in the user_profiles table
    cursor.execute("SELECT discord_user_id FROM user_profiles")
    discord_user_ids_in_db = set(row[0] for row in cursor.fetchall())

    # Create an in-memory cache of discord_user_ids
    discord_user_ids_cache = discord_user_ids_in_db.copy()

    for table_name in ["legacy_chatlogs", "chatlogs"]:
        query = (f"SELECT content, "
         f"{'discord_message_id' if table_name == 'legacy_chatlogs' else 'id'} "
         f"FROM {table_name}")

        #cursor.execute(f"SELECT content,discord_message_id FROM {table_name}")
        cursor.execute(query)
        contents = cursor.fetchall()
        pattern = re.compile(r"<@(\d+)>")

        for content in contents:
            match = re.search(pattern, content[0])
            if match:
                #print(f"message_id[{content[1]}] content[{content[0]}] discord_user_id[{discord_user_id}]")
                discord_user_id = match.group(1)
                if discord_user_id is None or discord_user_id in discord_user_ids_cache:
                    print(f"Skipping {discord_user_id} -- already in cache")
                    continue
                discord_username = convert_to_tag(discord_user_id)
                discord_user_ids_cache.add(discord_user_id)
                if discord_username is not None:
                    # Check if discord_user_id exists in the user_profiles table
                    cursor.execute(f"SELECT 1 FROM user_profiles WHERE discord_user_id = '{discord_user_id}'")
                    exists = cursor.fetchone()
                    
                    if not exists:
                        # Insert the discord_user_id and discord_username into the user_profiles table
                        cursor.execute(f"INSERT INTO user_profiles (discord_user_id, discord_username) VALUES ('{discord_user_id}', '{discord_username}')")
                        conn.commit()
                        #discord_user_ids_cache.add(discord_user_id)

                # Wait for 2 seconds before making another API call
                time.sleep(2)
    
    cursor.close()
    conn.close()



def convert_to_tag(user_id):
    token = os.getenv("DISCORD_TOKEN")
    headers = {
        'Authorization': f'Bot {token}',
        'User-Agent': 'DiscordBot (https://example.com, v0.1)',
    }
    response = requests.get(f'https://discord.com/api/v6/users/{user_id}', headers=headers)
    user_data = response.json()
    try:
        username = user_data['username']
        sanitized_username = sanitize_string(username)
        discriminator = user_data['discriminator']
        tag = f'{sanitized_username}#{discriminator}'
        print(f"tag: {tag} for user id {user_id}")
        return tag
    except KeyError as e:
        print(f"Error: {e} for user id {user_id}")
        return None

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("routine_name", type=str, help="Routine to run", choices=["clean_db", "update_discord_usernames"])
    parser.add_argument("table_name", type=str, help="Name of the table to operate on")
    parser.add_argument("--target", type=str, default="LOCAL", choices=["LOCAL", "PROD", "STAGING"], help="Target environment")
    args = parser.parse_args()

    if args.routine_name == 'clean_db':
        clean_db(args.target.upper(), args.table_name)
    elif args.routine_name == 'update_discord_usernames':
        update_discord_usernames(args.target.upper())
    else:
        print("Invalid routine name")

# user_id = "270147458737242112"
# print(convert_to_tag(user_id, token))


