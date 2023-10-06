import psycopg2

# Connect to the database
conn = psycopg2.connect(os.getenv('PROD_DB_CONN_URL'))

# Create a cursor
cur = conn.cursor()

cur.execute(
    "SELECT author, discord_message_id, content FROM legacy_chatlogs WHERE content ~* '[^.!?]*\?' AND content !~* '^[^ ]+\?$' AND content !~* '^https?://.*\?.*$' AND content != '?'")

# Fetch the rows
rows = cur.fetchall()

# Print the rows
for row in rows:
    print(row)

# Close the cursor and connection
cur.close()
conn.close()
