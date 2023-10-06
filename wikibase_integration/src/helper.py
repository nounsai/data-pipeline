from login import *
from wikibaseintegrator import wbi_login, WikibaseIntegrator
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator import wbi_helpers
from wikibaseintegrator.datatypes import Item, Property
from wikibaseintegrator.wbi_exceptions import ModificationFailed, MWApiError
from requests.exceptions import HTTPError

from pathlib import Path
import json
import re
import logging

wikibase_prefix = "nounsdev"
wbi_config["MEDIAWIKI_API_URL"] = f"https://{wikibase_prefix}.wikibase.cloud/w/api.php"
wbi_config[
    "SPARQL_ENDPOINT_URL"
] = f"https://{wikibase_prefix}.wikibase.cloud/query/sparql"
wbi_config["WIKIBASE_URL"] = f"https://{wikibase_prefix}.wikibase.cloud"

wbi_config["USER_AGENT"] = "NounsWikibaseBot"

login_instance = wbi_login.Clientlogin(user=WD_USER, password=WD_PASS)

logging.basicConfig(
    filename="log_file.log",
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(message)s",
)


## Curate information on properties

# Wikibase properties categorized by datatype
item_properties = {
    "Proposal Type",
    "Transfer To",
    "Proposer",
    "Status",
    "Previous Proposal",
    "Supported By",
    "Opposed By",
    "Createedition To",
    "Sendorregisterdebt To",
    "Sendorregisterdebt To Nouns",
    "Setproposalthresholdbps To",
    "Abstained By",
}

inverse_properties = {
    "Supported By": "Supported",
    "Opposed By": "Opposed",
    "Abstained By": "Abstained",
    "Proposer": "Proposed",
}

# Mapping of relations to their corresponding range
relation_to_range_mapping = {
    "Proposal Type": "Proposal Type",
    "Transfer To": "Individual",
    "Proposer": "Individual",
    "Supported By": "Individual",
    "Opposed By": "Individual",
    "Abstained By": "Individual",
    "Previous Proposal": "Proposal",
    "Status": "Status",
    "Createedition To": "Individual",
    "Sendorregisterdebt To Nouns": "Individual",
    "Sendorregisterdebt To": "Individual",
    "Setproposalthresholdbps To": "Individual",
}

date_properties = {"ExecutionETA", "Proposal Submission Date"}
string_properties = {"Label", "Summary", "Team Name"}
quantity_properties = {
    "Transfer Value",
    "Proposal Duration in Months",
    "Proposal Budget",
    "Supporter Count",
    "Opposer Count",
    "Abstain Count",
    "Quorumvotes",
    "Id",
    "Team Size",
    "Proposal Budget in USD",
    "Proposal Budget in ETH",
    "Proposal Budget in stETH",
    "Transfer Value in ETH",
    "Sendorregisterdebt Value To Nouns",
    "Sendorregisterdebt Value",
    "Setproposalthresholdbps Value",
}


def createProperty(
    label="",
    description="",
    property_datatype="",
):
    wbi = WikibaseIntegrator(login=login_instance)
    prop = wbi.property.new(datatype=property_datatype)
    prop.labels.set(language="en", value=label)
    prop.descriptions.set(language="en", value=description)
    try:
        new_property = prop.write()
        return new_property

    except MWApiError as e:
        print(e)
        pass


def get_properties_in_wikibase():
    property_lookup = {}

    query = """
    SELECT ?property ?label
    WHERE {
        ?property a wikibase:Property .
        ?property rdfs:label ?label .
        FILTER (LANG(?label) = "en" )
    }"""

    results = wbi_helpers.execute_sparql_query(
        query=query, endpoint=wbi_config["SPARQL_ENDPOINT_URL"]
    )

    for result in results["results"]["bindings"]:
        label = result["label"]["value"]
        property_lookup[label] = result["property"]["value"].split("/")[-1]

    return property_lookup


def get_items_on_wikibase():
    item_lookup = {}

    query = """
    SELECT ?item ?label WHERE {
      ?item rdfs:label ?label.
      FILTER((LANG(?label)) = "en")
      MINUS { ?item a wikibase:Property } 
    }"""

    results = wbi_helpers.execute_sparql_query(
        query=query, endpoint=wbi_config["SPARQL_ENDPOINT_URL"]
    )

    for result in results["results"]["bindings"]:
        label = result["label"]["value"]
        item_lookup[label] = result["item"]["value"].split("/")[-1]

    return item_lookup


# Get existing properties and items in wikibase
properties_in_wikibase = get_properties_in_wikibase()
items_on_wikibase = get_items_on_wikibase()


# Get the current working directory
HERE = Path(__file__).parent.resolve()

# Get existing properties and items in wikibase
properties_in_wikibase = get_properties_in_wikibase()


def update_by_key_value_pair(key, value):
    # Load current items
    current_items_path = HERE.joinpath("current_items.json")
    if current_items_path.exists():
        with open(current_items_path, "r") as f:
            current_items = json.load(f)
    else:
        current_items = {}

    # Update the dictionary with the provided key-value pair
    current_items[key] = value

    # Save updated items to file
    with open(current_items_path, "w") as f:
        json.dump(current_items, f, indent=4, sort_keys=True)

    items_on_wikibase = current_items


# Define the method to update the current_items.json file
def update_items_file():
    # Load current items
    current_items_path = HERE.joinpath("current_items.json")
    if current_items_path.exists():
        with open(current_items_path, "r") as f:
            current_items = json.load(f)
    else:
        current_items = {}

    # Update current items with items from wikibase
    items_on_wikibase = get_items_on_wikibase()
    current_items.update(items_on_wikibase)

    # Save updated items to file
    with open(current_items_path, "w") as f:
        json.dump(current_items, f, indent=4, sort_keys=True)

    return current_items


# Call the method to update the current_items.json file
items_on_wikibase = update_items_file()


# Create property in wikibase if it doesn't exist
def create_property_if_not_exists(property_name):
    if property_name not in properties_in_wikibase.keys():
        property_datatype = ""
        if property_name in item_properties:
            property_datatype = "wikibase-item"
        if property_name in string_properties:
            property_datatype = "string"
        if property_name in quantity_properties:
            property_datatype = "quantity"
        if property_name in date_properties:
            property_datatype = "time"
        if property_datatype == "":
            print(f"{property_name} not in any list")
            return None
        new_property = createProperty(
            label=property_name,
            description="machine-generated property",
            property_datatype=property_datatype,
        )
        print(f"Property {new_property} created successfully.")
        return new_property
    else:
        return None


def create_item_if_not_exists(
    item_name, item_label, item_description, wd_item_id_value, item_aliases=None
):
    if item_name not in items_on_wikibase.keys():
        print(item_name)
        wbi = WikibaseIntegrator(login=login_instance)

        data = [Item(value=wd_item_id_value, prop_nr="P6")]
        # Create a new item
        item = wbi.item.new()
        item.labels.set(language="en", value=item_label)
        item.descriptions.set(language="en", value=item_description)
        if item_aliases:
            item.aliases.set(language="en", values=[item_aliases])
        item.claims.add(data)
        try:
            new_item = item.write()
            update_by_key_value_pair(item_label, new_item.id)

        except ModificationFailed as e:
            print(e)
            # Parse the error message to get the label and QID
            error_message = str(e)
            match = re.search(
                r'Item \[\[Item:(Q[0-9]+)\|(Q[0-9]+)\]\] already has label "(.*?)"',
                error_message,
            )
            if match:
                item_qid = match.group(1)
                item_label = match.group(3)
                # Update the dictionary with the label and QID
                update_by_key_value_pair(item_label, item_qid)
        except HTTPError as e:
            print(e)
            pass
    else:
        return None
