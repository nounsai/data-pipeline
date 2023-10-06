import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np
import pinecone
import openai
from tqdm.auto import tqdm  # this is our progress bar
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

openai.organization = os.getenv('OPENAI_ORG')
openai.api_key = os.getenv('OPENAI_API_KEY')

#print(openai.Engine.list())  # check we have authenticated

conn = psycopg2.connect(os.getenv('LOCAL_DB_CONN_URL'))

cur = conn.cursor(cursor_factory=RealDictCursor)

query = """
SELECT qa.*, legacy_chatlogs.content, legacy_chatlogs.discord_channel_id 
FROM qa 
JOIN legacy_chatlogs 
ON qa.discord_message_id = legacy_chatlogs.discord_message_id 
WHERE qa.answer IS NOT NULL
"""
cur.execute(query)

data = cur.fetchall()

cur.close()
conn.close()

MODEL="text-embedding-ada-002"
res = openai.Embedding.create(
    input=[row['content'] for row in data[:10]], engine=MODEL
)

embeds = [record['embedding'] for record in res['data']]

pinecone.init(os.getenv('PINECONE_API_KEY'), environment="us-west1-gcp")
index_name = 'openai-pinecone-aipod'

# if the index does not exist, we create it
if index_name not in pinecone.list_indexes():
    pinecone.create_index(index_name, dimension=len(embeds[0]))

# # connect to index
index = pinecone.Index(index_name)

batch_size = 32  # process everything in batches of 32
for i in tqdm(range(0, len(data), batch_size)):
    # set end position of batch
    i_end = min(i+batch_size, len(data))
    # get batch of lines and IDs
    lines_batch = [row['content'] for row in data[i: i+batch_size]]
    ids_batch = [str(n) for n in range(i, i_end)]
    # create embeddings
    res = openai.Embedding.create(input=lines_batch, engine=MODEL)
    embeds = [record['embedding'] for record in res['data']]
    # prep metadata and upsert batch
    meta = [{'text': line, 'discord_message_id': row['discord_message_id']} for line,row in zip(lines_batch, [row for row in data[i: i+batch_size]])]
    to_upsert = zip(ids_batch, embeds, meta)
    # upsert to Pinecone
    index.upsert(vectors=list(to_upsert))
