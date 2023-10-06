import os
import psycopg2
from psycopg2.extras import RealDictCursor

from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('DB_CONN_URL'))
cur = conn.cursor(cursor_factory=RealDictCursor)

def execute_query(query_string):
    cur.execute(query_string)
    results = cur.fetchall()
    return results