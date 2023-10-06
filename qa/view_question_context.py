import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain.schema import (
    HumanMessage,
    SystemMessage
)

load_dotenv()

os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
#print(os.environ["OPENAI_API_KEY"])

# Get the guilds and channels data
def get_guilds_and_channels(cur):
    cur.execute("SELECT * FROM discord_guilds")
    guilds = {guild['guild_id']: guild['name'] for guild in cur.fetchall()}
    
    cur.execute("SELECT * FROM discord_channels")
    channels = {channel['channel_id']: {'name': channel['name'], 'guild_id': channel['guild_id']} for channel in cur.fetchall()}
    
    return guilds, channels

# Get replies recursively
def get_replies(cur, parent_id, messages):
    cur.execute("SELECT * FROM discord_messages WHERE parent_message_id = %s AND content IS NOT NULL AND content != ''", (parent_id,))
    rows = cur.fetchall()
    for row in rows:
        messages.append(row)
        get_replies(cur, row['id'], messages)

def get_conversation(cur, message_id):
    cur.execute("SELECT * FROM discord_messages WHERE id = %s", (message_id,))
    message = cur.fetchone()

    if not message:
        print("Message not found.")
        return

    guilds, channels = get_guilds_and_channels(cur)
    guild_name = guilds[channels[message['channel_id']]['guild_id']]
    channel_name = channels[message['channel_id']]['name']

    replies = []
    get_replies(cur, message_id, replies)

    if message['thread_id']:
        cur.execute("SELECT * FROM discord_messages WHERE thread_id = %s AND content IS NOT NULL AND content != ''", (message['thread_id'],))
        thread_replies = cur.fetchall()
        replies.extend(thread_replies)
        thread_name = message['thread_name']
        print(f"Thread: {thread_name}")

    cur.execute("""
        SELECT * FROM (
            (SELECT * FROM discord_messages
             WHERE channel_id = %s AND id::bigint > %s::bigint AND author_id::bigint != %s::bigint AND content IS NOT NULL AND content != ''
             ORDER BY id::bigint ASC LIMIT 25)
        ) AS combined
        ORDER BY id::bigint ASC
    """, (message['channel_id'], message_id, message['author_id']))
    next_conversation = cur.fetchall()

    print(f"Guild: {guild_name}")
    print(f"Channel: {channel_name}")
    if message['thread_id']:
        print(f"Thread: {thread_name}")

    print("\nQUESTION: ")
    print(f"{message['author_tag']}: {message['content']}")

    if replies:
        print("\nDirect replies:")
        for reply in replies:
            print(f"{reply['author_tag']}: {reply['content']}")

    print("\nOther messages in conversation:")
    for msg in next_conversation:
        print(f"{msg['author_tag']}: {msg['content']}")
    
    print("\nAnswer from GPT-4:")
    chat = ChatOpenAI(temperature=0, model_name='gpt-4', max_tokens=1000)

    system_prompt = """
    You are an expert at reading Discord Chat logs. Could you look through the context of a conversation that begins 
    with a question asked in a Nouns DAO-specialized Discord server? The user will include a conversation relevant to 
    the question, and your job is to identify whether the question was answered in the context. Sometimes the 
    conversation context will include direct replies to the user asking the question. Those could be highly relevant 
    as a potential match for an answer. The user will attempt to provide as many details as possible to each question, 
    including the channel's name. If the conversation context happened in a thread in the channel, the thread's name 
    would be included to help you gain more insight. The user will mark any part of the conversation that is a direct 
    reply to the user accordingly. This is usually a follow-up question or a high-signal answer. If there is no direct 
    reply, or the direct reply does not seem like an answer to the question, you should try to answer the question 
    based on any other context in the conversation. If you do not see an obvious answer to the question, do not make 
    one up; instead, simply state, "No answer located." If the question presented does not look like a question, reply with
    "Not a question." Also, if the question was answered, there is no need to prefix 
    your response with "Yes, the question was answered." Instead, please answer the question as best as you can, 
    given the context you are given. 


    ANSWER:
    """

    conversation_prompt = (
        "Guild: " + guild_name + "\n" +
        "Channel: " + channel_name + "\n" +
        ("Thread: " + thread_name + "\n" if message['thread_id'] else "") +
        "\nQUESTION:\n" +
            message['author_tag'] + ": " + message['content'] + "\n" +
            ("\nDirect replies:\n" if replies else "") +
            "".join([reply['author_tag'] + ": " + reply['content'] + "\n" for reply in replies]) +
            "\nOther messages in conversation:\n" +
            "".join([msg['author_tag'] + ": " + msg['content'] + "\n" for msg in next_conversation])
    )

    #print(conversation_template)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=conversation_prompt)
    ]
    print(chat(messages))


if __name__ == "__main__":
    conn = psycopg2.connect(os.getenv('DB_CONN_URL'))
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    message_id = input("Please enter a message ID: ")
    get_conversation(cur, message_id)

    conn.close()
