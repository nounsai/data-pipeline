import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import spacy

load_dotenv()

nlp = spacy.load("en_core_web_sm")


def is_question(text):
    doc = nlp(text)

    for sent in doc.sents:
        # Check for question mark at the end
        if len(sent) > 1 and sent[-1].text == "?":
            return True

        # Check for question word followed by an auxiliary verb
        if len(sent) > 2 and sent[0].lower_ in ["who", "what", "when", "where", "why", "how"] and sent[1].dep_ in ["aux", "ROOT"]:
            return True

        # Check for auxiliary verb at the beginning
        if len(sent) > 1 and sent[0].tag_ in ["VB", "VBP", "VBZ"]:
            nsubj_found = False
            for token in sent[1:]:
                if token.dep_ == "nsubj":
                    nsubj_found = True
                if nsubj_found and token.dep_ == "ROOT":
                    return True

    return False


conn = psycopg2.connect(os.getenv('DB_CONN_URL'))
cur = conn.cursor(cursor_factory=RealDictCursor)

# Empty the contents of the qa2_staging table
truncate_staging_query = """
DELETE from qa2_staging where answered = 1
"""
cur.execute(truncate_staging_query)

get_last_processed_id_query = """
SELECT MAX(CAST(message_id AS BIGINT)) as last_id
FROM qa2;
"""
cur.execute(get_last_processed_id_query)
last_processed_id = cur.fetchone()['last_id']


# all_content_query = """
# SELECT id, content
# FROM discord_messages
# WHERE content IS NOT NULL AND content != '';
# """

all_content_query = f"""
SELECT dm.id, dm.content
FROM discord_messages dm
JOIN discord_channels dc ON dm.channel_id = dc.channel_id
LEFT JOIN discord_channels dc_parent ON dc.parent_channel_id = dc_parent.channel_id
WHERE dm.content IS NOT NULL AND dm.content != '' AND CAST(dm.id AS BIGINT) > {last_processed_id}
AND dc.log != 0
AND (dc_parent.channel_id IS NULL OR dc_parent.log != 0);
"""

cur.execute(all_content_query)

# iterate through all of the rows and print the ones that are a question
for row in cur.fetchall():
    if is_question(row['content']):
        insert_query = """
        INSERT INTO qa2_staging (message_id)
        VALUES (%s);
        """
        print(f"Inserting question:  {row['content']}")
        cur.execute(insert_query, (row['id'],))

conn.commit()
