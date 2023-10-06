import os
import psycopg2
from psycopg2.extras import RealDictCursor
import pinecone
import openai
from tqdm import tqdm
from dotenv import load_dotenv
from openai.error import RateLimitError
from retrying import retry

load_dotenv()

@retry(stop_max_attempt_number=7, wait_exponential_multiplier=1000, wait_exponential_max=10000, retry_on_exception=lambda e: isinstance(e, RateLimitError))
def create_embedding(chunk):
    return openai.Embedding.create(input=chunk, engine=MODEL)

def chunks(lst, size):
    """Yield successive size-sized chunks from lst."""
    for i in range(0, len(lst), size):
        yield lst[i:i + size]

openai.api_key = os.getenv('OPENAI_API_KEY')

conn = psycopg2.connect(os.getenv('DB_CONN_URL'))

cur = conn.cursor(cursor_factory=RealDictCursor)

query = """
select message_id, question FROM qa2 WHERE is_relevant = 1 AND hidden = 0 AND answer IS NOT NULL
"""
cur.execute(query)

data = cur.fetchall()

cur.close()
conn.close()

MODEL = "text-embedding-ada-002"

questions = [row['question'] for row in data]
embeds = []

chunk_size = 10  # Adjust this value based on the API limitations

for chunk in tqdm(chunks(questions, chunk_size), total=len(questions)//chunk_size):
    try:
        res = create_embedding(chunk)
        embeds.extend([record['embedding'] for record in res['data']])
    except Exception as e:
        print(f"Exception occurred: {e}")

pinecone.init(os.getenv('PINECONE_API_KEY'), environment="us-west1-gcp")
index_name = 'nounsai-qa'

if index_name not in pinecone.list_indexes():
    pinecone.create_index(index_name, dimension=len(embeds[0]))

index = pinecone.Index(index_name)

batch_size = 32  # process everything in batches of 32
for i in tqdm(range(0, len(data), batch_size), total=len(data)//batch_size):
    i_end = min(i+batch_size, len(data))
    lines_batch = [row['question'] for row in data[i: i+batch_size]]
    ids_batch = [str(n) for n in range(i, i_end)]
    
    try:
        res = create_embedding(lines_batch)
        embeds = [record['embedding'] for record in res['data']]
        meta = [{'text': line, 'message_id': row['message_id']} for line, row in zip(lines_batch, [row for row in data[i: i+batch_size]])]
        to_upsert = zip(ids_batch, embeds, meta)
        index.upsert(vectors=list(to_upsert))
    except Exception as e:
        print(f"Exception occurred: {e}")
