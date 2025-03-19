import json
import hashlib
import os
import glob
import pandas as pd
import json
import random
import concurrent.futures
from tqdm import tqdm
from langchain_community.chat_models import ChatLiteLLM
from langchain.globals import set_debug
from langchain.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain.schema import HumanMessage, SystemMessage
from dotenv import load_dotenv
from litellm import Timeout
import time


class LllUtils:

    extraction_prompt = ChatPromptTemplate.from_messages([
        ("user", "# Fact:\nsubject:{subject}\nrelation: {relation}\nobject: {object}\n# Passage: {passage}"),
        ("assistant", "# Text Evidence: {text_evidence}\n===")]
    )

    verification_prompt = ChatPromptTemplate.from_messages([
        ("user", "# Fact:\nsubject:{subject}, relation: {relation}, object: {object}\n\n# Text Evidence: \n{text_evidence}"),
        ("assistant", "# Validation:\nFluent Sentences(s): {fluent_v}\nSubject mentioned in Text: {subject_v}\nRelation mentioned in Text: {relation_v}\nObject mentioned in Text: {object_v}\nFact Entailed By Text: {entailment}\n===")]
    )

    def __init__(self, extraction_examples_path=None, verification_example_path=None):
        load_dotenv()
        file_dir = os.path.dirname(os.path.abspath(__file__))
        if not extraction_examples_path:
            extraction_examples_path = os.path.join(file_dir, 'fewshots','text_evidence_extract_fewshots.json') 
        if not verification_example_path:
            verification_example_path = os.path.join(file_dir, 'fewshots', 'text_evidence_verification_fewshots.json') 
        with open(extraction_examples_path) as in_file:
            self.extraction_examples = json.load(in_file)
        with open(verification_example_path) as in_file:
            self.verification_examples = json.load(in_file)

    def get_text_extraction_prompt(self):
        few_shot_prompt = FewShotChatMessagePromptTemplate(
            example_prompt=LllUtils.extraction_prompt,
            examples=self.extraction_examples,
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a useful assistant. Given a fact in the form of (subject, relation, object) and a passage of text, your task is to read the text carefully and extract the sentence(s) that express or entail the given fact in the text. You should extract the text as is from the text (extractive) without doing any changes to the text. Finally, if the subject or object is reffered to using a pronoun (he,she,them,it, etc.), replace it with the corresponding proper noun. If none of the sentences entail the given fact, just write an empty string. IMPORTANT: (1) As much as possible, extract complete coherent sentence(s). (2) Do not write any explanations or additional text, just write only the text extracted from the passage. (2) If you come up with alternatives, please write the most suitable one (only a single concise text)"),
            few_shot_prompt,
            ("user", "# Fact:\nsubject:{subject}\nrelation: {relation}\nobject: {object}\n# Passage: {passage}"),
        ])
        return prompt
    
    def get_text_verification_prompt(self):
        few_shot_prompt = FewShotChatMessagePromptTemplate(
            example_prompt=LllUtils.verification_prompt,
            examples=self.verification_examples,
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a useful assistant. Given a fact in the form of (subject, relation, object) and a text, your task is to read the text carefully and check if the text entails the given fact or if the given fact can be extracted from the text. If the fact can be extracted from the text, write TRUE and FALSE otherwise. IMPORTANT: Please double check the following points. (1) You should only consider the text in \"Text Evidence\" and no additional context or background knowledge.\n(2) If the text does not consist of proper fluent sentence(s), write FALSE. (2) If the subject or object is not explicity mentioned in text, write FALSE. (2) If the given relation is not explictly described in text, write FALSE. (3) Do not make any assumptions about coreferences for pronouns such as it, he, she, etc unless they are explicitly mentioned in text (3) If there is any uncertanity, write FALSE."),
            few_shot_prompt,
            ("user", "# Fact:\nsubject:{subject}, relation: {relation}, object: {object}\n\n{text_evidence}"),
        ])
        return prompt   
    

    def extract_evidence_text(self, subj: str, rel: str, obj: str, text: str) -> str:
        llm_chat = ChatLiteLLM(model=os.environ['LLM_MODEL_ID'],  api_key=os.environ['LLM_API_KEY'], temperature=0, max_retries=1)
        prompt = self.get_text_extraction_prompt()
        chain = prompt | llm_chat
        input_data = {"subject": subj, "relation": rel, "object": obj, "passage": text}
        response = chain.invoke(input_data)
        return response.content
    
    def validate_fact_text(self, subj: str, rel: str, obj: str, text: str) -> str:
        llm_chat = ChatLiteLLM(model=os.environ['LLM_MODEL_ID'], api_key=os.environ['LLM_API_KEY'], temperature=0, max_retries=1)
        prompt = self.get_text_verification_prompt()
        chain = prompt | llm_chat
        input_data = {"subject": subj, "relation": rel, "object": obj, "text_evidence": text}
        response = chain.invoke(input_data)
        return response.content
    
llm_utils = LllUtils()
global_timeout_count = 0
global_timeout_threshold = 25

def secure_hash(url: str) -> str:
    return hashlib.sha3_256(url.encode()).hexdigest()

def triple_to_hash(triple: dict):
    tr_str = "".join([triple['subjLabel'], triple['prop'], triple['objLabel'], triple['page_id']])
    tr_hash = secure_hash(tr_str)
    return tr_hash

def extract_triple_text_span_and_validate(triple: dict):
    page_id  = triple['page_id']
    base_dir = ""
    page_content_path = base_dir + f"/text/{page_id}.txt"
    try:
        with open(page_content_path, 'r') as file:
            page_content = file.read()
        if len(page_content) > 150000:
            page_content =  page_content[:150000]
        text_evidence = llm_utils.extract_evidence_text(triple['subjLabel'], triple['prop'], triple['objLabel'], page_content)
        triple['text_span'] = text_evidence.replace("# Text Evidence:", "").strip()

        if triple['text_span'] != '':
            validation_result = llm_utils.validate_fact_text(triple['subjLabel'], triple['prop'], triple['objLabel'], text_evidence) 
            validated = False
            if "true" in validation_result.lower() and not "false" in validation_result.lower():
                validated = True
            triple['validation'] = validated
            triple['detailed_validation'] = validation_result
        else:
            triple['validation'] = False
            triple['detailed_validation'] = ''
        return triple
    except Timeout as timeout_ex:
        print(f"ERROR: {timeout_ex}")
        global_timeout_count += 1
        if global_timeout_count > global_timeout_threshold:
            raise timeout_ex
        time.sleep(300)
        return None
    except Exception as ex:
        print(f"ERROR: {ex}")
        return None

def load_triples(directory: str, prop_labels: dict, qid_to_label: dict) -> set:
    file_pattern = os.path.join(directory, "*_ref_data.jsonl")
    triples = list()
    for filepath in glob.glob(file_pattern):
        prop_id = filepath.split("/")[-1].replace("_ref_data.jsonl", "")
        if prop_id in prop_labels:
            prop_label = prop_labels[prop_id]
        else:
            continue
        with open(filepath, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    record['prop'] = prop_label
                    subj = record['subj']
                    if "http://" in record['obj']:
                        continue
                    if "objLabel" in record:
                        pass
                    else:
                        continue
                    if subj in qid_to_label:
                        record['subjLabel'] = qid_to_label[subj]
                    else:
                        continue
                    triples.append(record)
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON in file {filepath}: {e}")
    return triples

def dump_jsonl(data: list, file_path: str) -> None:
    if os.path.exists(file_path):
        os.rename(file_path, file_path+".backup")
    with open(file_path, 'w', encoding='utf-8') as file:
        for item in data:
            json_line = json.dumps(item, ensure_ascii=False)
            file.write(json_line + '\n')

def main():
    data_base_dir = ""
    page_info_path = data_base_dir + "page_retrieval_info.jsonl"
    q_id_to_label_path = data_base_dir + "qid_to_label_map.jsonl"
    property_label_path = data_base_dir + "property_label.tsv"
    old_outputs = [data_base_dir + "triples_text_span_validation-1.jsonl", 
                   data_base_dir + "triples_text_span_validation-2.jsonl"]
    output_file = data_base_dir + "triples_text_span_validation.jsonl"
    rel_ref_data_path  = "..."

    prop_df = pd.read_csv(property_label_path, sep='\t')
    prop_labels = prop_df.set_index('prop')['label'].to_dict()
    print(f"{len(prop_labels)} property labels loaded!")

    qid_to_label = dict()
    with open(q_id_to_label_path) as in_file:
        for line in in_file:
            data = json.loads(line)
            qid_to_label.update(data)
    print(f"{len(qid_to_label)} entity labels loaded!")

    ref_url_to_page_id = dict()
    with open(page_info_path) as in_file:
        for line in in_file:
            page_url, page_id, lang, _, page_size  = json.loads(line)
            if lang == 'en' and page_size > 250:
                ref_url_to_page_id[page_url] = page_id

    print(f"{len(ref_url_to_page_id)} pages with English conent and page size > 250 chars loaded.")

    triples = load_triples(rel_ref_data_path, prop_labels, qid_to_label)
    print(f"{len(triples)} triples filtered loaded.")

    triples_w_content = []
    for tr in triples:
        ref_url = tr['refURL']
        if ref_url in ref_url_to_page_id:
            tr['page_id'] = ref_url_to_page_id[ref_url]
            triples_w_content.append(tr)
    print(f"{len(triples_w_content)} triples after URL filtering.")

    completed = set()
    for old_output in old_outputs:
        with open(old_output) as in_file:
            completed.update({triple_to_hash(json.loads(line)) for line in in_file})
    print(f"{len(completed)} completed triples!")

    triples_w_content = [tr for tr in triples_w_content if triple_to_hash(tr) not in completed]
    print(f"{len(triples_w_content)} triples to process.")
    random.shuffle(triples_w_content)

    text_span_validation = list()
    checkpoint_interval = 100
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(extract_triple_text_span_and_validate, tr) for tr in triples_w_content]
        print("submitted all jobs to the executor ...")
        total = len(futures)
        pbar = tqdm(total=total, desc="Processing ...")     
        count = 0
        valid_count = 0
        for future in concurrent.futures.as_completed(futures):
            count += 1
            pbar.update(1)
            result = future.result()
            if result:
                text_span_validation.append(result)
                if result['validation'] == True:
                    valid_count += 1
            if count % checkpoint_interval == 0:
                dump_jsonl(text_span_validation, output_file)
            
    dump_jsonl(text_span_validation, output_file)

if __name__ == "__main__":
    main()
