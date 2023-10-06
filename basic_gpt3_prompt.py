import openai
from time import time,sleep
import re
from dotenv import load_dotenv

load_dotenv()

def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()

openai.api_key = os.getenv('OPENAI_API_KEY')

def gpt3_completion(prompt, engine='text-davinci-003', temp=0.1, top_p=1.0, tokens=250, freq_pen=0.25):
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
                frequency_penalty=freq_pen)
                #presence_penalty=pres_pen,
                #stop=stop)
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

prompt = "Write me a rap song about the clouds as if Eminem wrote it"
print(gpt3_completion(prompt))