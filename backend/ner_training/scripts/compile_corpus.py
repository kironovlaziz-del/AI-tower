"""Convert the JSONL dataset to spaCy's binary .spacy format."""

import json
import random
from pathlib import Path

import spacy
from spacy.tokens import DocBin

random.seed(42)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
JSONL_PATH = DATA_DIR / "uz_ner_train.jsonl"
TRAIN_PATH = DATA_DIR / "train.spacy"
DEV_PATH = DATA_DIR / "dev.spacy"


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def make_docbin(nlp, entries):
    db = DocBin()
    for entry in entries:
        doc = nlp.make_doc(entry["text"])
        ents = []
        for start, end, label in entry.get("entities", []):
            span = doc.char_span(start, end, label=label,
                                 alignment_mode="contract")
            if span is not None:
                ents.append(span)
        try:
            doc.ents = ents
            db.add(doc)
        except ValueError:
            continue
    return db


def main():
    if not JSONL_PATH.exists():
        raise SystemExit(f"{JSONL_PATH} missing")
    entries = load_jsonl(JSONL_PATH)
    random.shuffle(entries)
    split = int(len(entries) * 0.8)
    train_entries = entries[:split]
    dev_entries = entries[split:]
    nlp = spacy.blank("xx")
    make_docbin(nlp, train_entries).to_disk(TRAIN_PATH)
    make_docbin(nlp, dev_entries).to_disk(DEV_PATH)
    print(f"Train: {len(train_entries)} -> {TRAIN_PATH}")
    print(f"Dev:   {len(dev_entries)} -> {DEV_PATH}")


if __name__ == "__main__":
    main()
