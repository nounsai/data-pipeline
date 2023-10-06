
import openai
import os
from time import time,sleep
import re
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.environ.get('OPENAI_API_KEY')

def gpt3_completion(prompt, engine='text-davinci-003', temp=0.0, top_p=1.0, tokens=250, freq_pen=0.0, pres_pen=0.0, stop=['<<END>>']):
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
            if not os.path.exists('gpt3_logs'):
                os.mkdir('gpt3_logs')
            log_path = os.path.join(os.getcwd(), 'gpt3_logs', filename)
            with open(log_path, 'w') as outfile:
                outfile.write('PROMPT:\n\n' + prompt + '\n\n==========\n\nRESPONSE:\n\n' + text)
            return text
        except Exception as oops:
            retry += 1
            if retry >= max_retry:
                raise RuntimeError("GPT3 error: %s" % oops)
                #return "GPT3 error: %s" % oops
            print('Error communicating with OpenAI:', oops)
            sleep(2)