import os
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

# create content cleaning pipeline
# TODO: we will abstract this away into its own module

# Make a connection to the database
conn = psycopg2.connect(os.getenv('LOCAL_DB_CONN_URL'))

# Create a cursor
cur = conn.cursor(cursor_factory=RealDictCursor)

# for now we will hardcode a single channel from the database for testing purposes
# 943943469821476944

channel_query = """
SELECT author, content, created_timestamp, discord_message_id 
FROM legacy_chatlogs
WHERE discord_channel_id = '943943469821476944'
ORDER BY created_timestamp
LIMIT 500
"""

cur.execute(channel_query)

df = pd.DataFrame(cur.fetchall())

print(df.columns)

# for idx, row in df.iterrows():
#     # format the row as <Index>. <timestamp> <author>: <content> 
#     print(f"{idx}. {row['created_timestamp']} {row['author']}: {row['content']}")
