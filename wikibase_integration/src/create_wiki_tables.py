from datetime import datetime

from wikibaseintegrator import wbi_helpers

import requests

from login import WD_PASS, WD_USER


def create_wiki_table(wikibase_prefix, query):
    # Run the query
    results = wbi_helpers.execute_sparql_query(
        query, endpoint=f"https://{wikibase_prefix}.wikibase.cloud/query/sparql"
    )

    # Retrieve the header names from the results
    headers = results["head"]["vars"]

    # Begin the table in wiki markup
    wiki_table = '{| class="wikitable"\n|-\n! ' + " !! ".join(
        [f"{header.capitalize()}" for header in headers]
    )

    for result in results["results"]["bindings"]:
        # For each row, add a line to the table
        wiki_table += f"\n|-\n" + " ".join(
            [f"|| {result[header]['value']}" for header in headers]
        )

    # End the table in wiki markup
    wiki_table += "\n|}"

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    # Begin the table in wiki markup, including the time of last update
    wiki_table = f"''This table was last updated on {now} (UTC).''\n" + wiki_table
    return wiki_table


wikibase_prefix = "nounsdev"
query = """
    SELECT ?item ?itemLabel ?nouns_url WHERE {
        ?item <https://nounsdev.wikibase.cloud/prop/direct/P6> <https://nounsdev.wikibase.cloud/entity/Q2> . 
        ?item <https://nounsdev.wikibase.cloud/prop/direct/P15> ?id . 
        ?item <https://nounsdev.wikibase.cloud/prop/direct/P21> ?nouns_url . 
        ?item rdfs:label ?itemLabel
    }
    ORDER BY ?id
"""
# Create wiki table
wiki_table = create_wiki_table(wikibase_prefix, query)

# Write wiki table to file
with open("proposals.txt", "w") as f:
    f.write(wiki_table)

query = """
SELECT ?item ?itemLabel WHERE {
    <https://nounsdev.wikibase.cloud/entity/P6> wikibase:directClaim ?p .
    ?item ?p <https://nounsdev.wikibase.cloud/entity/Q8> . 
    ?item rdfs:label ?itemLabel
}
ORDER BY ?itemLabel
"""
# Create wiki table
wiki_table = create_wiki_table(wikibase_prefix, query)

# Write wiki table to file
with open("individuals.txt", "w") as f:
    f.write(wiki_table)


S = requests.Session()

URL = "https://nounsdev.wikibase.cloud/w/api.php"

LOGIN_TOKEN = S.get(
    url=URL,
    params={"action": "query", "meta": "tokens", "type": "login", "format": "json"},
).json()["query"]["tokens"]["logintoken"]

# Login
login_response = S.post(
    URL,
    data={
        "action": "login",
        "lgname": WD_USER,
        "lgpassword": WD_PASS,
        "lgtoken": LOGIN_TOKEN,
        "format": "json",
    },
)

# Check if login was successful
if login_response.json()["login"]["result"] == "Success":
    print("Logged in.")
else:
    print("Login failed.")

CSRF_TOKEN = S.get(
    url=URL, params={"action": "query", "meta": "tokens", "format": "json"}
).json()["query"]["tokens"]["csrftoken"]

print(CSRF_TOKEN)
# Read the content of 'individuals.txt'
with open("individuals.txt", "r") as f:
    individuals_content = f.read()

# Edit the page 'Individuals' with the content of 'individuals.txt'
edit_response_individuals = S.post(
    URL,
    data={
        "action": "edit",
        "title": "Individuals",
        "text": individuals_content,
        "token": CSRF_TOKEN,
        "format": "json",
    },
)

# Check if the edit was successful
if edit_response_individuals.json().get("edit"):
    print("Individuals page edited successfully.")
else:
    print("Failed to edit Individuals page.")

# Read the content of 'proposals.txt'
with open("proposals.txt", "r") as f:
    proposals_content = f.read()

# Edit the page 'Proposals' with the content of 'proposals.txt'
edit_response_proposals = S.post(
    URL,
    data={
        "action": "edit",
        "title": "Proposals",
        "text": proposals_content,
        "token": CSRF_TOKEN,
        "format": "json",
    },
)

# Check if the edit was successful
if edit_response_proposals.json().get("edit"):
    print("Proposals page edited successfully.")
else:
    print("Failed to edit Proposals page.")
