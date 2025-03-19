import os
import glob
import json
import re
from tqdm import tqdm
import tldextract
from collections import Counter, defaultdict

def domain_name_analysis(directory: str) -> Counter:
    file_pattern = os.path.join(directory, "*_ref_data.jsonl")
    url_pattern = r'^(?:https?:\/\/)?(?:www\.)?([^\/:]+)'

    file_paths = glob.glob(file_pattern)
    domain_url_map = defaultdict(set)
    for file_path in tqdm(file_paths, total=len(file_paths), desc=f"Processing files: "):
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    ref_url = record['refURL']
                    match = re.search(url_pattern, ref_url)
                    if match:
                        domain_name = match.group(1)
                        domain_url_map[domain_name].add(ref_url)
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON in file {file_path}: {e}")

    domain_name_counter = Counter()
    for domain_name in domain_url_map:
        domain_name_counter[domain_name] = len(domain_url_map[domain_name])

    tld_counter = Counter()
    tld_domain_name_map = defaultdict(set)
    for domain_name, _ in domain_name_counter.most_common():
        extracted = tldextract.extract(domain_name)
        tld = extracted.suffix
        tld_counter[tld] += 1
        tld_domain_name_map[tld].add(domain_name)

    return domain_name_counter, domain_url_map, tld_counter, tld_domain_name_map

def save_key_value_map(domain_url_map, output_file: str, key_label: str = "key", value_label: str = "values"):
    with open(output_file, "w") as f:
        for domain, urls in domain_url_map.items():
            record = {key_label: domain, value_label: list(urls)}
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

def save_counter_to_json(counter: Counter, output_file: str):
    counts_list = [[domain, count] for domain, count in counter.most_common()]
    with open(output_file, "w") as f:
        json.dump(counts_list, f, indent=1, ensure_ascii=False)

def main():
    
    directory_path = "..."
    domain_name_counter, domain_url_map, tld_counter, tld_domain_name_map = domain_name_analysis(directory_path)
    total_count = sum(len(urls) for urls in domain_url_map.values())
    print(f"distinct URLs: {total_count}\ndistinct domain names: {len(domain_name_counter)}")

    save_key_value_map(domain_url_map, ".../domain_url_map.jsonl", key_label="domain", value_label="urls")
    save_counter_to_json(domain_name_counter, ".../domain_name_counts.json")

    save_key_value_map(tld_domain_name_map, ".../tld_to_domain.jsonl", key_label="tld", value_label="domains")
    save_counter_to_json(tld_counter, ".../tld_counts.json")

if __name__ == "__main__":
    main()