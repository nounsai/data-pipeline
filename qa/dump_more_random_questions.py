import os
import csv
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Read the existing random_questions.csv file
def read_csv(file_name):
    message_ids = []

    with open(file_name, 'r') as csvfile:
        csvreader = csv.reader(csvfile)
        headers = next(csvreader)  # Skip the header row

        for row in csvreader:
            message_id = row[0]
            message_ids.append(message_id)

    return message_ids

existing_ids = read_csv('random_questions.csv')

connection = psycopg2.connect(os.getenv('DB_CONN_URL'))

# Execute the SQL query to get 10,000 random rows
cursor = connection.cursor()
cursor.execute("""
    WITH used_questions AS (
        SELECT message_id
        FROM qa2_staging
        ORDER BY RANDOM()
        LIMIT 10000
    )
    SELECT discord_messages.id, discord_messages.content
    FROM discord_messages
    JOIN used_questions ON discord_messages.id = used_questions.message_id;
""")

# Fetch the rows from the query result
new_rows = cursor.fetchall()

# Close the database connection
cursor.close()
connection.close()

# Filter out duplicates based on message IDs
unique_rows = [row for row in new_rows if row[0] not in existing_ids]

# Write the first 2,000 unique rows to a new CSV file
with open('new_random_questions.csv', 'w', newline='') as csvfile:
    csvwriter = csv.writer(csvfile)
    csvwriter.writerow(['id', 'content'])  # Write the header row
    csvwriter.writerows(unique_rows[:2000])