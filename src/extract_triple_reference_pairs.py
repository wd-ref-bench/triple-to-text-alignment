import argparse
from SPARQLWrapper import SPARQLWrapper, JSON
from tqdm import tqdm
import json
import logging

logging.basicConfig(level=logging.INFO)

prop_ref_query = """PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX pr: <http://www.wikidata.org/prop/reference/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?subj ?obj ?objLabel ?refURL 
 WHERE {
  ?subj <http://www.wikidata.org/prop/P_num_> ?statement .
  ?statement <http://www.wikidata.org/prop/statement/P_num_> ?obj;
       prov:wasDerivedFrom ?ref . 
  OPTIONAL {?obj rdfs:label ?objLabel . FILTER(LANG(?objLabel) = "en") }
  ?ref pr:P854 ?refURL .
}
LIMIT 5000"""

def extract_triple_reference_pairs(sparql_endpoint: str, start_index: int, end_index: int, output_dir: str):

    sparql = SPARQLWrapper(sparql_endpoint)
    with open("error.txt", "w") as error_out:
        indices = list(range(start_index, end_index))
        for i in tqdm(indices, total=len(indices), desc=f"Processing properties: "):
            try:
                query = prop_ref_query.replace("_num_", str(i))
                sparql.setQuery(query)
                sparql.setReturnFormat(JSON)
                sparql.setTimeout(50)
                results = sparql.query().convert()
                results_data = []
                if "results" in results and "bindings" in results["results"]:
                    for binding in results["results"]["bindings"]:
                        subj = binding['subj']["value"].replace("http://www.wikidata.org/entity/","")
                        obj = binding['obj']["value"].replace("http://www.wikidata.org/entity/","")
                        ref_data = {"subj": subj, "obj": obj}
                        if 'objLabel' in binding:
                            ref_data['objLabel'] = binding['objLabel']["value"]
                        ref_url = binding['refURL']["value"]
                        ref_data['refURL'] = ref_url
                        results_data.append(ref_data)
                logging.info(f"{len(results_data)} triple-pairs extracted for property P{i}.")
                if results_data:
                    with open(f"{output_dir}/P{i}_ref_data.jsonl", "w") as out_file:
                        for item in results_data:
                            out_file.write(f"{json.dumps(item, ensure_ascii=False)}\n")
            except Exception as ex:
                error_out.write(f"P{i}: {str(ex)}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spraql_endpoint", required=True, type=str, help="The SPARQL endpoint URL.")
    parser.add_argument("--output_dir", required=True, type=str, help="Directory where the output will be stored.")
    parser.add_argument("--start_index", required=True, type=int, help="The starting index for the operation.")
    parser.add_argument("--end_index", required=True, type=int, help="The ending index for the operation.")
    args = parser.parse_args()

if __name__ == "__main__":
    main()





