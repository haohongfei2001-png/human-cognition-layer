---
license: cc-by-4.0
---
# Morables-PD Dataset

## Description

This repository contains a Public Domain, cc-by-4.0 release of the data used in "<span style="font-variant: small-caps;">Morables</span> : A Benchmark for Assessing Abstract Moral Reasoning in LLMs with Fables", presented at EMNLP 2025.

This parallel release only contains the title-fable-moral triples within Public Domain, with the annotator verified morals. 

Each fable has an associated free-text moral, sourced from various websites and books (detailed in the paper). It is intended for use in NLP text understanding and moral inference tasks.

## Contents
- **File Format**: JSON 
- **Number of Records**: 308
- **Content of Each Entry**:
  - `alias`: (str) Unique ID of the fable
  - `title`: (str) Title of the Fable
  - `story`: (str) Content of the fable / short story
  - `moral`: (str) Moral of the story
- **List of files**:
  - `Morables-PD.json` : story/fable/moral triples, restricted to Open Domain translations;

## Citing this dataset

If you use this dataset in your research, please cite the main reference paper:

```
@inproceedings{marcuzzo2025morables,
      title={Morables: A Benchmark for Assessing Abstract Moral Reasoning in LLMs with Fables}, 
      author={Marcuzzo, Matteo and Zangari, Alessandro and Albarelli, Andrea and Camacho-Collados, Jose and Pilehvar, Mohammad Taher},
      year={2025},
      booktitle={Proceedings of EMNLP},
      publisher={Association of Computational Linguistics},
}
```