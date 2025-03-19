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
import hashlib
import os


def secure_hash(url: str) -> str:
    return hashlib.sha3_256(url.encode()).hexdigest()

def domain_lang_detection_worker(url: str, output_dir: str) -> Tuple[str, str, int]:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
    try:
        page_id = secure_hash(url)
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        page_text = BeautifulSoup(response.text, 'html.parser').get_text(separator='\n', strip=True)
        lang = detect(page_text)
        length = len(page_text)
        html_path = output_dir + f"html/{page_id}.html"
        text_path = output_dir + f"text/{page_id}.txt"
        with open(html_path, "w") as out_file:
            out_file.write(response.text)
        with open(text_path, "w") as out_file:
            out_file.write(page_text)
        return url, page_id, lang, None, length
    except Exception as ex:
        return url, page_id, None, str(ex), 0
    
def dump_jsonl(data: list, file_path: str) -> None:
    if os.path.exists(file_path):
        os.rename(file_path, file_path+".backup")
    with open(file_path, 'w', encoding='utf-8') as file:
        for item in data:
            json_line = json.dumps(item, ensure_ascii=False)
            file.write(json_line + '\n')

def main():
    base_dir = ""
    output_dir = ""
    domain_name_lang_path = base_dir + "domain_to_lang.jsonl"
    domain_name_map_path = base_dir + "domain_url_map.jsonl"
    output_file = base_dir + "page_retrieval_info.jsonl"
    english_domain_names = []
    with open(domain_name_lang_path) as in_file:
        for line in in_file:
            domain_name, page_count, lang, _, _, _  = json.loads(line)
            if lang == 'en':
                english_domain_names.append(domain_name)
    print(f"{len(english_domain_names)} domain names with English conent loaded.")
    
    english_page_urls = list()
    with open(domain_name_map_path) as in_file:
        for line in in_file:
            data = json.loads(line)
            if data['domain'] in english_domain_names:
                english_page_urls += data['urls']
    random.shuffle(english_page_urls)
    print(f"{len(english_page_urls)} urls with english content loaded.")

    page_info_list = list()
    checkpoint_interval = 10000
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        futures = [executor.submit(domain_lang_detection_worker, url, output_dir) for url in english_page_urls]
        print("submitted all jobs to the executor ...")
        total = len(futures)
        pbar = tqdm(total=total, desc="Processing ...")     
        count = 0
        for future in concurrent.futures.as_completed(futures):
            count += 1
            url, page_id, lang, error, length = future.result()
            page_info_list.append([url, page_id, lang, error, length])
            pbar.update(1)
            if count % checkpoint_interval == 0:
                dump_jsonl(page_info_list, output_file)


    dump_jsonl(page_info_list, output_file)
    pbar.close()

if __name__ == "__main__":
    main()