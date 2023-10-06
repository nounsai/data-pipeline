from create_relations_and_items import *
from wikibaseintegrator.datatypes import URL, Time, String
from wikibaseintegrator.wbi_enums import ActionIfExists
from wikibaseintegrator.models import Qualifiers
from wikibaseintegrator.wbi_exceptions import ModificationFailed
from tqdm import tqdm
import logging

# Set up logging
logging.basicConfig(
    filename="log_file.log",
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(message)s",
)

HERE = Path(__file__).parent.resolve()
DATA = HERE.parent.joinpath("data").resolve()


def main():
    # Read the KG data
    channel_info = pd.read_csv(DATA.joinpath("proposal_channels.csv"))

    properties = {
        "Timestamp": ("Qualifier for summaries", "time"),
        "Monthly Summary": ("A summary for a Discord channel", "string"),
        "Weekly Summary": ("A summary for a Discord channel", "string"),
        "Daily Summary": ("A summary for a Discord channel", "string"),
        "Question & Answer": ("A Q&A on a Discord channel. ", "string"),
        "Answer": (
            "A qualifier for 'Question & Answer' stating the answer to a question. ",
            "string",
        ),
        "Channel URL": ("The link for a channel on Discord", "url"),
        "Related Channel": (
            "A discord channel related to this Nouns proposal.",
            "wikibase-item",
        ),
        "Related Proposal": (
            "A Nouns Proposal related to this Nouns channel.",
            "wikibase-item",
        ),
    }

    create_properties(properties)

    items = {
        "Channel": (
            "Channel",
            "The 'instance of' value to be used for discord channels",
            "Q1",
        ),
    }

    create_items(items)

    discord_channels = channel_info[
        ["channel_id", "channel_name", "server_id", "server_name"]
    ].drop_duplicates()

    add_discord_channels(items_on_wikibase, discord_channels)

    items_on_wikibase["Channel"] = "Q4882"
    properties_in_wikibase["Related Proposal"] = "P88"

    prop_links = channel_info[
        ["proposal_id", "channel_id", "channel_name", "server_id", "server_name"]
    ].drop_duplicates()

    update_proposal_channel_mapping(prop_links, items_on_wikibase)

    properties_in_wikibase["Answer"] = "P81"
    properties_in_wikibase["Question & Answer"] = "P80"

    properties_in_wikibase["Channel URL"] = "P68"

    update_channel_url(discord_channels, items_on_wikibase)

    update_summaries(channel_info, items_on_wikibase)

    update_q_and_a(channel_info, items_on_wikibase)


def clean_up_string(string):
    summary = string
    if len(summary) > 2499:
        summary = summary[0:2400]
    summary = summary.replace("\n", "-").replace('"', "").strip()
    return summary


def create_properties(properties):
    for property_name, (description, data_type) in properties.items():
        add_property_if_not_exists(
            properties_in_wikibase, property_name, description, data_type
        )


def create_items(items):
    for item_name, (item_label, item_description, wd_item_id_value) in items.items():
        create_item_if_not_exists(
            item_name, item_label, item_description, wd_item_id_value
        )


def update_proposal_channel_mapping(prop_links, items_on_wikibase):
    statement = "update_proposal_channel_mapping"
    print(f"====== {statement} =====")
    logging.info(f"====== {statement} =====")
    for i, row in tqdm(prop_links.iterrows(), total=prop_links.shape[0]):
        channel_name = f"{row['server_name']} - {row['channel_name']}"
        channel_qid = items_on_wikibase[channel_name]
        try:
            proposal_qid = items_on_wikibase[f"Proposal {str(int(row['proposal_id']))}"]
        except KeyError as ke:
            logging.error("KeyError encountered: " + str(ke))
            continue

        wbi = WikibaseIntegrator(login=login_instance)
        item = wbi.item.get(entity_id=proposal_qid)
        data = []

        data.append(
            Item(
                prop_nr=properties_in_wikibase["Related Channel"],
                value=channel_qid,
            )
        )
        try:
            old_claims = item.claims

            serialized_obj1 = json.dumps(
                old_claims.__dict__, sort_keys=True, default=str
            )
            item.claims.add(data, action_if_exists=ActionIfExists.APPEND_OR_REPLACE)

            serialized_obj2 = json.dumps(
                item.claims.__dict__, sort_keys=True, default=str
            )

            if serialized_obj1 == serialized_obj2:
                pass
            else:
                item.write()
        except ModificationFailed as e:
            logging.error("ModificationFailed error encountered: " + str(e))
            continue

        item = wbi.item.get(entity_id=channel_qid)
        data = []

        data.append(
            Item(
                prop_nr=properties_in_wikibase["Related Proposal"],
                value=proposal_qid,
            )
        )
        try:
            old_claims = item.claims

            serialized_obj1 = json.dumps(
                old_claims.__dict__, sort_keys=True, default=str
            )
            item.claims.add(data, action_if_exists=ActionIfExists.APPEND_OR_REPLACE)

            serialized_obj2 = json.dumps(
                item.claims.__dict__, sort_keys=True, default=str
            )

            if serialized_obj1 == serialized_obj2:
                pass
            else:
                item.write()
        except ModificationFailed as e:
            logging.error("ModificationFailed error encountered: " + str(e))
            continue


def add_discord_channels(items_on_wikibase, discord_channels):
    for i, row in tqdm(discord_channels.iterrows(), total=discord_channels.shape[0]):
        channel_name = f"{row['server_name']} - {row['channel_name']}"
        create_item_if_not_exists(
            item_name=channel_name,
            item_label=channel_name,
            item_description="A Nouns discord channel.",
            wd_item_id_value=items_on_wikibase["Channel"],
        )


def update_q_and_a(channel_info, items_on_wikibase):
    statement = "update_q_and_a"
    print(f"====== {statement} =====")
    logging.info(f"====== {statement} =====")

    proposal_ids = list(set(channel_info["proposal_id"]))
    proposal_ids.sort()

    for proposal_id in tqdm(proposal_ids):
        channel_info_for_proposal = channel_info[
            channel_info["proposal_id"] == proposal_id
        ]
        try:
            proposal_qid = items_on_wikibase[f"Proposal {str(proposal_id)}"]
        except KeyError as ke:
            logging.error("KeyError encountered: " + str(ke))
            continue
        wbi = WikibaseIntegrator(login=login_instance)
        item = wbi.item.get(entity_id=proposal_qid)
        data = []
        for i, row in channel_info_for_proposal.iterrows():
            channel_name = f"{row['server_name']} - {row['channel_name']}"
            channel_qid = items_on_wikibase[channel_name]
            qualifiers = Qualifiers()
            qualifiers.add(
                Item(
                    prop_nr=properties_in_wikibase["Related Channel"],
                    value=channel_qid,
                )
            )
            if row["question"] != row["question"]:  # test na
                continue
            if row["answer"] != row["answer"]:  # test na
                data.append(
                    String(
                        prop_nr=properties_in_wikibase["Question & Answer"],
                        value=clean_up_string(row["question"]),
                        qualifiers=qualifiers,
                    )
                )
                continue
            else:
                qualifiers.add(
                    String(
                        value=clean_up_string(row["answer"]),
                        prop_nr=properties_in_wikibase["Answer"],
                    )
                )
                data.append(
                    String(
                        prop_nr=properties_in_wikibase["Question & Answer"],
                        value=clean_up_string(row["question"]),
                        qualifiers=qualifiers,
                    )
                )

        try:
            old_claims = item.claims

            serialized_obj1 = json.dumps(
                old_claims.__dict__, sort_keys=True, default=str
            )
            item.claims.add(data, action_if_exists=ActionIfExists.APPEND_OR_REPLACE)

            serialized_obj2 = json.dumps(
                item.claims.__dict__, sort_keys=True, default=str
            )

            if serialized_obj1 == serialized_obj2:
                pass
            else:
                item.write()
        except ModificationFailed as e:
            logging.error("ModificationFailed error encountered: " + str(e))
            continue


def update_summaries(channel_info, items_on_wikibase):
    statement = "update_summaries"
    print(f"====== {statement} =====")
    logging.info(f"====== {statement} =====")
    for i, row in tqdm(channel_info.iterrows(), total=channel_info.shape[0]):
        if row["interval"] == "month":
            property_name = "Monthly Summary"
        elif row["interval"] == "week":
            property_name = "Weekly Summary"
        elif row["interval"] == "day":
            property_name = "Daily Summary"
        else:
            continue

        try:
            proposal_qid = items_on_wikibase[f"Proposal {str(row['proposal_id'])}"]
        except KeyError as ke:
            logging.error("KeyError encountered: " + str(ke))
            continue
        channel_name = f"{row['server_name']} - {row['channel_name']}"
        channel_qid = items_on_wikibase[channel_name]
        wbi = WikibaseIntegrator(login=login_instance)
        item = wbi.item.get(entity_id=proposal_qid)
        data = []
        qualifiers = Qualifiers()
        qualifiers.add(
            Item(
                prop_nr=properties_in_wikibase["Related Channel"],
                value=channel_qid,
            )
        )

        import datetime

        timestamp = datetime.datetime.strptime(row["timestamp"], "%Y-%m-%d").strftime(
            "+%Y-%m-%dT00:00:00Z"
        )
        qualifiers.add(
            Time(time=timestamp, prop_nr=properties_in_wikibase["Timestamp"])
        )

        summary = clean_up_string(row["summary"])

        data.append(
            String(
                prop_nr=properties_in_wikibase[property_name],
                value=summary,
                qualifiers=qualifiers,
            )
        )
        try:
            old_claims = item.claims
            serialized_obj1 = json.dumps(
                old_claims.__dict__, sort_keys=True, default=str
            )
            item.claims.add(data, action_if_exists=ActionIfExists.APPEND_OR_REPLACE)

            serialized_obj2 = json.dumps(
                item.claims.__dict__, sort_keys=True, default=str
            )

            if serialized_obj1 == serialized_obj2:
                pass
            else:
                item.write()
        except ModificationFailed as e:
            logging.error("ModificationFailed error encountered: " + str(e))
            continue


def update_channel_url(discord_channels, items_on_wikibase):
    for i, row in tqdm(discord_channels.iterrows(), total=discord_channels.shape[0]):
        channel_name = f"{row['server_name']} - {row['channel_name']}"
        channel_qid = items_on_wikibase[channel_name]
        wbi = WikibaseIntegrator(login=login_instance)
        item = wbi.item.get(entity_id=channel_qid)

        # Update Channel URL
        url = f"https://discordapp.com/channels/{row['server_id']}/{row['channel_id']}"
        data = []
        data.append(
            URL(
                value=url,
                prop_nr=properties_in_wikibase["Channel URL"],
            )
        )
        try:
            old_claims = item.claims

            serialized_obj1 = json.dumps(
                old_claims.__dict__, sort_keys=True, default=str
            )
            item.claims.add(data, action_if_exists=ActionIfExists.REPLACE_ALL)

            serialized_obj2 = json.dumps(
                item.claims.__dict__, sort_keys=True, default=str
            )

            if serialized_obj1 == serialized_obj2:
                pass
            else:
                item.write()
        except ModificationFailed as e:
            logging.error("ModificationFailed error encountered: " + str(e))
            continue


if __name__ == "__main__":
    main()
