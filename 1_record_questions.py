import psycopg2
import re
from psycopg2.extras import RealDictCursor
import openai
from time import time,sleep
from dotenv import load_dotenv

load_dotenv()

def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()


openai.api_key = os.getenv('OPENAI_API_KEY')

def gpt3_completion(prompt, engine='text-davinci-003', temp=0.1, top_p=1.0, tokens=250, freq_pen=0.25, pres_pen=0.0, stop=['<<END>>'], log=False, log_dir=None, log_id=None):
    max_retry = 5
    retry = 0
    while True:
        try:
            response = openai.Completion.create(
                engine=engine,
                prompt=prompt,
                temperature=temp,
                max_tokens=tokens,
                top_p=top_p,
                frequency_penalty=freq_pen,
                presence_penalty=pres_pen,
                stop=stop)
            text = response['choices'][0]['text'].strip()
            text = re.sub('\s+', ' ', text)
            if log:
                filename = '%s_gpt3.txt' % (log_id)
                with open('gpt3_logs/%s/%s' % (log_dir, filename), 'w') as outfile:
                    outfile.write('PROMPT:\n\n' + prompt + '\n\n==========\n\n' + text)
            return text
        except Exception as oops:
            retry += 1
            if retry >= max_retry:
                return "GPT3 error: %s" % oops
            print('Error communicating with OpenAI:', oops)
            sleep(1)

# Make a connection to the database
conn = psycopg2.connect(os.getenv('LOCAL_DB_CONN_URL'))

# Create a cursor
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute("SELECT * FROM legacy_chatlogs WHERE content ILIKE '%?%'")

# Fetch the rows
rows = cur.fetchall()

# Print the rows
for row in rows:
    #print(row)
    is_question_prompt = open_file('prompts/is_nouns_question.txt').replace('<<QUESTION>>', row['content'])
    is_question_prompt = is_question_prompt.encode(encoding='ASCII',errors='ignore').decode()
    is_question = gpt3_completion(is_question_prompt, log=False, log_dir='is_question', log_id=row['discord_message_id'])
    if re.match(r'(?i)^Pass', is_question):
        print('Question: %s' % row['content'])
        try:
            # Check if the discord_message_id already exists in the table
            cur.execute("SELECT * FROM qa WHERE discord_message_id = %s", (row['discord_message_id'],))
            if not cur.fetchone():
                # Insert the record into the table
                print(f"Inserting record {row['discord_message_id']} into legacy_chatlogs...")
                cur.execute("INSERT INTO qa (discord_message_id) VALUES (%s)", (row['discord_message_id'],))
                conn.commit()
            else:
                print(f"Question already exists in qa...{row['discord_message_id']}")
        except (Exception, psycopg2.DatabaseError) as error:
            print(f"Error inserting record into qa...{row['discord_message_id']}")
            print(error)


# Close the cursor and connection
cur.close()
conn.close()

