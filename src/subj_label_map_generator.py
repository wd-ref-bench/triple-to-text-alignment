from SPARQLWrapper import SPARQLWrapper, JSON
import concurrent.futures
from tqdm import tqdm
import json
import os
import glob

def load_subj_set(directory: str) -> set:
    subj_set = set()
    file_pattern = os.path.join(directory, "*_ref_data.jsonl")
    
    for filepath in glob.glob(file_pattern):
        with open(filepath, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    if "subj" in record:
                        subj_set.add(record["subj"])
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON in file {filepath}: {e}")
    return subj_set

def dump_jsonl(data: dict, file_path: str) -> None:
    with open(file_path, 'w', encoding='utf-8') as file:
        for key, value in data.items():
            json_line = json.dumps({key: value}, ensure_ascii=False)
            file.write(json_line + '\n')

def query_entity_label(sparql_endpoint: str, qid: str) -> str:
    query = "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> select distinct ?label where { <http://www.wikidata.org/entity/" + qid + ">  rdfs:label ?label . FILTER(LANG(?label) = \"en\") }"
    sparql = SPARQLWrapper(sparql_endpoint)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    sparql.setTimeout(30)
    try:
        results = sparql.query().convert()
        if "results" in results and "bindings" in results["results"]:
            for binding in results["results"]["bindings"]:
                if 'label' in binding:
                    if binding['label']["value"].strip() == '':
                        return None
                    else:
                        return binding['label']["value"]
    except Exception as ex:
        print(f"Error: {ex}\nQuery: {query}")
    return None

def main():
    
    directory_path = "..."
    sparql_endpoint  = "..."
    subjects = load_subj_set(directory_path)
    print(f"Collected {len(subjects)} unique 'subj' values.")

    qid_list = list(subjects)
    qid_to_label_map = {}

    output_file = "qid_to_label_map.jsonl"
    checkpoint_interval = 50000

    def worker(sparql_endpoint, qid):
        label = query_entity_label(sparql_endpoint, qid)
        return (qid, label)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(worker, qid) for qid in qid_list]
        total = len(futures)
        pbar = tqdm(total=total, desc="Processing ...")
        count = 0
        #with tqdm(total=total, desc="Processing QIDs") as pbar:
        for future in concurrent.futures.as_completed(futures):
            qid, label = future.result()
            #print(label)
            if label:
                qid_to_label_map[qid] = label
            pbar.update(1)
            count += 1
            if count % checkpoint_interval == 0:
                dump_jsonl(qid_to_label_map, output_file)

    dump_jsonl(qid_to_label_map, output_file)
    print(f"Processing complete with {len(qid_to_label_map)} entities.")
    pbar.close()


if __name__ == "__main__":
    main()