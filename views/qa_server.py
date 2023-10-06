from flask import Flask, render_template
import psycopg2

app = Flask(__name__)

# Connect to the database
conn = psycopg2.connect('postgresql://postgres:postgrespassword@127.0.0.1:5432')

# Create a cursor
cur = conn.cursor()

# Execute the query
cur.execute("SELECT qa.id, legacy_chatlogs.content, qa.answer FROM qa JOIN legacy_chatlogs ON qa.discord_message_id = legacy_chatlogs.discord_message_id WHERE qa.answer is NOT NULL")

# Fetch the rows
rows = cur.fetchall()

@app.route('/')
def display_table():
    return render_template('qa.html', rows=rows)

if __name__ == '__main__':
    app.run(debug=True)
