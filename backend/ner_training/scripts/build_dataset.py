"""
Build a small synthetic Uzbek NER dataset for smoke-testing the model
pipeline. Real production NER requires a human-annotated corpus - see
ner_training/README.md for sources.

Uzbek is agglutinative: entity mentions appear with case suffixes
attached ("Toshkent" -> "Toshkentga", "Toshkentda", "Toshkentdan"). The
generator emits suffixed variants AND uses templates that do NOT carry
their own suffixes, so the span covers the full "Toshkentga" token.
"""

import json
import random
from pathlib import Path

random.seed(42)

OUT_PATH = Path(__file__).resolve().parents[1] / "data" / "uz_ner_train.jsonl"


PERSONS = [
    "Aziz Karimov", "Dilnoza Yusupova", "Bekzod Rahimov", "Nilufar Saidova",
    "Javohir Toshmatov", "Malika Ergasheva", "Sardor Nazarov",
    "Zulfiya Abdullayeva", "Otabek Mirzayev", "Kamola Ismoilova",
]

ORGS = [
    "UzAuto Motors", "Uztelecom", "Tashkent City", "Uzum Market",
    "Payme", "Click", "Humans", "UzCard", "Beeline Uzbekistan",
    "TBC Bank",
]

LOCATIONS = [
    "Toshkent", "Samarqand", "Buxoro", "Andijon", "Namangan",
    "Farg'ona", "Nukus", "Xiva", "Qarshi", "Termiz",
]

DATES = [
    "2026-yil 1-yanvar", "2026-yil 15-fevral", "o'tgan hafta",
    "kecha", "bugun", "ertaga", "3-mart kuni",
]

MONEY = [
    "1 000 000 so'm", "500 000 so'm", "12 million so'm",
    "3 500 000 so'm", "100 dollar", "50 yevro",
]

PERSON_SUFFIXES = ["", "ning", "ga", "ni"]
ORG_SUFFIXES = ["", "ning", "ga", "da"]
LOCATION_SUFFIXES = ["", "ga", "da", "dan", "ning"]
DATE_SUFFIXES = [""]
MONEY_SUFFIXES = [""]

SUFFIXES_BY_LABEL = {
    "PERSON": PERSON_SUFFIXES,
    "ORG": ORG_SUFFIXES,
    "LOCATION": LOCATION_SUFFIXES,
    "DATE": DATE_SUFFIXES,
    "MONEY": MONEY_SUFFIXES,
}

BANKS = {
    "PERSON": PERSONS,
    "ORG": ORGS,
    "LOCATION": LOCATIONS,
    "DATE": DATES,
    "MONEY": MONEY,
}

# Templates must NOT include case suffixes on slots - the suffix is added
# during generation so the entity span covers the full token.
TEMPLATES = [
    ("{PERSON} {ORG} kompaniyasida ishlaydi.", ["PERSON", "ORG"]),
    ("{ORG} {LOCATION} shahrida yangi ofis ochdi.", ["ORG", "LOCATION"]),
    ("{PERSON} {LOCATION} {DATE} jo'nadi.", ["PERSON", "LOCATION", "DATE"]),
    ("{ORG} {MONEY} miqdorida shartnoma imzoladi.", ["ORG", "MONEY"]),
    ("{PERSON} {DATE} {ORG} bilan uchrashdi.", ["PERSON", "DATE", "ORG"]),
    ("Yangi mahsulot {MONEY} sotiladi.", ["MONEY"]),
    ("{PERSON} {LOCATION} tug'ilgan.", ["PERSON", "LOCATION"]),
    ("{ORG} rahbari {PERSON} edi.", ["ORG", "PERSON"]),
    ("{DATE} {ORG} aksiyalari oshdi.", ["DATE", "ORG"]),
    ("{PERSON} {MONEY} miqdorida kredit oldi.", ["PERSON", "MONEY"]),
    ("{LOCATION} va {LOCATION} o'rtasida yangi poyezd qatnovi ochildi.",
     ["LOCATION", "LOCATION"]),
    ("{ORG} {PERSON} bosh direktor etib tayinladi.", ["ORG", "PERSON"]),
    ("{PERSON} {LOCATION} {ORG} vakili sifatida qatnashdi.",
     ["PERSON", "LOCATION", "ORG"]),
    ("Shartnoma summasi {MONEY} etib belgilandi.", ["MONEY"]),
    ("{PERSON} {LOCATION} yashaydi.", ["PERSON", "LOCATION"]),
    ("{ORG} {LOCATION} faoliyat yuritadi.", ["ORG", "LOCATION"]),
]


def build_entry(template: str, labels: list):
    text = template
    entities = []
    for label in labels:
        placeholder = "{" + label + "}"
        if placeholder not in text:
            continue
        base = random.choice(BANKS[label])
        suffix = random.choice(SUFFIXES_BY_LABEL.get(label, [""]))
        value = base + suffix
        idx = text.index(placeholder)
        text = text.replace(placeholder, value, 1)
        entities.append([idx, idx + len(value), label])
    if "{" in text:
        return None
    entities.sort(key=lambda x: x[0])
    return {"text": text, "entities": entities}


def main():
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    entries = []
    for _ in range(3000):
        template, labels = random.choice(TEMPLATES)
        entry = build_entry(template, labels)
        if entry is None or entry["text"] in seen:
            continue
        seen.add(entry["text"])
        entries.append(entry)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    print(f"Wrote {len(entries)} examples to {OUT_PATH}")


if __name__ == "__main__":
    main()
