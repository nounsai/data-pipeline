import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('DB_CONN_URL'))

cur = conn.cursor(cursor_factory=RealDictCursor)

query = """
SELECT qv.similar_question_id
FROM question_votes qv
JOIN qa2 ON qv.similar_question_id = qa2.message_id
WHERE qv.downvotes >= 3 AND qa2.hidden = 0
GROUP BY qv.similar_question_id, qv.id, qv.original_question_id, qv.original_question_text, qv.upvotes, qv.downvotes, qv.created_at, qv.updated_at;
"""

cur.execute(query)
result = cur.fetchall()

for row in result:
    similar_question_id = row['similar_question_id']
    update_query = """
    UPDATE qa2
    SET hidden = 1
    WHERE message_id = %s;
    """
    cur.execute(update_query, (similar_question_id,))

# Commit the changes and close the connection
conn.commit()
cur.close()
conn.close()
