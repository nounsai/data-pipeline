import requests
import json
import psycopg2
import time
import datetime

from dotenv import load_dotenv
load_dotenv()

# Make a connection to the database
conn = psycopg2.connect(os.getenv("PROD_DB_CONN_URL"))

# Create a cursor
cur = conn.cursor()

# Set the initial offset
offset = 126145

# Set a flag to indicate when we are done
done = False

while not done:
    # Make an HTTP request to the API endpoint
    response = requests.get(
        f"https://api.addressform.io/nouns-atlas/discord-messages?offset={offset}")

    # Check if we received a successful response
    if response.status_code == 200:
        # Parse the response as JSON
        data = response.json()

        # print number of records in data
        print(f"Number of records in data: {len(data)}")

        # Check if there are any records left to parse
        if len(data) == 0:
            print("Data import complete! on offset ", offset)
            done = True
        else:
            # Iterate over the list of objects
            for record in data:
                # Extract the values from the record
                author = record["author"]
                content = record["content"]
                created_timestamp = datetime.datetime.fromtimestamp(
                    record["created_timestamp"]).strftime('%Y-%m-%d %H:%M:%S')
                discord_message_id = record["discord_message_id"]
                discord_channel_id = record["discord_channel_id"]
                discord_user_id = record["discord_user_id"]
                try:
                    # Check if the discord_message_id already exists in the table
                    cur.execute(
                        "SELECT * FROM legacy_chatlogs WHERE discord_message_id = %s", (discord_message_id,))
                    if not cur.fetchone():
                        # Insert the record into the table
                        print(
                            f"Inserting record {discord_message_id} into legacy_chatlogs...")
                        cur.execute("INSERT INTO legacy_chatlogs (author, content, created_timestamp, discord_message_id, discord_channel_id, discord_user_id) VALUES (%s, %s, %s, %s, %s, %s)", (
                            author, content, created_timestamp, discord_message_id, discord_channel_id, discord_user_id))
                        conn.commit()
                    else:
                        print(
                            f"Record already exists in legacy_chatlogs...{discord_message_id}")
                except (Exception, psycopg2.DatabaseError) as error:
                    print(
                        f"Error inserting record into legacy_chatlogs...{discord_message_id}")
                    print(error)

            offset += 100
            print(f"Offset is now {offset}")

            time.sleep(1)
    else:
        # There was an error making the request
        print(
            f"An error occurred with status code {response.status_code} on offset {offset}! Exiting...")
        done = True


# Close the cursor and connection
cur.close()
conn.close()
