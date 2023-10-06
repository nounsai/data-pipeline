import os
from time import time,sleep
import pandas as pd
import json
from tqdm import tqdm
import openai
from dotenv import load_dotenv
import re
import tiktoken

from datetime import datetime

from utils import shorten_text, create_summary, get_proposal_type, calculate_budget, \
        extract_dates, get_team_details, process_values, clean, post_process_budgets, post_process_budgets2, \
        post_process_budgets3, post_process_deadline, post_process_pairs, post_process_proposal_types, post_process_team_size

load_dotenv()

MODEL_NAME = "gpt-4" #"gpt-3.5-turbo-16k"
MAX_LEN = 3500

def create_KG(proposal, gen_view1 = True, gen_view2 = True):
    max_retry = 5
    retry = 0
    while True:
        try:
            proposal_id = "Proposal {}".format(proposal["id"])
            subjects = []
            relations = []
            objects = []
            
            if gen_view1 == True:
                subjects.append(proposal_id)
                relations.append("ID")
                objects.append(proposal["id"])
                
                if 'proposer' in proposal:
                    subjects.append(proposal_id)
                    relations.append("Proposer")
                    objects.append(proposal['proposer']['id'])
                
                if 'createdTimestamp' in proposal:
                    subjects.append(proposal_id)
                    relations.append("Proposal Submission Date")
                    objects.append(datetime.utcfromtimestamp(int(proposal['createdTimestamp'])).strftime('%Y-%m-%d'))
                
                if 'quorumVotes' in proposal:
                    subjects.append(proposal_id)
                    relations.append("quorumVotes")
                    objects.append(int(proposal['quorumVotes']))
                
                if 'status' in proposal:
                    subjects.append(proposal_id)
                    relations.append("Status")
                    objects.append(proposal['status'])
                
                if 'executionETA' in proposal:
                    if proposal["executionETA"]:
                        subjects.append(proposal_id)
                        relations.append("executionETA")
                        objects.append(proposal['executionETA'])
                
                if 'title' in proposal:
                    title = proposal['title'] #get_title(proposal['description'])
                    subjects.append(proposal_id)
                    relations.append("Label")
                    objects.append(title)
                
                if 'description' in proposal or 'description_short' in proposal:
                    try:
                        summary = create_summary(proposal['description'], MODEL_NAME)
                    except:
                        try:
                            summary = create_summary(proposal['description_short'], MODEL_NAME)
                        except:
                            summary = ""
                    
                    if summary != "":
                        subjects.append(proposal_id)
                        relations.append("Summary")
                        objects.append(summary)

                    try:
                        budget = calculate_budget(proposal["description"], MODEL_NAME)
                    except:
                        try:
                            budget = calculate_budget(proposal["description_short"], MODEL_NAME)
                        except:
                            budget = ""

                    if budget != "":
                        subjects.append(proposal_id)
                        relations.append("Proposal Budget")
                        objects.append(budget)

                    try:
                        props = get_proposal_type(proposal["description"], MODEL_NAME)
                        objects.append()
                    except:
                        try:
                            props = get_proposal_type(proposal["description_short"], MODEL_NAME)
                        except:
                            props = ""
                    
                    if props != "":
                        subjects.append(proposal_id)
                        relations.append("Proposal Type")
                        objects.append(props)

                    try:
                        date = extract_dates(proposal["description"], MODEL_NAME)
                    except:
                        try:
                            date = extract_dates(proposal["description_short"], MODEL_NAME)
                        except:
                            date = ""

                    if date != "":
                        subjects.append(proposal_id)
                        relations.append("Proposal Duration")
                        objects.append(date)

                    try:
                        team_size, team_name, proposal_cont, _ = get_team_details(proposal["description"], MODEL_NAME)
                    except:
                        try:
                            team_size, team_name, proposal_cont, _ = get_team_details(proposal["description_short"], MODEL_NAME)
                        except:
                            team_name = ""
                            proposal_cont = None
                            team_size = None

                    if team_name != "":
                        subjects.append(proposal_id)
                        relations.append("Team Name")
                        objects.append(team_name)

                    if proposal_cont:
                        for p in proposal_cont:
                            subjects.append(proposal_id)
                            relations.append("Previous Proposal")
                            objects.append("Proposal {}".format(str(p)))

                    if team_size:
                        subjects.append(proposal_id)
                        relations.append("Team Size")
                        objects.append(team_size)
                
                if 'targets' in proposal:
                    for i in range(len(proposal['targets'])):
                        if proposal['values'][i] != '0':
                            try:
                                trans_type = proposal['signatures'][i].split("(")[0]
                            except:
                                trans_type = "Transfer"

                            if trans_type == "":
                                trans_type = "Transfer"

                            if trans_type == "Transfer":
                                subjects.append(proposal_id)
                                relations.append("{} To".format(trans_type))
                                objects.append(proposal['targets'][i])

                                subjects.append(proposal_id) #proposal['targets'][i]
                                relations.append("{} Value".format(trans_type))
                                objects.append(process_values(proposal['values'][i]))

                        elif proposal['signatures'][i].startswith("sendOrRegisterDebt") and "and" not in budget:
                            subjects.append(proposal_id)
                            relations.append("sendOrRegisterDebt To Nouns")
                            objects.append(proposal['targets'][i])

                            string = proposal['calldatas'][i][-16:]
                            val = int(str(int(string, 16))[:-6])

                            subjects.append(proposal_id) #proposal['targets'][i]
                            relations.append("sendOrRegisterDebt Value To Nouns")
                            objects.append(val)

                        elif proposal['signatures'][i].startswith("sendOrRegisterDebt") and "and" in budget:
                            subjects.append(proposal_id)
                            relations.append("sendOrRegisterDebt To")
                            objects.append(proposal['targets'][i])

                            string = proposal['calldatas'][i][-16:]
                            val = int(str(int(string, 16))[:-6])

                            subjects.append(proposal_id) #proposal['targets'][i]
                            relations.append("sendOrRegisterDebt Value")
                            objects.append(val)

                        elif proposal['signatures'][i].startswith("createEdition"):
                            subjects.append(proposal_id)
                            relations.append("createEdition To")
                            objects.append(proposal['targets'][i])

                        elif "bps" in budget:
                            bps_val = re.findall("\d+bps", budget)[0]

                            subjects.append(proposal_id)
                            relations.append("setProposalThresholdBPS To")
                            objects.append(proposal['targets'][i])

                            subjects.append(proposal_id) #proposal['targets'][i]
                            relations.append("setProposalThresholdBPS Value")
                            objects.append(bps_val)
            
            if gen_view2 == True:
                subjects2 = []
                relations2 = []
                objects2 = []
                weights2 = []
                reasons2 = []
                    
                if 'votes' in proposal:
                    votes = proposal['votes']

                    supporter_count = 0
                    opposer_count = 0

                    for vote in votes:
                        subjects2.append(proposal_id)
                        if vote['support'] == True:
                            relations2.append("Supported By")
                            #supporter_count += int(vote.get("votes",1))
                            weights2.append(max(int(vote.get("votes",1)),1))
                            reasons2.append(vote.get("reason", "No reason provided"))
                        elif vote['supportDetailed'] == 0:
                            relations2.append("Opposed By")
                            #opposer_count += int(vote.get("votes",1))
                            weights2.append(max(int(vote.get("votes",1)),1))
                            reasons2.append(vote.get("reason", "No reason provided"))
                        elif vote['supportDetailed'] == 2:
                            relations2.append("Abstained By")
                            #opposer_count += int(vote.get("votes",1))
                            weights2.append(max(int(vote.get("votes",1)),1))
                            reasons2.append(vote.get("reason", "No reason provided"))

                        objects2.append(vote['id'])   
            
            if gen_view1 == True:
                if 'forVotes' in proposal:
                    subjects.append(proposal_id)
                    relations.append("Supporter Count")
                    objects.append(int(proposal["forVotes"]))
                
                if 'abstainVotes' in proposal:
                    subjects.append(proposal_id)
                    relations.append("Abstain Count")
                    objects.append(int(proposal["abstainVotes"]))
                
                if 'againstVotes' in proposal:
                    subjects.append(proposal_id)
                    relations.append("Opposer Count")
                    objects.append(int(proposal["againstVotes"]))
            
            pairs = pd.DataFrame()
            pairs2 = pd.DataFrame()
            
            if gen_view1 == True:
                
                pairs['subject'] = subjects
                pairs['relation'] = relations
                pairs['object'] = objects
            
            if gen_view2 == True:
                pairs2['subject'] = subjects2
                pairs2['relation'] = relations2
                pairs2['object'] = objects2
                pairs2['weight'] = weights2
                pairs2['reason'] = reasons2

            return pairs, pairs2
            
        except Exception as oops:
            retry += 1
            if retry >= max_retry:
                return pd.DataFrame(), pd.DataFrame()
            
            print('Error communicating with OpenAI:', oops)
            sleep(1)
            
            return pd.DataFrame(), pd.DataFrame()

if __name__ == '__main__':
    openai.api_key = os.getenv("OPENAI_API_KEY")
    tokenizer = tiktoken.get_encoding("cl100k_base")

    if 'nouns_proposals_new.json' in os.listdir('../data/') and 'nouns_proposals.json' in os.listdir('../data/'):
        data_old = json.load(open('../data/nouns_proposals.json','r'))
        data = json.load(open('../data/nouns_proposals_new.json','r'))

        formatted_data = {}
        formatted_old_data = {}

        for i in range(len(data_old['data']['proposals'])):
            formatted_old_data[data_old['data']['proposals'][i]['id']] = data_old['data']['proposals'][i]

        for i in range(len(data['data']['proposals'])):
            formatted_data[data['data']['proposals'][i]['id']] = data['data']['proposals'][i]

        new_data = {}

        for key in formatted_data:
            if key in formatted_old_data:
                if formatted_data[key] == formatted_old_data[key]:
                    pass
                else:
                    new_data[key] = {}
                    new_data[key]['id'] = key
                    for key2 in formatted_data[key]:
                        if formatted_data[key][key2] != formatted_old_data[key][key2]:
                            new_data[key][key2] = formatted_data[key][key2]
            else:
                new_data[key] = formatted_data[key]

    elif 'nouns_proposals.json' in os.listdir('../data/'):
        data = json.load(open('../data/nouns_proposals.json','r'))
        new_data = {}
        for i in range(len(data['data']['proposals'])):
            new_data[data['data']['proposals'][i]['id']] = data['data']['proposals'][i]
            
    elif 'nouns_proposals_new.json' in os.listdir('../data/'):
        data = json.load(open('../data/nouns_proposals_new.json','r'))
        new_data = {}
        for i in range(len(data['data']['proposals'])):
            new_data[data['data']['proposals'][i]['id']] = data['data']['proposals'][i]

    else:
        raise ValueError("Either nouns_proposals.json or nouns_proposals_new.json \
            file should be present in the root folder")

    for key in new_data:
        if 'description' in new_data[key]:
            new_data[key]['description_short'] = shorten_text(tokenizer, MAX_LEN, new_data[key]['description'])

    pairs = []
    pairs2 = []

    id_wise_pairs = {}

    for key in tqdm(new_data):
        print ("Proposal " + new_data[key]['id'])
        p1, p2 = create_KG(new_data[key], gen_view1=True, gen_view2=True)
        pairs.append(p1)
        pairs2.append(p2)
        id_wise_pairs[new_data[key]["id"]] = p1.copy()
        
        sleep(3)
        
    pairs = pd.concat(pairs, axis=0)
    pairs2 = pd.concat(pairs2, axis=0)

    pairs2['object'] = pairs2['object'].apply(lambda x: x.split("-")[0])

    if pairs.shape[0] > 0:
        pairs = post_process_proposal_types(pairs)
        pairs = post_process_budgets(pairs)
        pairs = post_process_budgets2(pairs)
        pairs = post_process_pairs(pairs)
        pairs = post_process_team_size(pairs)
        pairs4 = post_process_budgets3(pairs)
        
        pairs.object = pairs.object.apply(clean)
    
    pairs = pairs.drop_duplicates().reset_index(drop=True)
    pairs2 = pairs2.drop_duplicates().reset_index(drop=True)

    pairs2.reason = pairs2.reason.fillna("Reason not provided")
    pairs2.reason = pairs2.reason.apply(clean)

    if 'KG_view1.csv' in os.listdir('../data/') and 'KG_view2.csv' in os.listdir('../data/'):
        pairs = pd.concat([pd.read_csv("../data/KG_view1.csv"), pairs], axis=0)
        pairs2 = pd.concat([pd.read_csv("../data/KG_view2.csv"), pairs2], axis=0)
        
        pairs3 = pairs[pairs.relation.isin(['Previous Proposal', 'Transfer To', 'Proposal Type', \
                'Transfer Value in ETH', 'Sendorregisterdebt Value To Nouns'])]
        pairs4 = pairs[pairs.relation.isin(['Previous Proposal', 'Transfer To', 'Proposal Type', \
                'Transfer Value in ETH', 'Sendorregisterdebt Value To Nouns']) == False]

        pairs3 = pairs3.drop_duplicates(subset=['subject','relation','object'], keep='last').reset_index(drop=True)
        pairs4 = pairs4.drop_duplicates(subset=['subject','relation'], keep='last').reset_index(drop=True)

        pairs = pd.concat([pairs3, pairs4], axis=0).sort_values(['subject']).reset_index(drop=True)

        pairs2 = pairs2.drop_duplicates(subset=['subject','object'], keep='last').reset_index(drop=True)

    pairs.to_csv("../data/KG_view1.csv", index=False)
    pairs2.to_csv("../data/KG_view2.csv", index=False)

    if 'nouns_proposals_new.json' in os.listdir('../data/') and 'nouns_proposals.json' in os.listdir('../data/'):
        os.remove("../data/nouns_proposals.json")
        os.rename("../data/nouns_proposals_new.json", "../data/nouns_proposals.json")
    elif 'nouns_proposals_new.json' in os.listdir('../data/'):
        os.rename("../data/nouns_proposals_new.json", "../data/nouns_proposals.json")