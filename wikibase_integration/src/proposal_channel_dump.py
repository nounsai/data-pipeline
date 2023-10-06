from dotenv import load_dotenv
import os
import psycopg2
import pandas as pd
from pathlib import Path

load_dotenv()

conn = psycopg2.connect(os.getenv("DB_CONN_URL"))
cur = conn.cursor()

sql_summary = """
SELECT 
    pc.proposal_id,
    dc.channel_id,
    dc.name,
    dg.guild_id,
    dg.name,
    s.timestamp,
    s.interval,
    s.summary
FROM proposal_channels pc
JOIN discord_channels dc ON pc.channel_id = dc.channel_id
   OR (pc.channel_id IS NULL AND pc.server_id = dc.guild_id) 
JOIN discord_guilds dg ON dc.guild_id = dg.guild_id
JOIN summary s ON s.channel_id = dc.channel_id
"""

sql_qa = """
SELECT DISTINCT
  pc.proposal_id,
  dc.channel_id,
  dc.name,
  dg.guild_id, 
  dg.name,
  q.question,
  q.answer 
FROM discord_channels dc
JOIN discord_guilds dg 
  ON dc.guild_id = dg.guild_id  
JOIN discord_messages dm
  ON dc.channel_id = dm.channel_id
JOIN qa2 q
  ON dm.id = q.message_id
JOIN proposal_channels pc ON dc.channel_id = pc.channel_id
"""

# execute the SQL queries and fetch all the results
cur.execute(sql_summary)
summary_data = cur.fetchall()

cur.execute(sql_qa)
qa_data = cur.fetchall()

# create pandas dataframes for summary and QA data
summary_df = pd.DataFrame(
    summary_data,
    columns=[
        "proposal_id",
        "channel_id",
        "channel_name",
        "server_id",
        "server_name",
        "timestamp",
        "interval",
        "summary",
    ],
)

qa_df = pd.DataFrame(
    qa_data,
    columns=[
        "proposal_id",
        "channel_id",
        "channel_name",
        "server_id",
        "server_name",
        "question",
        "answer",
    ],
)
# qa_df = pd.DataFrame(
#     qa_data,
#     columns=[
#         "channel_id",
#         "channel_name",
#         "server_id",
#         "server_name",
#         "question",
#         "answer",
#     ],
# )

# merge the two dataframes
merged_df = pd.concat([summary_df, qa_df], ignore_index=True)

# close the cursor and connection
cur.close()
conn.close()


# save the merged dataframe to a CSV file
HERE = Path(__file__).parent.resolve()
DATA = HERE.parent.joinpath("data").resolve()
merged_df.to_csv(DATA.joinpath("proposal_channels.csv"), index=False)
