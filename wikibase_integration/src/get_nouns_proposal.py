import requests
import json

url = "https://api.thegraph.com/subgraphs/name/nounsdao/nouns-subgraph"

def get_query(batch_size=100, skip_val=0):
    body = """
        {
        proposals(orderBy: startBlock, orderDirection: desc, first: %d, skip: %d) {
        id
        startBlock
        endBlock
        proposalThreshold
        quorumVotes
        description
        status
        executionETA
        createdTimestamp
        totalSupply
        title
        targets
        values
        signatures
        quorumCoefficient
        forVotes
        createdTransactionHash
        createdBlock
        calldatas
        proposer {
        id
        }
        votes {
        id
        support
        votes
        supportDetailed
        votesRaw
        blockNumber
        reason
        }
        
        abstainVotes
            againstVotes
            forVotes}}
        """ % (batch_size, skip_val)

    return body

status_code = 200
query_results = {'data': {"proposals": []}}
batch_query_results = {'data': {"proposals": [{}]}}
count = 0

with open('../data/nouns_proposals_new.json', 'w') as f:
    while status_code == 200 and len(batch_query_results['data']['proposals']) > 0:
        body = get_query(skip_val=count)
        print (body)
        response = requests.post(url=url, json={"query": body})
        if response.status_code == 200:
            batch_query_results = json.loads(response.content.decode("utf-8"))
            count += len(batch_query_results['data']['proposals'])
            query_results['data']['proposals'] += batch_query_results['data']['proposals']

    json.dump(query_results, f)