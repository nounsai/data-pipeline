This repository contains a series of scripts to connect knowledge graphs in .csv files to a Wikibase.

## Generating KG data from Nouns Proposals

Firstly, make sure you have installed all the needed packages in your Python environment by running:

```
pip install -r src/requirements.txt
python -m spacy download en
```

First we need to fetch the Nouns proposals from thesubgraph. 

```
cd src
python get_nouns_proposal.py 
```

If the proposals.json file exists in the ./data/ directory, we pull the latest version under nouns_proposals_new.json

Once the proposals are fetched, we use GPT-4 to generate the KG. We create two csv files - KG_view1.csv that contains information about each proposal ID and KG_view2.csv that contains the voting related information.

To run the get_KG script, we first need to obtain OpenAI API and store it as OPENAI_API_KEY in a .env file saved in src folder. This file is added to the gitignore, so the information can be preserved from sharing to public.

```
python get_KG.py
```

The script automatically overrides the existing KG data inside ./data/ folder and renames the nouns_proposals_new.json to nouns_proposals.json. 

This way, we can automatically fetch the new proposals and update the knowledge graphs.

## Building Wikibase on Extracted KG

It currently points to a Wikibase hosted on wikibase.cloud, the Nouns Dev Wikibase: https://nounsdev.wikibase.cloud/. 

Wikibase is a software to host editable knowledge graphs, similar to Wikidata, which are displayed in an user friendly interface. 

It can be run as a standalone software, with full customizability. 
For those working with open data and without deep needs of early customization, Wikibase.cloud provides a free hosting service.
The code here has been developed for a wikibase.cloud instance, but could be used for any Wikibase by changing the configuration in the [src/helper.py]("./src/helper.py") file. 

The code for integration is written in Python and based on the framework for Wikibase editing [WikibaseIntegrator](https://github.com/LeMyst/WikibaseIntegrator).

It runs under the unique name assumption, where each unique name in the knowledge graph is assigned to a different entity/relation. 

## Starting the integration 

The task of transposing the Nouns knowledge graph to a Wikibase includes three major steps: 

1. Creation of the properties in the Wikibase (the edge types, used to link entities)
2. Creation of the entities in the Wikibase
3. Update of the triples in the database that describe the different entities of interest 

The first 2 tasks are taken by the `create_relations_and_items.py` script, where task 3 is divided in 2, one for Nouns Proposals (`add_triples_to_proposals.py`) and another one for Nouns Individuals (the different ETH wallets in the Nouns community; `add_triples_to_individuals.py`).


### Configuration

Before starting to run the scripts for the first time, make sure the configuration in the  [src/helper.py]("./src/helper.py") file is correct. 
It contains 3 basic URLs, one for the MediaWiki API, one for the SPARQL endpoint and another for the wikibase itself:
 
```
wikibase_prefix = "nounsdev"
wbi_config["MEDIAWIKI_API_URL"] = f"https://{wikibase_prefix}.wikibase.cloud/w/api.php"
wbi_config[
    "SPARQL_ENDPOINT_URL"
] = f"https://{wikibase_prefix}.wikibase.cloud/query/sparql"
wbi_config["WIKIBASE_URL"] = f"https://{wikibase_prefix}.wikibase.cloud"
```

For simplification, the script is using a username and a password hardcoded in the `src/login.py`. 
This file should never be committed to the git version control system.
Also make sure the username and password refer to an existing user in the Wikibase.
The `src/login.py` file should look like this: 

```
WD_USER = "YourUserName"
WD_PASS = "y0urP4ssw0rd"
```

## First run of the scripts

**Note**: this bit does not apply for the current Wikibase installation, where the initial information has been updated already.

Before the first run of the scripts, some bits of information need to be manually edited. 
Particularly, the relations in the database are identified by PIDs, alphanumeric identifiers that look like P[0-9]*, e.g. "P3", "P23" and so on. 

While most relations in the current Wikibase are created by script, some have been created manually, and thus require hard-coding (or refactoring of the code). 

Look for and substitute in the codebase the following properties for the IDs on your database: 

* "P6" - The "instance of" property, used for categorizing the entities in the Wikibase by type, present on most items. 
* "P15" - The property for the numeric Nouns ID for each proposal 
* "P21" - The property for the Nouns https://github.com/LeMyst/WikibaseIntegrator/blob/4f2bcee7d1a869d651bd6ed4bea2f7134c16657d/wikibaseintegrator/models/claims.py#L51URL of the proposal

Besides substituting these PIDs, the installation in a new Wikibase also needs to take into account  and substitute in the code 3 different QIDs: 

* "Q1" - The "node type" item, used as base value for the "instance of" property. 
* "Q2" - The item for the concept of a "Proposal"
* "Q8" - The concept for an individual. 


After these PIDs and QIDs are updated, the code is almost ready to roll. 
You will need now to assign an entity type for each of the properties you want to include in the knowledge graph. 
This is done by updating sets in the `helper.py` file. 

There is one set for each entity type, and these sets are loaded as Python global variables. 
**Note**: Every time a new property is needed, you will have to curate it here, so the script knows how to add it to the Wikibase. 
There are 4 base sets: `item_properties`, `date_properties`, `string_properties` and `quantity_properties`. 

Besides the sets, there are 2 dictionaries that also need to be manually curated, one called `inverse_properties` and another one called `relation_to_range_mapping`. 
The `inverse_properties` dictionary contains the inverse name for some properties in the knowledge graph. 
It is needed for the Wikibase to duplicate some of the triples in the inverse direction, so they are shown both in the item for the Proposal and the item for each of the Individuals. 
The `relation_to_range_mapping` dictionary is needed for creating different items in the Wikibase with the correct "instance of" value. This is important for proper categorization and retrieval of items. 

## Updates of the database 

### Understanding and running the `create_relations_and_items.py` script

The `create_relations_and_items.py` is a master script to create the basic structure of the platform. 
**Note**:This script needs to be run every time there is an update of the knowledge graphs `KG_view1.csv` and `KG_view2.csv` 

It starts by adding some hard-coded properties, namely the "Vote Weight" and "Inverse Type" relations. 
Then it proceeds to adding to the Wikibase the items for "Proposal" and the items for the different range types cataloged in the `relation_to_range_mapping` dict in the `helper.py` file. 

After this scaffolding, the code will run 3 functions for each of the knowledge graphs, one to add all the different relations, one to add all the items for the proposals and finally another one to create all other kinds of entities from the "object" column in the graph.
These are creating with a type (e.g. "Individual", "Status" or "Property Type") based on the `relation_to_range_mapping` dict. 

The script needs to be run from the command line, e.g. 

```
cd src 
python3 create_relations_and_items.py
```

**Note**: Some errors might appear when running the script, due to the time taken for the database to update all its different parts. 
For example, the code knows which properties and items currently exist by running SPARQL queries. 
The SPARQL endpoint might take considerable time to update, sometimes in the range of hours for Wikibase.cloud. 

### Adding triples to the Wikibase 

After the basic structure has been created, now it is time to add the triples to the items for Proposals and Individuals.
The "triple" is the basic unit of knowledge in a knowledge graph, and almost all edges in the knowledge graph are added as triples in the knowledge base. 
The only exception is when additional information is present, for example in the case of the vote weights for KG2. 
These are added in a format called a "qualifier", the Wikibase implementation of reification (statements about statements).

**Note**:The 2 scripts, `add_triples_to_individuals.py` and `add_triples_to_proposals.py` both depend on the creation of relations and entities in the previous step and thus also require waiting for the database to complete the update of all its parts. 

As some properties are handled in special ways, with modification of the values or adding qualifiers, there are some hardcoded ifelse statements that need to be changed when new properties are added to the graph. 

Other than that, to update the graph, one needs only running in whatever order:

```
python3 add_triples_to_individuals.py
python3 add_triples_to_proposals.py
```

The default behavior of the graph is to replace all the existing statements with the new ones.
This behavior is set by the `action_if_exists` parameter, present in the snippet `item.claims.add(data, action_if_exists=ActionIfExists.REPLACE_ALL)`.
Different behaviors can be selected, and if that is desired the reader is referred to the [WikibaseIntegrator documentation](https://github.com/LeMyst/WikibaseIntegrator/blob/4f2bcee7d1a869d651bd6ed4bea2f7134c16657d/wikibaseintegrator/models/claims.py#L51).


## Setting up the "Proposals" and "Individuals pages

The Wikibase contains structured data alongside documentation pages. 
To produce a nice visualization of the core entities in the Nouns Wikibase, two pages were added, one for "Individuals" and one for "Proposals".

These pages contain each a different table in Wiki Markup detailing the entities. 

These pages need to be updated manually as there is not any simple way, to date, to update programatically a documentation page of an Wikibase.
To facilitate the process, the [create_wiki_tables.py](./src/create_wiki_tables.py) script generates two .txt documents containing the source code for the pages: [individuals.txt](individuals.txt) and [proposals.txt](proposals.txt).

After generating the files, one just needs to go to one of the source pages, click on "Edit" and substitute the source code for the new and updated version:

  * https://nounsdev.wikibase.cloud/wiki/Proposals
  * https://nounsdev.wikibase.cloud/wiki/Individuals