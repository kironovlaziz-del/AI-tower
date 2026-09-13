# Uzbek NER model

Training data and scripts for the Uzbek NER model used by the Prompt
Firewall when the request language is `uz`.

## Layout

data/
uz_ner_train.spacy ← compiled spaCy training corpus
scripts/
build_dataset.py ← generates the synthetic seed dataset
compile_corpus.py ← converts JSONL to spaCy .spacy format
train.py ← trains and packages the model
## Workflow

```bash
cd backend
source .venv/bin/activate

# 1. Build the seed dataset (or replace with your own JSONL)
python -m ner_training.scripts.build_dataset

# 2. Compile to spaCy binary format
python -m ner_training.scripts.compile_corpus

# 3. Train (5-20 minutes on CPU for the seed dataset)
python -m ner_training.scripts.train

# 4. Enable in backend/.env
#    PROMPT_FIREWALL_NER_MODELS={"en":"en_core_web_sm","uz":"uz_ner_model"}Replacing the seed dataset

build_dataset.py produces a small synthetic seed — enough to prove
the pipeline end-to-end. For production quality, point compile_corpus
at a larger, manually labelled corpus in the same JSONL format:

{"text": "...", "entities": [[start, end, "LABEL"], ...]}

Data sources worth considering:

    UzNERCorpus — a small manually annotated corpus (~1k sentences).

    Wikipedia UZ dump — extract sentences, run a weak supervision
    model, then human-verify samples.

    Internal customer data — anonymised support tickets, chat logs.

Aim for at least 3,000–5,000 labelled sentences before expecting
production-grade accuracy on general text.
