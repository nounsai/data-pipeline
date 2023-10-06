import psycopg2
import csv
from dotenv import load_dotenv

# Replace DATABASE_URL with the actual connection string to your database
conn = psycopg2.connect(os.getenv("PROD_DB_CONN_URL"))

# Open a cursor to perform database operations
cur = conn.cursor()

# Execute the SELECT query
cur.execute("SELECT proposal_id::int, description FROM review ORDER BY proposal_id::int ASC")

# Fetch the rows from the cursor as a list of tuples
rows = cur.fetchall()

# Write the rows to a CSV file
with open('proposals.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['proposal_id', 'description'])
    writer.writerows(rows)

# Close the cursor and connection
cur.close()
conn.close()
