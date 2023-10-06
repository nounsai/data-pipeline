import psycopg2
from dotenv import load_dotenv
load_dotenv()

# Connect to the database
conn = psycopg2.connect(os.getenv('LOCAL_DB_CONN_URL'))


# Create a cursor
cur = conn.cursor()

# Select rows from the `legacy_chatlogs` table where the `content` column looks like a question and does not match certain patterns
cur.execute("SELECT * FROM legacy_chatlogs WHERE content ~* '[^.!?]*\?' AND content !~* '^[^ ]+\?$' AND content !~* '^https?://.*\?.*$' AND content != '?'")


# Fetch the rows
rows = cur.fetchall()

# Print the rows
for row in rows:
    print(row)

# Close the cursor and connection
cur.close()
conn.close()
