import os
import psycopg2
from psycopg2.extras import RealDictCursor
import pinecone
import openai
from dotenv import load_dotenv
load_dotenv()

openai.api_key = os.getenv('OPENAI_API_KEY')

pinecone.init(os.getenv('PINECONE_API_KEY'), environment="us-west1-gcp")
index_name = 'nounsai-qa'
index = pinecone.Index(index_name)

conn = psycopg2.connect(os.getenv('DB_CONN_URL'))
cur = conn.cursor(cursor_factory=RealDictCursor)

get_answer_query = "SELECT answer FROM qa2 WHERE id = %s"

while True:
    query = input("Enter a Nouns related question: ")
    if query == "exit":
        break
    else:
        xq = openai.Embedding.create(input=query, engine="text-embedding-ada-002")['data'][0]['embedding']
        res = index.query([xq], top_k=5, include_metadata=True)
        for match in res['matches']:
            id = match['metadata']['id']
            query = f"SELECT * FROM qa2 WHERE id = '{id}'"
            cur.execute(query)
            answer = cur.fetchone()['answer']
            print(f"\nQuestion: {match['metadata']['text']}  \n Score: {match['score']:.2f} \n Answer: {answer} \n ID: {id}\n")
            conn.commit()

cur.close()
conn.close()

