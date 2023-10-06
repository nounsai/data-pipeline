import psycopg2
import openai
import re
from time import time,sleep
from dotenv import load_dotenv

load_dotenv()

def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()

openai.api_key = os.getenv('OPENAI_API_KEY')

def gpt3_completion(prompt, engine='text-davinci-003', temp=0.1, top_p=1.0, tokens=2000, freq_pen=0.25, pres_pen=0.0, stop=['<<END>>']):
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
            filename = '%s_gpt3.txt' % time()
            with open('gpt3_logs/%s' % filename, 'w') as outfile:
                outfile.write('PROMPT:\n\n' + prompt + '\n\n==========\n\n' + text)
            return text
        except Exception as oops:
            retry += 1
            if retry >= max_retry:
                return "GPT3 error: %s" % oops
            print('Error communicating with OpenAI:', oops)
            sleep(1)

# Make a connection to the database
conn = psycopg2.connect(os.getenv('PROD_DB_CONN_URL'))

# Create a cursor
cur = conn.cursor()

# Execute a SELECT statement to select the `id`,`summary` columns where `display_summary` is NULL
cur.execute("SELECT id, summary FROM audio WHERE display_summary IS NULL")

# Fetch all the results of the SELECT statement
results = cur.fetchall()

# Iterate through the results
for row in results:
    audio_id = row[0]
    summary = row[1]
    # Run gpt-3 completion code and store the response in a variable
    # gpt3_response = stub_for_gpt3_completion_code(summary)
    prompt = open_file('prompts/summary_of_summary.txt').replace('<<SUMMARY>>', summary)
    prompt = prompt.encode(encoding='ASCII',errors='ignore').decode()
    summary_of_summary = gpt3_completion(prompt)
    # Update the audio table with the response from gpt-3 for the corresponding audio.id
    cur.execute("UPDATE audio SET display_summary = %s WHERE id = %s", (summary_of_summary, audio_id))
    #Commit the update statement
    conn.commit()

# Close the cursor and connection
cur.close()
conn.close()