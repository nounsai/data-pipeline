import psycopg2
from prettytable import PrettyTable
from dotenv import load_dotenv
load_dotenv()

# Connect to the database
conn = psycopg2.connect(os.getenv('LOCAL_DB_CONN_URL'))

# Create a cursor
cur = conn.cursor()

# Execute the query
cur.execute("SELECT qa.id, legacy_chatlogs.content, qa.answer FROM qa JOIN legacy_chatlogs ON qa.discord_message_id = legacy_chatlogs.discord_message_id WHERE qa.answer is NOT NULL")

# Fetch the rows
rows = cur.fetchall()

# Create a table to hold the results
table = PrettyTable()
table.field_names = ['ID', 'Content', 'Answer']
table._max_width = {"ID": 5, "Content" : 25, "Answer" : 25}

# Add the rows to the table
for row in rows:
    table.add_row(row)

# Print the table
print(table)

# Close the cursor and connection
cur.close()
conn.close()
