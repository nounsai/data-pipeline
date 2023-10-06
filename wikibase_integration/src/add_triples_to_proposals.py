import pandas as pd
from pathlib import Path
from helper import *
from login import *
from time import strptime, strftime
from wikibaseintegrator.datatypes import Item, String, Time, Quantity, URL
from wikibaseintegrator.wbi_enums import ActionIfExists
from wikibaseintegrator.models import Qualifiers
from wikibaseintegrator.wbi_exceptions import ModificationFailed
from tqdm import tqdm
import json
import logging


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
        return

    kg_list = [kg1, kg2]
    proposals = list(set(kg1["subject"]))
    proposals.sort()

    for kg in kg_list:
        print("====== Adding triples to proposals =====")
        logging.info("====== Adding triples to proposals =====")
        for proposal in tqdm(proposals):
            try:
                kg_subset = kg[kg["subject"] == proposal]

                proposal_qid = items_on_wikibase[proposal]
                wbi = WikibaseIntegrator(login=login_instance)
                item = wbi.item.get(entity_id=proposal_qid)
                data = []
                for i, row in kg_subset.iterrows():
                    property_name = row["relation"]
                    object_name = row["object"]
                    if pd.isna(object_name):
                        continue

                    if property_name in item_properties:
                        if property_name in {
                            "Supported By",
                            "Opposed By",
                            "Abstained By",
                        }:
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
                                        prop_nr=properties_in_wikibase["Vote Reason"],
                                        value=reason.replace("\n", "-")
                                        .replace('"', "")
                                        .strip(),
                                    )
                                )
                            data.append(
                                Item(
                                    value=items_on_wikibase[object_name],
                                    prop_nr=properties_in_wikibase[property_name],
                                    qualifiers=new_qualifiers,
                                )
                            )
                        else:
                            data.append(
                                Item(
                                    value=items_on_wikibase[object_name],
                                    prop_nr=properties_in_wikibase[property_name],
                                )
                            )

                    elif property_name in string_properties:
                        if "\n" in object_name:
                            object_name = object_name.replace("\n", " --- ")
                        data.append(
                            String(
                                value=object_name,
                                prop_nr=properties_in_wikibase[property_name],
                            )
                        )
                    elif property_name in date_properties:
                        time_struct = strptime(row["object"], "%Y-%m-%d")

                        wikidata_time = strftime("+%Y-%m-%dT00:00:00Z", time_struct)
                        data.append(
                            Time(
                                wikidata_time,
                                prop_nr=properties_in_wikibase[property_name],
                            )
                        )
                    elif property_name in quantity_properties:
                        data.append(
                            Quantity(
                                amount=float(object_name),
                                prop_nr=properties_in_wikibase[property_name],
                            )
                        )
                        if property_name == "Id":
                            data.append(
                                URL(
                                    value=f"https://nouns.wtf/vote/{str(object_name)}",
                                    prop_nr="P21",  # Nouns URL property
                                )
                            )

                    else:
                        print(property_name)
                    continue

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

            except KeyError as ke:
                logging.error(f"KeyError encountered: {str(ke)}")
                continue
            except ModificationFailed as e:
                logging.error("Failed to write item: " + str(e))
            except Exception as e:
                logging.error(f"An unexpected error occurred: {str(e)}")


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
