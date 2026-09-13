"""Train a spaCy NER model for Uzbek and package it."""

import random
from pathlib import Path

import spacy
from spacy.training import Example
from spacy.util import minibatch, compounding
from spacy.tokens import DocBin

random.seed(42)

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "output"
MODEL_DIR = OUT_DIR / "uz_ner_model"
TRAIN_PATH = DATA_DIR / "train.spacy"
DEV_PATH = DATA_DIR / "dev.spacy"

N_ITER = 30
DROPOUT = 0.35
BATCH_SIZES = compounding(4.0, 32.0, 1.001)


def load_docs(path, nlp):
    db = DocBin().from_disk(path)
    return list(db.get_docs(nlp.vocab))


def evaluate(nlp, examples):
    scorer = nlp.evaluate(examples)
    # spaCy 3.8 returns a Scorer that behaves like a dict; use key access
    # rather than attribute access to stay compatible across versions.
    return {
        "ents_p": scorer["ents_p"],
        "ents_r": scorer["ents_r"],
        "ents_f": scorer["ents_f"],
    }

def main():
    if not TRAIN_PATH.exists() or not DEV_PATH.exists():
        raise SystemExit("Training files missing. Run compile_corpus first.")

    nlp = spacy.blank("xx")
    ner = nlp.add_pipe("ner", last=True)

    train_docs = load_docs(TRAIN_PATH, nlp)
    dev_docs = load_docs(DEV_PATH, nlp)

    for doc in train_docs:
        for ent in doc.ents:
            ner.add_label(ent.label_)

    train_examples = [Example(nlp.make_doc(d.text), d) for d in train_docs]
    dev_examples = [Example(nlp.make_doc(d.text), d) for d in dev_docs]

    optimizer = nlp.initialize(lambda: train_examples)

    print(f"Training on {len(train_examples)} examples, dev on {len(dev_examples)}")
    for i in range(N_ITER):
        random.shuffle(train_examples)
        losses = {}
        batches = minibatch(train_examples, size=BATCH_SIZES)
        for batch in batches:
            nlp.update(batch, sgd=optimizer, drop=DROPOUT, losses=losses)
        if (i + 1) % 5 == 0:
            m = evaluate(nlp, dev_examples)
            print(f"iter {i+1:3d}  loss {losses.get('ner', 0):.2f}  "
                  f"P {m['ents_p']:.3f}  R {m['ents_r']:.3f}  F {m['ents_f']:.3f}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    nlp.to_disk(MODEL_DIR)
    print(f"\nModel written to {MODEL_DIR}")


if __name__ == "__main__":
    main()
