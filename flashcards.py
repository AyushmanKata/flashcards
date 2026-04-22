"""
flashcards.py — AI Flashcard Generator using Groq
--------------------------------------------------
Commands:
  python flashcards.py upload notes.txt       generate flashcards from a text file
  python flashcards.py topic "binary search"  generate flashcards from a topic name
  python flashcards.py quiz <deck>            quiz yourself on a saved deck
  python flashcards.py list                   list all saved decks
  python flashcards.py show <deck>            print all cards in a deck
"""

import os
import sys
import json
import random

from groq import Groq

# ── Config ────────────────────────────────────────────────────────────────────
MODEL       = "llama-3.3-70b-versatile"   # best free Groq model
DECKS_DIR   = "decks"                     # where .json flashcard files are saved
NUM_CARDS   = 10                          # cards to generate per run


# ── Groq call helper ──────────────────────────────────────────────────────────
def ask_groq(system: str, user: str) -> str:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system",  "content": system},
            {"role": "user",    "content": user},
        ],
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()


# ── Generate flashcards from text ─────────────────────────────────────────────
SYSTEM_PROMPT = f"""You are a flashcard generator for ECE students.
Given notes or a topic, produce exactly {NUM_CARDS} flashcards.

Return ONLY a valid JSON array, no explanation, no markdown fences.
Each card has exactly two keys: "q" (question) and "a" (answer).
Answers must be concise — 1 to 3 sentences max.

Example format:
[
  {{"q": "What is a stack?", "a": "A stack is a LIFO data structure where the last element added is the first removed."}},
  {{"q": "What does LIFO stand for?", "a": "Last In, First Out."}}
]"""


def generate_cards(content: str, deck_name: str) -> list[dict]:
    print(f"Generating {NUM_CARDS} flashcards for '{deck_name}'...")
    raw = ask_groq(SYSTEM_PROMPT, f"Generate flashcards for:\n\n{content}")

    # Strip markdown fences if model adds them anyway
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    cards = json.loads(raw)
    if not isinstance(cards, list) or not cards:
        raise ValueError("Model did not return a valid card list.")

    save_deck(deck_name, cards)
    print(f"Saved {len(cards)} cards → {deck_path(deck_name)}")
    return cards


# ── From uploaded file ────────────────────────────────────────────────────────
def from_file(filepath: str):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        sys.exit(1)

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.strip():
        print("File is empty.")
        sys.exit(1)

    # Use filename (without extension) as deck name
    deck_name = os.path.splitext(os.path.basename(filepath))[0]
    cards = generate_cards(content, deck_name)
    print_cards_preview(cards)


# ── From a topic name ─────────────────────────────────────────────────────────
def from_topic(topic: str):
    prompt = f"Create detailed, exam-ready flashcards on the topic: {topic}"
    cards  = generate_cards(prompt, topic.replace(" ", "_"))
    print_cards_preview(cards)


# ── Quiz mode ─────────────────────────────────────────────────────────────────
def quiz(deck_name: str):
    cards = load_deck(deck_name)
    if not cards:
        return

    random.shuffle(cards)
    score  = 0
    total  = len(cards)

    print(f"\nQuiz: {deck_name}  ({total} cards)")
    print("Press Enter to reveal answer. Type 'y' if you got it right.\n")
    print("─" * 50)

    for i, card in enumerate(cards, 1):
        print(f"\nQ {i}/{total}: {card['q']}")
        input("  → Press Enter to reveal...")
        print(f"A: {card['a']}")
        got_it = input("  Correct? (y/n): ").strip().lower()
        if got_it == "y":
            score += 1

    pct = int(score / total * 100)
    print(f"\n{'─'*50}")
    print(f"Score: {score}/{total}  ({pct}%)")

    if pct == 100:
        print("Perfect — you know this deck cold.")
    elif pct >= 70:
        print("Solid. Review the ones you missed.")
    else:
        print("Keep studying. Try again after reviewing your notes.")


# ── List all decks ────────────────────────────────────────────────────────────
def list_decks():
    if not os.path.exists(DECKS_DIR):
        print("No decks saved yet.")
        return

    files = [f for f in os.listdir(DECKS_DIR) if f.endswith(".json")]
    if not files:
        print("No decks saved yet.")
        return

    print(f"Saved decks ({len(files)}):")
    for f in sorted(files):
        name  = f.replace(".json", "")
        cards = load_deck(name)
        print(f"  {name}  ({len(cards)} cards)")


# ── Show all cards in a deck ──────────────────────────────────────────────────
def show_deck(deck_name: str):
    cards = load_deck(deck_name)
    if not cards:
        return
    print(f"\nDeck: {deck_name}  ({len(cards)} cards)\n{'─'*50}")
    for i, card in enumerate(cards, 1):
        print(f"\nQ{i}: {card['q']}")
        print(f"A:  {card['a']}")


# ── File helpers ──────────────────────────────────────────────────────────────
def deck_path(name: str) -> str:
    safe = name.replace(" ", "_")
    return os.path.join(DECKS_DIR, f"{safe}.json")

def save_deck(name: str, cards: list):
    os.makedirs(DECKS_DIR, exist_ok=True)
    with open(deck_path(name), "w") as f:
        json.dump(cards, f, indent=2)

def load_deck(name: str) -> list:
    path = deck_path(name)
    if not os.path.exists(path):
        # Try treating name as a direct path
        if os.path.exists(name):
            with open(name) as f:
                return json.load(f)
        print(f"Deck not found: {name}")
        print("Run: python flashcards.py list")
        return []
    with open(path) as f:
        return json.load(f)

def print_cards_preview(cards: list):
    print(f"\nFirst 3 cards:")
    for card in cards[:3]:
        print(f"  Q: {card['q']}")
        print(f"  A: {card['a']}")
        print()


# ── Entry point ───────────────────────────────────────────────────────────────
def usage():
    print("Usage:")
    print("  python flashcards.py upload <file.txt>     generate from uploaded notes file")
    print("  python flashcards.py topic 'binary search' generate from a topic")
    print("  python flashcards.py quiz <deck>           quiz yourself")
    print("  python flashcards.py list                  list all decks")
    print("  python flashcards.py show <deck>           print all cards in a deck")

if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        usage()
        sys.exit(1)

    cmd = args[0].lower()

    if cmd == "upload":
        if len(args) < 2:
            print("Usage: python flashcards.py upload <file.txt>")
        else:
            from_file(args[1])

    elif cmd == "topic":
        if len(args) < 2:
            print("Usage: python flashcards.py topic 'your topic'")
        else:
            from_topic(" ".join(args[1:]))

    elif cmd == "quiz":
        if len(args) < 2:
            print("Usage: python flashcards.py quiz <deck_name>")
        else:
            quiz(" ".join(args[1:]))

    elif cmd == "list":
        list_decks()

    elif cmd == "show":
        if len(args) < 2:
            print("Usage: python flashcards.py show <deck_name>")
        else:
            show_deck(" ".join(args[1:]))

    else:
        print(f"Unknown command: {cmd}")
        usage()
