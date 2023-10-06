from nounish_question_classifier import NounishQuestionClassifier
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv('DB_CONN_URL'))
cur = conn.cursor(cursor_factory=RealDictCursor)

all_questions_query = """
select dm.content as question,dm.id from discord_messages as dm
JOIN qa2_staging as qa2 on dm.id = qa2.message_id
WHERE qa2.is_relevant IS NULL
"""

cur.execute(all_questions_query)
rows = cur.fetchall()

# You can pass the model path if it's different from the default
predictor = NounishQuestionClassifier()
relevant_count = 0
not_relevant_count = 0
for row in rows:
    # print(row['question'])
    result = predictor.predict(row['question'])
    print(f"[{result}][{row['id']}] {row['question']}")
    is_relevant = 1 if result == 'Relevant' else 0

    update_query = """
    UPDATE qa2_staging
    SET is_relevant = %s
    WHERE message_id = %s
    """
    cur.execute(update_query, (is_relevant, row['id']))
    conn.commit()

    if result == "Relevant":
        relevant_count += 1
    else:
        not_relevant_count += 1

print(f"Total Relevant questions: {relevant_count}")
print(f"Total Not Relevant questions: {not_relevant_count}")

# result = predictor.predict("How are you going to vote on proposal 185?")
# print(result)
