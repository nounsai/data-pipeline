import pandas as pd
from pathlib import Path
from helper import *
from login import *
from time import strptime, strftime
from wikibaseintegrator.datatypes import Item, String, Time, Quantity, URL
from wikibaseintegrator.wbi_enums import ActionIfExists
from wikibaseintegrator.models import Qualifiers
from wikibaseintegrator.wbi_exceptions import MissingEntityException, ModificationFailed
import logging
from tqdm import tqdm
import copy


def main():
    # Set up logging
    logging.basicConfig(
        filename="log_file.log",
        level=logging.INFO,
        format="%(asctime)s:%(levelname)s:%(message)s",
    )

    # Resolve path to the data
    HERE = Path(__file__).parent.resolve()
    DATA = HERE.parent.joinpath("data").resolve()

    # Read the KG data
    try:
        kg1 = pd.read_csv(DATA.joinpath("KG_view1.csv"))
        kg2 = pd.read_csv(DATA.joinpath("KG_view2.csv"))
    except Exception as e:
        logging.error("Failed to read KG data: " + str(e))
        exit()

    kg_list = [kg1, kg2]
    proposals = list(set(kg1["subject"]))
    proposals.sort()
    properties_in_wikibase["Vote Reason"] = "P63"

    for kg in kg_list:
        individuals = list(set([a for a in kg["object"] if str(a).startswith("0x")]))
        individuals.sort()
        print("====== Adding triples for individuals =====")
        logging.info("====== Adding triples for individuals =====")

        for individual in tqdm(individuals):
            if individual == "0xbobatea":
                continue
            kg_subset = kg[kg["object"] == individual]
            wbi = WikibaseIntegrator(login=login_instance)
            try:
                individual_qid = items_on_wikibase[individual]
            except KeyError as ke:
                logging.error("KeyError encountered: " + str(ke))
                continue
            try:
                item = wbi.item.get(entity_id=individual_qid)
            except MissingEntityException as e:
                logging.error("MissingEntityException encountered: " + str(e))
                continue
            data = []
            for i, row in kg_subset.iterrows():
                try:
                    property_name = row["relation"]
                    object_name = row["subject"]
                    if property_name in item_properties:
                        if property_name in inverse_properties.keys():
                            if property_name != "Proposer":
                                new_qualifiers = Qualifiers()
                                new_qualifiers.add(
                                    Quantity(
                                        prop_nr=properties_in_wikibase["Vote Weight"],
                                        amount=int(row["weight"]),
                                    )
                                )
                                if row["reason"] != "Reason not provided":
                                    reason = row["reason"]
                                    if len(reason) > 2499:
                                        reason = reason[0:2400]
                                    new_qualifiers.add(
                                        String(
                                            prop_nr=properties_in_wikibase[
                                                "Vote Reason"
                                            ],
                                            value=reason.replace("\n", "-")
                                            .replace('"', "")
                                            .strip(),
                                        )
                                    )
                                data.append(
                                    Item(
                                        value=items_on_wikibase[object_name],
                                        prop_nr=properties_in_wikibase[
                                            inverse_properties[property_name]
                                        ],
                                        qualifiers=new_qualifiers,
                                    )
                                )
                            else:
                                data.append(
                                    Item(
                                        value=items_on_wikibase[object_name],
                                        prop_nr=properties_in_wikibase[
                                            inverse_properties[property_name]
                                        ],
                                    )
                                )
                    else:
                        logging.warning("Unexpected property name: " + property_name)
                except KeyError as ke:
                    logging.error("KeyError encountered: " + str(ke))
                    continue
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
            except Exception as e:
                logging.error("An unexpected error occurred: " + str(e))


if __name__ == "__main__":
    main()
