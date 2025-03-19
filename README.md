# triple-to-text-alignment

This repo contains a set of scripts that were used to create the [wikidata references triple-to-text alignment](https://huggingface.co/datasets/sven-h/wikidata_reference) dataset.


| Script | Purpose |
|----------|----------|
| extract_triple_reference_pairs.py   | Extracts triple-reference pairs for each of the Wikidata properties from a given SPARQL endpoint.   |
| subj_label_map_generator.py   | Extracts entity labels for entities in the previous step. This step is done separately for efficiency.   |
| url_domain_analysis.py | Extracts the domain names from the URLs and group URLs by domain |
| domain_language_detection.py | Detects the content language for each domain |
| web_page_retrieval.py | Download the pages from English language content domains |
| llm_triple_text_alignments.py | For each triple, extracts the text span that corresponds to it from the URL page content and validate if the extracted text entails the given triple |
| dataset_statistics.py | Calculates some dataset statistics |

# LLM-based text span selection and validation 
Here are the prompts, including the instructions and few-shots for in-context learning for the two LLM-based tasks of selecting the text span corresponding to a triple and validating the selected text span that entails the given triple that are used in `llm_triple_text_alignments.py`.

## Prompt for text span selection for a given text

```
You are a useful assistant. Given a fact in the form of (subject, relation, object)
and a passage of text, your task is to read the text carefully and extract the 
sentence(s) that express or entail the given fact in the text. You should extract 
the text as is from the text (extractive) without doing any changes to the text. 
Finally, if the subject or object is reffered to using a pronoun (he,she,them,it, 
etc.), replace it with the corresponding proper noun. If none of the sentences 
entail the given fact, just write an empty string. 

IMPORTANT: 
(1) As much as possible, extract complete coherent sentence(s). 
(2) Do not write any explanations or additional text, just write only the text ext
racted from the passage.
(3) If you come up with alternatives, please write the most suitable one (only a single concise text)

Here are two examples:

# Fact:
subject:Boston
relation: population
object: 675,647

# Passage: 
Boston is the capital and most populous city in the Commonwealth of Massachusetts in the United States. The city serves as the cultural and financial center of New England, a region of the Northeastern United States. Boston has an area of 48.4 sq mi (125 km2) an
d a population of 675 647 as of the 2020 census, making it the third-largest city in the Northeastern United States after New York City and Philadelphia. The larger Greater Boston metropolitan statistical area has a population of 4.9 million as of 2023, making it the largest in New England and the eleventh-largest in the country.

# Text Evidence: Boston has an area of 48.4 sq mi (125 km2) and a population of 675,647 as of the 2020 census, making it the third-largest city in the Northeastern United States after New York City and Philadelphia.
===

Human: # Fact:
subject:Javascript
relation: has use
object: web development

# Passage: JavaScript | Social Sciences & Humanities Open Marketplace
Skip to main content
Report an issue
Browse
Contribute
About
Search
Home
/
Tools & services
/
JavaScript
Tool or service
JavaScript
Copy to clipboard
JavaScript, often abbreviated as JS, is a high-level, interpreted pro
gramming language. It is a language which is also characterized as dynamic, weakly typed, prototype-based and multi-paradigm. Alongside HTML and CSS, JavaScript is one of the three core technologies of the World Wide Web. JavaScript ena
bles interactive web pages and thus is an essential part of web applications. The vast majority of websites use it, and all major web browsers have a dedicated JavaScript engine to execute it.
Go to Tool or service
Details
Properties

Access
Terms Of Use
Free
Open Source
Categorisation
Activity
Web Development
Programming
Actors
Creator
N/A
Sources
Source
:
TAPoR
Media

# Text Evidence: Alongside HTML and CSS, JavaScript is one of the three core technologies of the World Wide Web.
===

# Fact:
subject: {wikidata_subject}
relation: {wikidata_relation}
object: {wikidata_object}

# Passage: 
{web_page_content}

# Text Evidence:

```

## Prompt for validating the extracted text for text entailment

```
You are a useful assistant. Given a fact in the form of (subject, relation, object) and
a text, your task is to read the text carefully and check if the text entails the given 
fact or if the given fact can be extracted from the text. If the fact can be extracted 
from the text, write TRUE and FALSE otherwise. 

IMPORTANT: Please double check the following points. 
(1) You should only consider the text in "Text Evidence" and no additional context or
background knowledge.
(2) If the text does not consist of proper fluent sentence(s), write FALSE. 
(3) If the subject or object is not explicity mentioned in text, write FALSE. 
(4) If the given relation is not explictly described in text, write FALSE. 
(5) Do not make any assumptions about coreferences for pronouns such as it, he, she,
etc unless they are explicitly mentioned in text (3) If there is any uncertanity, write FALSE.

# Fact:
subject: Boston
relation: population
object: 675,647

# Text Evidence:
Boston has an area of 48.4 sq mi (125 km2) and a population of 675,647 as of the 2020 
census, making it the third-largest city in the Northeastern United States after 
New York City and Philadelphia.

# Validation:
Fluent Sentences(s): TRUE
Subject mentioned in Text: TRUE
Relation mentioned in Text: TRUE
Object mentioned in Text: TRUE
Fact Entailed By Text: TRUE
===

# Fact:
subject:Javascript
relation: has use
object: web development

# Text Evidence:
Alongside HTML and CSS, JavaScript is one of the three core technologies for web development.

# Validation:
Fluent Sentences(s): TRUE
Subject mentioned in Text: TRUE
Relation mentioned in Text: TRUE
Object mentioned in Text: TRUE
Fact Entailed By Text: TRUE
===

Human: # Fact:
subject:Madrid
relation: capital of
object: Spain

# Text Evidence:
The first historical document about the existence of an established settlement in
Madrid dates from the Muslim age.

# Validation:
Fluent Sentences(s): TRUE
Subject mentioned in Text: TRUE
Relation mentioned in Text: FALSE
Object mentioned in Text: FALSE
Fact Entailed By Text: FALSE
===

Human: # Fact:
subject:Martin Moebius
relation: honorific prefix
object: Doctor

# Text Evidence:
Martin Moebius (Dr.; Gau Labor Office, Saxony)

# Validation:
Fluent Sentences(s): FALSE
Subject mentioned in Text: TRUE
Relation mentioned in Text: FALSE
Object mentioned in Text: TRUE
Fact Entailed By Text: FALSE
===

# Fact:
subject:IBM
relation: chief executive officer
object: Arvind Krishna

# Text Evidence:
Arvind Krishna has co-authored 15 patents.International Business Machines Corporation 
(IBM) is a multinational technology company from the United States that makes and sells 
software, computer hardware, infrastructure services, and consulting services.

# Validation:
Fluent Sentences(s): TRUE
Subject mentioned in Text: TRUE
Relation mentioned in Text: FALSE
Object mentioned in Text: TRUE
Fact Entailed By Text: FALSE
===

# Fact:
subject: {subject}
relation: {relation}, 
object: {object}

# Text Evidence:
{selected text span}

# Validation:
```