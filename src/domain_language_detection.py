import json
import random
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from langdetect import detect
import concurrent.futures
from collections import deque, Counter
from typing import Tuple, List
import re

MAX_ATTEMPT_COUNT = 25
QUEUE_SIZE = 7
SAME_LANG_COUNT = 5

def domain_lang_detection_worker(domain_name: str, urls: List[str]) -> Tuple[str, str, float, Counter]:
    random.shuffle(urls)
    url_count = len(urls)
    urls = urls[:MAX_ATTEMPT_COUNT]
    lang_queue = deque(maxlen=QUEUE_SIZE)
    lang_detected = None
    total_counter = Counter()
    error_counter = Counter()
    page_sizes = []
    for url in urls:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
        try:
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            page_text = BeautifulSoup(response.text, 'html.parser').get_text(separator=' ', strip=True)
            page_sizes.append(len(page_text))
            lang = detect(page_text)
            # print(url)
            # print(lang)
            lang_queue.append(lang)
            total_counter[lang] += 1
            lang_counter = Counter(lang_queue)
            max_lang, max_count = lang_counter.most_common(1)[0]
            if max_count == SAME_LANG_COUNT:
                lang_detected = max_lang
                break
        except Exception as ex:
            # print(ex)
            err_str = str(ex)
            code_match = re.search(r"\b\d{3}\b", err_str)
            if code_match:
                error_counter[f"err-{code_match.group()}"] += 1
            else:
                error_counter["err"] += 1
    
    # print(f"urls: {len(urls)}")
    # print(f"dect: {lang_detected}")
    # print(f"total: {total_counter}")
    # print(f"lang: {lang_counter}")
    # print(f"queue: {lang_queue}")

    if not lang_detected:
        if len(total_counter) > 0:
            max_lang, max_count = total_counter.most_common(1)[0]
            lang_detected = max_lang
        else:
            lang_detected = "unknown"

    avg_page_size = 0
    if page_sizes:
        avg_page_size = sum(page_sizes) / len(page_sizes)

    return domain_name, url_count, lang_detected, avg_page_size, total_counter, error_counter


def dump_jsonl(data: list, file_path: str) -> None:
    data = sorted(data, key=lambda x: x[1], reverse=True)
    with open(file_path, 'w', encoding='utf-8') as file:
        for domain_name, url_count, lang, avg_page_size, total_counter, error_counter in data:
            json_line = json.dumps([domain_name, url_count, lang, round(avg_page_size,2), [[lang_c, count] for lang_c, count in total_counter.most_common()], [[err, count] for err, count in error_counter.most_common()]], ensure_ascii=False)
            file.write(json_line + '\n')


def main():

    domain_name_counts_path = ".../data/domain_name_counts.json"
    domain_name_map_path = ".../data/domain_url_map.jsonl"
    output_file = "../data/domain_to_lang.jsonl"
    domain_name_counts = None
    with open(domain_name_counts_path) as in_file:
        domain_name_counts = json.load(in_file)
    print(f"{len(domain_name_counts)} domain name counts loaded.")

    domain_name_to_urls = dict()
    with open(domain_name_map_path) as in_file:
        for line in in_file:
            data = json.loads(line)
            domain_name_to_urls[data['domain']] = data['urls']
    print(f"{len(domain_name_to_urls)} domain name to urls mappings loaded.")

    domain_to_lang = list()
    checkpoint_interval = 1000
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = list()
        for domain_name, count in domain_name_counts:
            futures.append(executor.submit(domain_lang_detection_worker, domain_name, domain_name_to_urls[domain_name]))
        total = len(futures)
        pbar = tqdm(total=total, desc="Processing ...")
        count = 0
        for future in concurrent.futures.as_completed(futures):
            count += 1
            domain_name, url_count, lang_detected_res, avg_page_size, total_counter, error_counter = future.result()
            domain_to_lang.append([domain_name, url_count, lang_detected_res, avg_page_size, total_counter, error_counter])
            pbar.update(1)
            if count % checkpoint_interval == 0:
                dump_jsonl(domain_to_lang, output_file)

    dump_jsonl(domain_to_lang, output_file)
    pbar.close()

if __name__ == "__main__":
    main()