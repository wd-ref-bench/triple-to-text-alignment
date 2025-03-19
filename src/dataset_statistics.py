from SPARQLWrapper import SPARQLWrapper, JSON
import concurrent.futures
from tqdm import tqdm
import json
import os
import glob
from collections import Counter


def count_triples(directory: str) -> set:
    file_pattern = os.path.join(directory, "*_ref_data.jsonl")
    triple_count = 0
    qids = set()
    urls = set()
    for filepath in glob.glob(file_pattern):
        with open(filepath, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    qids.add(record['subj'])
                    if 'objLabel' in record:
                        qids.add(record['obj'])
                    urls.add(record['refURL'])
                    triple_count += 1
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON in file {filepath}: {e}")
    return triple_count, len(qids), len(urls)

def lang_summary(doman_to_lang_file: str):
    with open(doman_to_lang_file) as in_file:
        lang_counter = Counter()
        domain_lang_counter = Counter()
        for line in in_file:
            try:
                _, count, lang, _, _, _ = json.loads(line)
            except Exception as ex:
                print(f"ERROR: {line}")
            lang_counter[lang] += count
            domain_lang_counter[lang] += 1

    
    print(f"# of languages: {len(lang_counter)}")
    print(domain_lang_counter.most_common(10))
    print(lang_counter.most_common(10))

def validation_summary():

    data_base_dir = ""
    old_outputs = [data_base_dir + "triples_text_span_validation-1.jsonl", 
                data_base_dir + "triples_text_span_validation-2.jsonl",
                data_base_dir + "triples_text_span_validation-3.jsonl",
                data_base_dir + "triples_text_span_validation-4.jsonl",
                data_base_dir + "triples_text_span_validation-5.jsonl",
                data_base_dir + "triples_text_span_validation-6.jsonl",
                data_base_dir + "triples_text_span_validation-7.jsonl"]
    
    output_data = []
    for old_output in old_outputs:
        with open(old_output) as in_file:
            data = [json.loads(line) for line in in_file]
            output_data += data
    print(len(output_data))

    no_text = 0
    valid = 0
    qids = set()
    relations = set()
    for out in output_data:
        if out['text_span'].strip() == "":
            no_text += 1
        if out['validation'] == True:
            valid += 1
            qids.add(out['subj'])
            qids.add(out['obj'])
            relations.add(out['prop'])
    print(f"no text: {no_text}")
    print(f"valid: {valid}")
    print(f"entity: {len(qids)}")
    print(f"relations: {len(relations)}")

def main():
    # triple_count, entity_count, url_count = count_triples("/Users/nandana/Documents/src/public/kgBasedRE/tr_align")
    # print(f"triples: {triple_count}")
    # print(f"entities: {entity_count}")
    # print(f"URLs: {url_count}")
    validation_summary()

if __name__ == "__main__":
    main()