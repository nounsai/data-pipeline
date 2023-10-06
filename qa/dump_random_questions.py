import os
import psycopg2
import csv
from dotenv import load_dotenv
load_dotenv()

connection = psycopg2.connect(os.getenv('DB_CONN_URL'))


# Replace the connection parameters with your own

cursor = connection.cursor()

query = '''
SELECT dm.id, dm.content
FROM discord_messages AS dm
JOIN qa2_staging AS qa2 ON dm.id = qa2.message_id
ORDER BY RANDOM()
LIMIT 2000;
'''

cursor.execute(query)

# Fetch all the rows as a list of tuples
rows = cursor.fetchall()

# Write the rows to a CSV file
with open('random_questions.csv', 'w', newline='', encoding='utf-8') as csvfile:
    csv_writer = csv.writer(csvfile)
    csv_writer.writerow(['id', 'content', 'label'])
    for row in rows:
        csv_writer.writerow(row + (None,))

cursor.close()
connection.close()
