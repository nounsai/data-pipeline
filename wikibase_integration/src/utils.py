import re
from time import sleep

import pandas as pd
import openai
import spacy
from nltk import word_tokenize, pos_tag
from word2number import w2n

from dateutil.parser import parse
from datetime import datetime

nlp = spacy.load('en')

def clean(x):
    try:
        return x.replace("\n", " ").replace("'",'').replace('"','')
    except:
        return x
    
def clean_tweets(text):
    #text = text.lower()
    text = re.sub(r'@\w+','',text)
    text = re.sub(r'http\S+','',text)
    text = re.sub(r'://\S+','',text)
    text = re.sub(r'#\w+','',text)
    text = re.sub(r'##*','',text)
    #text = re.sub(r'\d+','',text)
    return text.strip()

def remove_html(text):
    #text = text.replace("\n"," ")
    pattern = re.compile('<.*?>') #all the HTML tags
    return pattern.sub(r'', text)

def remove_email(text):
    text = re.sub(r'[\w.<>]*\w+@\w+[\w.<>]*', " ", text)
    return text

def remove_emojis(data):
    emoj = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002500-\U00002BEF"  # chinese char
        u"\U00002702-\U000027B0"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U0001f926-\U0001f937"
        u"\U00010000-\U0010ffff"
        u"\u2640-\u2642" 
        u"\u2600-\u2B55"
        u"\u200d"
        u"\u23cf"
        u"\u23e9"
        u"\u231a"
        u"\ufe0f"  # dingbats
        u"\u3030"
                      "]+", re.UNICODE)
    return re.sub(emoj, '', data)

def shorten_text(tokenizer, MAX_LEN, text):
    tokens = tokenizer.encode(text)
    tokens = tokens[:MAX_LEN]
    return tokenizer.decode(tokens)

def recursive_summarize(text, max_len, engine="gpt-4", temp=0.1, top_p=1.0, tokens=75, freq_pen=0.25, pres_pen=0.0, stop=['<|endoftext|>']):
    # Ensure the input text is not already within the desired length
    if len(text.split()) <= max_len:
        return text

    # Create a chat with the model to generate a summary
    completion = openai.ChatCompletion.create(
        model=engine,
        temperature=temp,
        max_tokens=tokens,
        top_p=top_p,
        frequency_penalty=freq_pen,
        presence_penalty=pres_pen,
        stop=stop,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes text, focusing on key points and eliminating unnecessary details."},
            {"role": "user", "content": f"The text I want you to summarize is: {text}"}
        ]
    )

    summary = completion.choices[0].message['content']

    # If the summary is still too long, recursively break it down
    if len(summary) > max_len:
        mid = len(summary) // 2
        first_half = recursive_summarize(summary[:mid], max_len)
        sleep(1)
        second_half = recursive_summarize(summary[mid:], max_len)
        return first_half + " " + second_half

    return summary

def create_summary(text, MODEL_NAME="gpt-4"):
    text = clean_tweets(remove_html(remove_email(remove_emojis(text))))
    #summary = gpt3_summarizer(text)
    summary = recursive_summarize(text, engine=MODEL_NAME, max_len=200)
    
    if summary.endswith('.'):
        return summary.replace("'",'').replace('"','').replace("\n", " ")
    elif ". " in summary:
        return (".".join(summary.split(".")[:-1]) + ".").replace("'",'').replace('"','').replace("\n", " ")
    else:
        return text.replace("'",'').replace('"','').replace("\n", " ")

def get_title(text):
    return text.split("\n")[0].replace("#","").strip()

def check_float(string):
    try:
        x = float(string)
        return True
    except:
        return False
    
def calculate_budget(text, MODEL_NAME='gpt-4', debug=False):
    text = clean_tweets(remove_html(remove_email(remove_emojis(text))))

    message_log = [
        {"role": "system", "content": """You are a helpful assistant that returns only with the quantity of how much money is requested in a proposal. The answer should be in terms of USD if mentioned, otherwise ETH is acceptable. 
    \n e.g. in: 'Nouns Wet Wipes will become a permanent item in the market after this initial investment of USD 19,050.--PROPOSAL END--' -> out:$19050
    \n in: 'We would like to seek funding of 50 ETH to continue develop archives.wtf...--PROPOSAL END--' -> out: 50 ETH
    \n in: 'We would like to seek funding of 50 ETH (100 USD) for our proposal...--PROPOSAL END--' -> out: 50 ETH (100 USD)"""},
        {"role": "user", "content": "You are a helpful assistant that returns only with the quantity of how much money is requested in a proposal."}
    ]

    question = """How much money is requested in the proposal?  """
    prompt = f'{question}: "in: {text}"'
    message_log.append({"role": "user", "content": prompt})
    message_log.append({"role": "user", "content": "--PROPOSAL END-- How much money is requested in the proposal? -> out:"})
    
    response = openai.ChatCompletion.create(model=MODEL_NAME, messages=message_log, \
                                            temperature=0, max_tokens=45)
    
    if debug == True:
        print (response)
    
    out = response['choices'][0]['message']['content'].replace("\n"," ")
    
    return get_money(out)

def get_deadline(text, MODEL_NAME='gpt-4'):
    message_log = [
        {"role": "system", "content": """You are a helpful assistant that returns how many days or weeks or months the project in the proposal runs for.
    \n e.g. in: 'The project is expected to run for 3 months.--PROPOSAL END--' -> out:3 months
    \n in: 'The project completes in four weeks..--PROPOSAL END--' -> out:four weeks
    \n in: 'We need an extension for 4 months.--PROPOSAL END--' -> out:4 months
    \n in: 'Our plan for next three months is to develop and put the code to production.--PROPOSAL END--' -> out:three months"""},
        {"role": "user", "content": "You are a helpful assistant that returns how many days or weeks or months the project in the proposal runs for."}
    ]

    question1 = "How many days or weeks or months the project in the proposal runs for?"
    prompt = f'{question1}: "in: {text}"'
    message_log.append({"role": "user", "content": f"in: {text}"+"--PROPOSAL END-- How many days or weeks or months the project in the proposal runs for? -> out:"})
    
    
    response = openai.ChatCompletion.create(model=MODEL_NAME, messages=message_log, \
                                            temperature=0, max_tokens=45)
    
    out = response['choices'][0]['message']['content'].replace("\n"," ")
    
    return out

def get_team_details(text, MODEL_NAME='gpt-4', debug=False):
    #text = clean_tweets(remove_html(remove_email(remove_emojis(text))))
    
    message_log = [
        {"role": "system", "content": """You are a helpful assistant that returns the names of the members that are there in the team proposing a proposal.
    \n e.g. in: 'Context: Our team consists of Tim as dev, Ben as data scientist. --PROPOSAL END--' '\n Question: How many member, builders or contributors are there in the team?' '\n Reasoning: The members in the team are Tim and Ben. Hence, there are 2 people in the team.' -> '\n out: There are 2 people in the team.'
    \n in: 'Context: The members of the team are Tim, Frank, Pop and Roy. --PROPOSAL END--' '\n Question: How many members with names are there in the team?' '\n Reasoning: The team comprises of Tim, Frank, Pop and Roy. Thus there are 4 members in the team' -> '\n out: There are 4 members in the team'.
    \n in: 'Context: There are 10 members in the team. --PROPOSAL END--' '\n Question: How many members with names are there in the team?' '\n Reasoning: The names of the team members are not mentioned in the proposal. Therefore, I can not answer this.' -> '\n out: This question cannot be answered.'.
    """},
        {"role": "user", "content": "You are a helpful assistant that returns only with the quantity of how many members with names are there in the team proposing a proposal."}
    ]

    #question1 = "How many members, builders or contributors are there in the team?"
    #prompt = f'{question1}: "Context: {text}"'
    message_log.append({"role": "user", "content": f"Context: {text}"+"--PROPOSAL END-- \n Question: How many members with names are there in the team? -> Reasoning:"})
    #message_log.append({"role": "user", "content": "--PROPOSAL END-- How many members or contributors are there in the team? -> out:"})
    
    response = openai.ChatCompletion.create(model=MODEL_NAME, messages=message_log, \
                                            temperature=0.0, max_tokens=75)
    
    if debug == True:
        print (response)
    
    team_size = re.findall('\d+ ', response['choices'][0]['message']['content']) #+ re.findall('\d+\.', response['choices'][0]['message']['content'])
    
    team_size = [i.replace(".","").strip() for i in team_size]
    
    team_size = max([int(i) for i in team_size]) if len(team_size) > 0 else None
    
    if team_size is None:
        text2 = nlp(response['choices'][0]['message']['content'])

        for token in text2.ents:
            if token.label_ == 'CARDINAL':
                team_size = w2n.word_to_num(token.text)
    
    message_log = [
        {"role": "system", "content": """You are a helpful assistant that return only the name of the team or the builder that proposes a proposal.
         \n e.g. in: 'We are Archives.wtf consisting three people in the team.--PROPOSAL END--' -> out:Archives.wtf
         \n e.g. in: 'The proposer team is Korean J/24.--PROPOSAL END--' -> out:Korean J/24
         \n e.g. in: 'The proposer team is Korean J/24.--PROPOSAL END--' -> out:Korean J/24"""},
        {"role": "user", "content": "You are a helpful assistant that return only the name of the team or builder that proposes a proposal."}
    ]

    question2 = "What is the name of the team?"
    prompt = f'{question2}: "in: {text}"'
    message_log.append({"role": "user", "content": f"in: {text}"+"--PROPOSAL END-- What is the name of the team? -> out:"})

    response = openai.ChatCompletion.create(model=MODEL_NAME, messages=message_log, \
                                            temperature=0, max_tokens=15)
    
    team_desc = response['choices'][0]['message']['content']
    
    team_desc = team_desc.replace('"','').replace("'",'').replace(".","")
    team_name = team_desc.replace("The name of the team is","").strip()
    team_name = team_name.replace("The name of the proposer team is","").strip()
    
    sleep(1)
    
    message_log = [
        {"role": "system", "content": "You are a helpful assistant that answers questions from a given context."}
    ]
    
    message_log = [
        {"role": "system", "content": """You are a helpful assistant that return the name of id of the previous proposal to which the current proposal is a continuation.
         \n e.g. in: 'Previous proposals are prop 42, prop 23 and prop 121.--PROPOSAL END--' -> out:prop 42, prop 23, prop 121"""},
        {"role": "user", "content": "You are a helpful assistant that return the name of id of the previous proposal to which the current proposal is a continuation."}
    ]

    question3 = "What is the previous proposal of which the current proposal is part of?"
    prompt = f'{question3}: "in: {text}"'
    message_log.append({"role": "user", "content": f"in: {text}"+"--PROPOSAL END-- What is the previous proposal of which the current proposal is part of? -> out:"})
    
    response = openai.ChatCompletion.create(model=MODEL_NAME, messages=message_log, \
                                            temperature=0, max_tokens=35)
    
    proposal_cont = re.findall("prop* \d+", response['choices'][0]['message']['content'].lower())
    proposal_cont = [re.findall("\d+", i)[0] for i in proposal_cont] if len(proposal_cont) > 0 else None
    
    return team_size, team_name, proposal_cont, team_desc

def get_proposal_type(text, MODEL_NAME='gpt-4'):
    question = "What are the keywords in this proposal?"
    
    message_log = [
        {"role": "system", "content": """You are a helpful assistant that returns only the keywords mentioned in a proposal. 
        \n e.g. in: 'We are requesting an extension of 6 months of the existing contract.--PROPOSAL END--' -> out:extension """},
        {"role": "user", "content": "You are a helpful assistant that returns the keywords mentioned in a proposal."}
    ]

    message_log.append({"role": "user", "content": text+"--PROPOSAL END-- What are the keywords in this proposal? -> out:"})
    
    response = openai.ChatCompletion.create(model=MODEL_NAME, messages=message_log, \
                                            temperature=0, max_tokens=15)
    
    out = response['choices'][0]['message']['content'].replace("\n"," ")

    out = out.replace("Keywords in this proposal: -","").replace("Keywords in this proposal:","").replace("Keywords","").replace("Keyword","").strip().replace(":","").replace("-",",").strip()
    
    return out

def try_parse(date):
    try:
        return parse(date)
    except:
        return parse("01/01/1901")
    
def extract_dates(text, MODEL_NAME='gpt-4'):
    
    text = get_deadline(text, MODEL_NAME)
    
    doc = nlp(text)
    results = [(ent.text, ent.label_) for ent in doc.ents if ent.label_ in ['DATE']]
    
    results1 = [int(re.findall("\d+", i[0])[0]) for i in results if len(re.findall("\d+ month", i[0])) > 0]+\
                [int(re.findall("\d+", i[0])[0]) for i in results if len(re.findall("\d+-month", i[0])) > 0]
    results2 = [int(re.findall("\d+", i[0])[0]) for i in results if len(re.findall("\d+ day", i[0])) > 0]
    results3 = [try_parse(i[0]) for i in results if len(re.findall("Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec", i[0])) > 0]
    results4 = [int(re.findall("\d+", i[0])[0]) for i in results if len(re.findall("\d+ week", i[0])) > 0]+\
            [int(re.findall("\d+", i[0])[0]) for i in results if len(re.findall("\d+-week", i[0])) > 0]
                
    if len(results1) > 0:
        return str(max(results1)) + " months"
    elif len(results2) > 0:
        return str(results2[0]//30) + " months"
    elif len(results4) > 0:
        return str(results4[0]//4) + " months"
    elif len(results2) > 0 and max(results2) > datetime.today():
        return max(results2)
    elif "month" in text:
        text2 = nlp(text)
        for token in text2.ents:
            if token.label_ == 'DATE':
                t = token.text.split()[0]
                try:
                    return str(w2n.word_to_num(t)) + " months"
                except:
                    pass
    elif "week" in text:
        text2 = nlp(text)
        for token in text2.ents:
            if token.label_ == 'DATE':
                t = token.text.split()[0]
                try:
                    return str(w2n.word_to_num(t)//4) + " months"
                except:
                    pass
    return ""
    
def process_values(value, decimal_point=5):
    value = str(value)
    if len(value) >= 18:
        amount = value[:len(value)-18] + "." + value[len(value)-18:]
        amount = round(float(amount),decimal_point)
    else:
        amount = int(value)/(10**18)
    
    return "{} ETH".format(amount)

def get_usd(string):
    out = re.findall("\$\d+,\d+",string) + re.findall("\$\d+k",string) + re.findall("\$\d+K",string) + re.findall("\$\d+.\d+k",string) + re.findall("\$\d+.\d+K",string)
    if len(out) > 0:
        return out[0]
    else:
        out = re.findall("\d+,\d+ *USD",string) + re.findall("USD *\d+,\d+",string) + \
            re.findall("\d+.\d+ *USD",string) + re.findall("USD *\d+.\d+",string) + \
            re.findall("\d+.\d+k *USD",string) + re.findall("USD *\d+.\d+k",string) + \
            re.findall("\d+.\d+K *USD",string) + re.findall("USD *\d+.\d+K",string) + \
            re.findall("\d+k *USD",string) + re.findall("\d+K *USD",string) + \
            re.findall("USD *\d+k",string) + re.findall("USD *\d+K",string) +  \
            re.findall("\d+,\d+ *USDC",string) + re.findall("USDC *\d+,\d+",string) + \
            re.findall("\d+.\d+ *USDC",string) + re.findall("USDC *\d+.\d+",string) + \
            re.findall("\d+.\d+k *USDC",string) + re.findall("USDC *\d+.\d+k",string) + \
            re.findall("\d+.\d+K *USDC",string) + re.findall("USDC *\d+.\d+K",string) + \
            re.findall("\d+k *USDC",string) + re.findall("\d+K *USDC",string) + \
            re.findall("USDC *\d+k",string) + re.findall("USDC *\d+K",string)
        if len(out) > 0:
            return out[0]
        else:
            return ''

def get_eth(string):
    out = re.findall("\d+.\d+ *\w*ETH", string)
    if len(out) > 0:
        return " and ".join(out)
    else:
        out = re.findall("\d+ *\w*ETH", string)
        if len(out) > 0:
            return " and ".join(out)
        else:
            return ''
        
def get_money(string):
    usd = get_usd(string)
    eth = get_eth(string)
    
    if usd != '' and eth != '' and "or" not in string.split() and "||" not in string.split() and "(" not in string:
        return usd + " and " + eth
    elif usd != '':
        return usd
    elif eth != '':
        return eth
    else:
        return string

def post_process_deadline(x, pairs):
    if x.relation == 'Proposal Duration':
        if type(x.object) == str and 'month' in x.object:
            return re.findall("\d+",x.object)[0]
        elif type(x.object) == datetime:
            proposal_date = parse(pairs[(pairs['subject'] == x.subject) & \
                                        (pairs['relation'] == 'Proposal Submission Date')].reset_index(drop=True).object.iloc[0])
            
            return round((x.object-proposal_date).days/30)
    
    return x.object

def post_process_proposal_types(pairs):
    df_ = pairs[pairs['relation'] == 'Proposal Type'].reset_index(drop=True)
    df_['object'] = df_['object'].apply(lambda x: x.replace("Keywords in this proposal include","").replace("-","").replace('"','').replace("I don't know.","").strip().split(","))
    df_ = df_.explode('object')
    df_ = df_[df_['object'] != ""]
    df_['object'] = df_['object'].apply(lambda x: x.strip().capitalize())
    df_ = df_[df_.object.str.len() > 1].reset_index(drop=True)
    
    df2_ = pairs[pairs['relation'] != 'Proposal Type'].reset_index(drop=True)
            
    df2_['relation'] = df2_['relation'].apply(lambda x: x.title())
    
    df2_.loc[df2_.relation == 'Executioneta', "relation"] = "ExecutionETA"
    df2_.loc[df2_.relation == 'ExecutionETA', "object"] = df2_[df2_.relation == 'ExecutionETA'].object.apply(lambda x: \
                                                            datetime.utcfromtimestamp(int(x)).strftime('%Y-%m-%d'))

    
    df2_['object'] = df2_.apply(lambda x: post_process_deadline(x, df2_), axis=1)
    
    df2_.loc[df2_.relation == 'Proposal Duration', "relation"] = "Proposal Duration in Months"
    
    return pd.concat([df_, df2_], axis=0).sort_values(['subject']).reset_index(drop=True)

def convert_string_to_num(x):
    x = x.replace("USDC",'')
    x = x.replace("USD",'')
    x = x.replace("$",'')
    x = x.replace("StETH",'')
    x = x.replace("stETH",'')
    x = x.replace("ETH",'')
    x = x.replace(",",'')
    x = x.split("-")[-1]
    if '.' in x and ('k' in x or 'K' in x):
        #try:
        round_digit = '0' * (3-len(re.findall("\.\d+",x)[0].replace(".",'')))
        string = (re.findall("\.\d+k",x) + re.findall("\.\d+K",x))[0]
        string2 = str(int(re.findall("\.\d+",x)[0].replace(".",''))) + round_digit
        x = x.replace(string,string2)
        #except:
        #    pass
    x = x.replace("k",'000').replace("K",'000')
    
    try:
        return float(x.strip())
    except:
        return ""
    
def post_process_budgets(pairs):
    df1_ = pairs[pairs['relation'] != 'Proposal Budget'].reset_index(drop=True)
    df2_ = pairs[pairs['relation'] == 'Proposal Budget'].reset_index(drop=True)
    df3_ = pd.DataFrame()
    
    index = 0
    for i in range(df2_.shape[0]):
        if "and" not in df2_.object.iloc[i] and ('$' in df2_.object.iloc[i] or 'USD' in df2_.object.iloc[i]):
            df3_.loc[index, "subject"] = df2_.subject.iloc[i]
            df3_.loc[index, "relation"] = "Proposal Budget in USD"
            df3_.loc[index, "object"] = convert_string_to_num(df2_.object.iloc[i])
            index += 1
        
        elif "and" not in df2_.object.iloc[i] and "ETH" in df2_.object.iloc[i] and "stETH" not in df2_.object.iloc[i]:
            df3_.loc[index, "subject"] = df2_.subject.iloc[i]
            df3_.loc[index, "relation"] = "Proposal Budget in ETH"
            df3_.loc[index, "object"] = convert_string_to_num(df2_.object.iloc[i])
            index += 1
        
        elif "and" not in df2_.object.iloc[i] and "stETH" in df2_.object.iloc[i]:
            df3_.loc[index, "subject"] = df2_.subject.iloc[i]
            df3_.loc[index, "relation"] = "Proposal Budget in stETH"
            df3_.loc[index, "object"] = convert_string_to_num(df2_.object.iloc[i])
            index += 1
            
        elif "and" in df2_.object.iloc[i]:
            for val in df2_.object.iloc[i].split("and"):
                if '$' in val or 'USD' in val:
                    df3_.loc[index, "subject"] = df2_.subject.iloc[i]
                    df3_.loc[index, "relation"] = "Proposal Budget in USD"
                    df3_.loc[index, "object"] = convert_string_to_num(val)
                    index += 1
                elif 'ETH' in val and 'stETH' not in val:
                    df3_.loc[index, "subject"] = df2_.subject.iloc[i]
                    df3_.loc[index, "relation"] = "Proposal Budget in ETH"
                    df3_.loc[index, "object"] = convert_string_to_num(val)
                    index += 1
                elif 'stETH' in val:
                    df3_.loc[index, "subject"] = df2_.subject.iloc[i]
                    df3_.loc[index, "relation"] = "Proposal Budget in stETH"
                    df3_.loc[index, "object"] = convert_string_to_num(val)
                    index += 1
    
    if df3_.shape[0] > 0:
        df3_ = df3_[df3_.object != ""].reset_index(drop=True)
    
    return pd.concat([df1_, df3_], axis=0)

def post_process_budgets2(pairs):
    for prop in pairs.subject.unique():
        index = pairs.shape[0]
        if 'Proposal Budget in ETH' not in pairs[pairs.subject == prop].relation.unique() and \
                'Transfer Value' in pairs[pairs.subject == prop].relation.unique():
            if 'ETH' in pairs[(pairs.subject == prop) & (pairs.relation == 'Transfer Value')].object.iloc[0]:
                pairs.loc[index, "subject"] = prop
                pairs.loc[index, "relation"] = 'Proposal Budget in ETH'
                pairs.loc[index, "object"] = float(pairs[(pairs.subject == prop) & (pairs.relation == 'Transfer Value')].object.iloc[0].replace("ETH","").strip())
            elif 'USD' in pairs[(pairs.subject == prop) & (pairs.relation == 'Transfer Value')].object.iloc[0]:
                pairs.loc[index, "subject"] = prop
                pairs.loc[index, "relation"] = 'Proposal Budget in USD'
                pairs.loc[index, "object"] = float(pairs[(pairs.subject == prop) & (pairs.relation == 'Transfer Value')].object.iloc[0].replace("USD","").strip())
    
    df1_ = pairs[pairs['relation'] != 'Proposal Budget in ETH'].reset_index(drop=True)
    df11_ = df1_[df1_['relation'] != 'Proposal Budget in USD'].reset_index(drop=True)
    
    df12_ = df1_[df1_['relation'] == 'Proposal Budget in USD'].reset_index(drop=True)
    df2_ = pairs[pairs['relation'] == 'Proposal Budget in ETH'].reset_index(drop=True)
    
    df12_ = df12_.sort_values(['subject','object'], ascending=[True,False]).reset_index(drop=True).drop_duplicates(subset=['subject','relation'],keep='first').reset_index(drop=True)
    df2_ = df2_.sort_values(['subject','object'], ascending=[True,False]).reset_index(drop=True).drop_duplicates(subset=['subject','relation'], keep='first').reset_index(drop=True)
    
    return pd.concat([df11_, df12_, df2_], axis=0).sort_values(['subject']).reset_index(drop=True)

def post_process_pairs(pairs):
    pairs.loc[pairs.relation == 'Setproposalthresholdbps Value', 'object'] = pairs.loc[pairs.relation == \
                            'Setproposalthresholdbps Value', 'object'].apply(lambda x: float(x.replace("bps",'')))
    
    pairs.loc[pairs.relation == 'Transfer Value', 'object'] = pairs.loc[pairs.relation == \
                            'Transfer Value', 'object'].apply(lambda x: float(x.replace("ETH",'')))
    pairs.loc[pairs.relation == 'Transfer Value', 'relation'] = 'Transfer Value in ETH'
    
    pairs.loc[pairs.relation == 'Team Name',"object"] = pairs.loc[pairs.relation == 'Team Name',"object"].apply(lambda x: \
                                                                                            x.capitalize())
    
    return pairs

def post_process_team_size(pairs):
    for prop in pairs.subject.unique():
        index = pairs.shape[0]
        if 'Team Size' not in pairs[pairs.subject == prop].relation.unique():
            pairs.loc[index, "subject"] = prop
            pairs.loc[index, "relation"] = 'Team Size'
            pairs.loc[index, "object"] = 1
            
    return pairs.sort_values(['subject']).reset_index(drop=True)

def post_process_budgets3(pairs):
    pairs_out = []
    for proposal in pairs.subject.unique():
        df_ = pairs[pairs.subject == proposal].reset_index(drop=True)
        if 'Transfer Value in ETH' in df_.relation.unique() and "Proposal Budget in ETH" in df_.relation.unique():
            if float(df_[df_.relation == 'Transfer Value in ETH'].object.iloc[0]) > float(df_[df_.relation == 'Proposal Budget in ETH'].object.iloc[0]):
                df_.loc[df_.relation == 'Proposal Budget in ETH',"object"] = df_.loc[df_.relation == 'Transfer Value in ETH'].object.iloc[0]
        if 'Transfer Value in USD' in df_.relation.unique() and "Proposal Budget in USD" in df_.relation.unique():
            if float(df_[df_.relation == 'Transfer Value in USD'].object.iloc[0]) > float(df_[df_.relation == 'Proposal Budget in USD'].object.iloc[0]):
                df_.loc[df_.relation == 'Proposal Budget in USD',"object"] = df_.loc[df_.relation == 'Transfer Value in USD'].object.iloc[0]
        pairs_out.append(df_)
    
    pairs_out = pd.concat(pairs_out, axis=0).reset_index(drop=True)
    