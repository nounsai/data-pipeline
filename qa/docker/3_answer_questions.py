import json
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain.schema import (
    HumanMessage,
    SystemMessage
)
from datetime import datetime
import tiktoken


load_dotenv()

os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super(DateTimeEncoder, self).default(obj)


def get_discord_messages(cur, message_ids):
    if not message_ids:
        return []

    message_ids_str = ','.join([f"'{str(id)}'" for id in message_ids])
    cur.execute(
        f"""SELECT * FROM discord_messages WHERE id IN ({message_ids_str})""")
    messages = cur.fetchall()
    return messages


def num_tokens_from_messages(messages, model="gpt-3.5-turbo"):
    """Return the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model in {
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-16k",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-32k-0613",
    }:
        tokens_per_message = 3
        tokens_per_name = 1
    elif model == "gpt-3.5-turbo-0301":
        # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_message = 4
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif "gpt-3.5-turbo" in model:
        print("Warning: gpt-3.5-turbo may update over time. Returning num tokens assuming gpt-3.5-turbo-0613.")
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613")
    elif "gpt-4" in model:
        print(
            "Warning: gpt-4 may update over time. Returning num tokens assuming gpt-4-0613.")
        return num_tokens_from_messages(messages, model="gpt-4-0613")
    else:
        raise NotImplementedError(
            f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
        )
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens


def export_data_to_json(cur):
    cur.execute(
        """SELECT id, question, answer, logs FROM qa2 WHERE is_relevant = 1 AND answer IS NOT NULL""")
    items = cur.fetchall()

    data = []
    print("Total items:", len(items))
    for item in items:
        print(f"Processing item ID: {item['id']}")
        logs = item['logs']
        reply_ids = logs["reply_ids"]
        conversation_ids = logs["conversation_ids"]

        direct_replies = get_discord_messages(cur, reply_ids)
        other_messages = get_discord_messages(cur, conversation_ids)

        data.append({
            "id": item["id"],
            "question": item["question"],
            "answer": item["answer"],
            "logs": {
                "direct_replies": direct_replies,
                "other_messages": other_messages
            }
        })
        # print(data)

    with open("data.json", "w") as f:
        json.dump(data, f, indent=2, cls=DateTimeEncoder)


def get_guilds_and_channels(cur):
    cur.execute("SELECT * FROM discord_guilds")
    guilds = {guild['guild_id']: guild['name'] for guild in cur.fetchall()}

    cur.execute("SELECT * FROM discord_channels")
    channels = {channel['channel_id']: {'name': channel['name'],
                                        'guild_id': channel['guild_id']} for channel in cur.fetchall()}

    return guilds, channels


def get_replies(cur, parent_id, messages):
    cur.execute(
        "SELECT * FROM discord_messages WHERE parent_message_id = %s AND content IS NOT NULL AND content != ''", (parent_id,))
    rows = cur.fetchall()
    for row in rows:
        messages.append(row)
        get_replies(cur, row['id'], messages)


def process_message(cur, message_id):
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
        # cur.execute("SELECT * FROM discord_messages WHERE thread_id = %s AND content IS NOT NULL AND content != ''", (message['thread_id'],))
        cur.execute("SELECT * FROM discord_messages WHERE thread_id = %s AND content IS NOT NULL AND content != '' AND id > %s ORDER BY id ASC LIMIT 25",
                    (message['thread_id'], message_id))
        thread_replies = cur.fetchall()
        replies.extend(thread_replies)
        thread_name = message['thread_name'] if message['thread_name'] else ""

    query = f"""
        SELECT * FROM (
            (
                SELECT * FROM discord_messages
                WHERE channel_id = '{message['channel_id']}' AND id::bigint < '{message_id}'::bigint AND author_id::bigint != '{message['author_id']}'::bigint AND content IS NOT NULL AND content != ''
                ORDER BY id::bigint DESC LIMIT 10
            ) UNION ALL (
                SELECT * FROM discord_messages
                WHERE channel_id = '{message['channel_id']}' AND id::bigint > '{message_id}'::bigint AND author_id::bigint != '{message['author_id']}'::bigint AND content IS NOT NULL AND content != ''
                ORDER BY id::bigint ASC LIMIT 25
            )
        ) AS combined
        ORDER BY id::bigint ASC
    """
    # print("Query:", query)
    cur.execute(query)

    next_conversation = cur.fetchall()

    print(f"Processing message ID: {message_id}")

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
    one up; instead, simply state, "No answer located." If the question was answered, please do NOT start an answer 
    with "Yes, the question was answered." Instead, please answer the question as best as you can.
    """

    system_multi_shot_1 = """
    QUESTION: 
    Wen delegate to multiple addresses from a single address? Seems like a non-trivial problem / anyone 
    think they can build for < 200 eth? 

    Direct Replies:
    sidenoun#1868: That’s actually a brilliant idea
    9999#9948: The unfortunate result of not thinking a year into the future and forking a fungible governance protocol is that delegation is treated as fungible units at the token layer so its behaviour can’t be changed. However, <@850478993463443487> has a beta for a Gnosis Safe module that can transfer a Noun to a Safe controlled sub-contract for single Id delegation.
    willprice#7766: delegation lives in the immutable token contract
    willprice#7766: oh I should read before typing lol

    Other messages in conversation:
    shobhit#5121: cool; thanks! 🙂
    Energy#7362: Hey everyone, not sure if this is the right channel. I'm exploring the use of SVGs, fully on-chain art and some possible Noun ideas, and wondered what was the reason for the 320x320px for Nouns? I know a project using vectors/SVGs could be something like 24x24px and rendered/scaled higher as an alternative. I usually work with raster images, and i'm trying to understand what is considered 'best practice' for fully on-chain projects. Thanks.
    CryptoRalph#0001: Awesome - even better. Thanks 👍
    sidenoun#1868: Someone can correct me if I'm wrong, but on chain they're not actually 320x320, they're 32x32, however, when encoded to an svg, their size is then 320x320 👉 https://github.com/nounsDAO/nouns-monorepo/blob/5afbdc328a2e9f14ea349638d64311a4f1310e16/packages/nouns-contracts/contracts/libs/MultiPartRLEToSVG.sol#L55
    brianj#3816: ^ this is correct
    brianj#3816: they default render to 320x320 but the "size" of the image in pixels (unscaled) is 32x32
    Energy#7362: Thank you both 🤌
    pp!!#4352: any developers here that specialize in creating websites?
    !𝚡𝚊𝚛𝚐𝚜#0333: Yes!

    ANSWER:
    Delegation is treated as fungible units at the token layer, so its behavior can't be changed. However, there is 
    a beta for a Gnosis Safe module that can transfer a Noun to a Safe controlled sub-contract for single Id delegation.
    """

    system_multi_shot_2 = """
    QUESTION: 
    headed for a beer with Lil Bubble maybe we can buy some alts at all time lows or maybe we could do something nounish?

    Other messages in conversation:
    Usergnome#0001: https://tenor.com/view/aspen-trees-gif-13203990
    brennen.eth#7360: anyone watch the new kids in the hall episodes
    brennen.eth#7360: thats what triggered all this rewatch
    brennen.eth#7360: https://www.youtube.com/watch?v=A-avHA_9SvY
    Usergnome#0001: Watching right now haha
    brennen.eth#7360: always reminded me of this https://www.youtube.com/watch?v=gyD8kdOiAOM
    brennen.eth#7360: FLCL for life
    Usergnome#0001: Trying to spot from episode summaries which will have bouncing weiners but it’s so hard to tell
    brennen.eth#7360: what a youtube quote

    ANSWER: 
    No answer located.
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
        "".join([msg['author_tag'] + ": " + msg['content'] + "\n" for msg in next_conversation]) +
        "\"ANSWER:\n"
    )

    all_prompts = [
        {'content': system_prompt},
        {'content': system_multi_shot_1},
        {'content': system_multi_shot_2},
        {'content': conversation_prompt}
    ]
    token_count = num_tokens_from_messages(all_prompts)

    model_name = "gpt-3.5-turbo"
    if token_count > 3846:
        model_name = "gpt-3.5-turbo-16k"

    chat = ChatOpenAI(temperature=0, model_name=model_name, max_tokens=250)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=system_multi_shot_1),
        HumanMessage(content=system_multi_shot_2),
        HumanMessage(content=conversation_prompt)
    ]
    gpt4_response = chat(messages)

    answer = gpt4_response.content
    question = message['content']

    print(f"Question: {question}\nAnswer: {answer}\n")

    no_answer = 0
    if answer in ("Not a question.", "No answer located."):
        no_answer = 1
        answer = None

    logs = {
        'thread_id': message['thread_id'],
        'reply_ids': [reply['id'] for reply in replies],
        'conversation_ids': [msg['id'] for msg in next_conversation],
        'conversation_prompt': conversation_prompt,
    }

    logs_json = json.dumps(logs)

    cur.execute("""
        UPDATE qa2_staging SET answered = %s WHERE message_id = %s;
    """, (0 if no_answer == 1 else 1, message_id))

    if no_answer == 0:
        cur.execute("""
            INSERT INTO qa2 (message_id, question, answer, model, logs, is_relevant)
            VALUES (%s, %s, %s, %s, %s, 1);
        """, (message_id, question, answer, model_name, logs_json))

    cur.connection.commit()


if __name__ == "__main__":
    conn = psycopg2.connect(os.getenv('DB_CONN_URL'))
    cur = conn.cursor(cursor_factory=RealDictCursor)
    # export_data_to_json(cur)

    cur.execute("""
        SELECT message_id FROM qa2_staging
        WHERE is_relevant = 1
        AND answered = 0
        AND NOT EXISTS (
            SELECT 1 FROM qa2 WHERE qa2.message_id = qa2_staging.message_id
        )
    """)

    # # Test with one message_id
    # #process_message(cur, message_ids[0])
    # for message_id in message_ids:
    #     process_message(cur, message_id)

    message_ids = [row['message_id'] for row in cur.fetchall()]

    for message_id in message_ids:
        process_message(cur, message_id)

    conn.close()
