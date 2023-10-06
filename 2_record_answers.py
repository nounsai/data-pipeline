import psycopg2
import re
from psycopg2.extras import RealDictCursor
import openai
from time import sleep
from dotenv import load_dotenv

load_dotenv()


def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()

openai.api_key = os.getenv('OPENAI_API_KEY')

def gpt3_completion(prompt, engine='text-davinci-003', temp=0.1, top_p=1.0, tokens=500, freq_pen=0.25, pres_pen=0.0, stop=['<<END>>'], log=False, log_dir=None, log_id=None):
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
            if str(oops).startswith("This model's maximum context length"):
                print("Content too long for log_id %s" % log_id)
                return False
            retry += 1
            if retry >= max_retry:
                print(oops)
                print("Exception caught in gpt3_completion()")
                return False
                #return "GPT3 error: %s" % oops
            print('Error communicating with OpenAI:', oops)
            print(oops)
            sleep(1)

# Make a connection to the database
conn = psycopg2.connect(os.getenv('LOCAL_DB_CONN_URL'))

# Create a cursor
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute("SELECT qa.*, legacy_chatlogs.content, legacy_chatlogs.discord_channel_id FROM qa JOIN legacy_chatlogs ON qa.discord_message_id = legacy_chatlogs.discord_message_id WHERE qa.answer IS NULL")

# Fetch the rows
rows = cur.fetchall()

chat_query = """WITH cte AS (
   SELECT created_timestamp, discord_channel_id, discord_message_id, content
   FROM legacy_chatlogs
   WHERE discord_channel_id = '%s' AND discord_message_id = '%s'
)
SELECT t.content
FROM legacy_chatlogs t
JOIN cte
ON t.discord_channel_id = cte.discord_channel_id
AND t.created_timestamp > cte.created_timestamp
ORDER BY t.created_timestamp ASC
LIMIT 8;"""

for row in rows:
    #print(row)
    # retrieve the next ~50 messages that occurred after the question
    try:
        # print(row)
        # exit()
        cur.execute(chat_query % (row['discord_channel_id'], row['discord_message_id']))
        result = cur.fetchall()
        result_str = ''
        for content in result:
            result_str += content['content'] + '\n'
        if len(result_str) > 0:
            # prepare the prompt        
            qa_prompt = open_file('prompts/question_with_potential_answers.txt').replace('<<CONVERSATION>>', result_str).replace('<<QUESTION>>', row['content'])
            qa_prompt = qa_prompt.encode(encoding='ASCII', errors='ignore').decode()
            answer = gpt3_completion(qa_prompt, log=True, log_dir='answers', log_id=row['id'])
            if answer is not False:
                cur.execute("UPDATE qa SET answer = %s WHERE id = %s", (answer, row['id']))
                conn.commit()
                print('Answered question %s' % row['id'])
    except (Exception, psycopg2.DatabaseError) as error:
        print("Error: %s" % error)


cur.close()
conn.close()
        
