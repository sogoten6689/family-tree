#!/usr/bin/env python3
"""
Convert Doccano JSON annotations to CONLL 2003 format

Usage:
    python convert_doccano_to_conll.py \
        --input vietnamese_annotations.jsonl \
        --output vietnamese_genealogy_ner.conll2003
"""

import json
import argparse
from pathlib import Path
from typing import List, Tuple


def parse_doccano_entities(text: str, entities: List[dict]) -> List[Tuple[str, str]]:
    """
    Convert Doccano entity format to token-level CONLL IOB2 tags.

    Doccano format:
    {
        "id": 1,
        "text": "Ông Nguyễn Văn An sinh năm 1945",
        "label": [
            [0, 3, "PERSON"],
            [4, 17, "PERSON"],
            [26, 30, "YEAR"]
        ]
    }

    CONLL 2003 IOB2 format:
    Ông B-PERSON
    Nguyễn I-PERSON
    Văn I-PERSON
    An I-PERSON
    sinh O
    năm O
    1945 B-YEAR

    """

    if not entities:
        # No entities - all tokens are O
        tokens = text.split()
        return [(token, "O") for token in tokens]

    # Sort entities by start position
    entities = sorted(entities, key=lambda x: x[0])

    # Build character-to-label mapping
    char_labels = {}
    for start, end, label in entities:
        # Mark character positions with entity info
        entity_type = label if label != "O" else "O"
        for i in range(start, end):
            char_labels[i] = entity_type

    # Tokenize by whitespace
    tokens = []
    token_starts = []

    pos = 0
    for token in text.split():
        # Find actual position in original text
        idx = text.find(token, pos)
        if idx >= 0:
            token_starts.append(idx)
            pos = idx + len(token)
        else:
            token_starts.append(pos)
        tokens.append(token)

    # Assign IOB2 tags to tokens
    result = []
    for i, token in enumerate(tokens):
        start_pos = token_starts[i]

        # Get label from first character of token
        if start_pos in char_labels:
            label = char_labels[start_pos]
        else:
            # Check if any character in token has a label
            token_end = start_pos + len(token)
            token_labels = set()
            for pos in range(start_pos, token_end):
                if pos in char_labels:
                    token_labels.add(char_labels[pos])

            if token_labels and "O" not in token_labels:
                label = list(token_labels)[0]
            else:
                label = "O"

        # IOB2 tagging: first token of entity = B-, rest = I-
        if label != "O":
            if i == 0:
                tag = f"B-{label}"
            elif result and result[-1][1].startswith("B-") and result[-1][1].split("-")[1] == label:
                tag = f"I-{label}"
            elif i > 0 and result[-1][1].startswith("I-") and result[-1][1].split("-")[1] == label:
                tag = f"I-{label}"
            else:
                tag = f"B-{label}"
        else:
            tag = "O"

        result.append((token, tag))

    return result


def convert_doccano_to_conll(input_file: str, output_file: str) -> None:
    """Convert Doccano JSONL to CONLL 2003 format."""

    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    output_lines = []
    sentence_count = 0
    token_count = 0

    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            data = json.loads(line)
            text = data.get("text", "").strip()
            entities = data.get("label", [])

            if not text:
                continue

            # Convert to CONLL
            token_tags = parse_doccano_entities(text, entities)

            # Write tokens
            for token, tag in token_tags:
                output_lines.append(f"{token} {tag}")
                token_count += 1

            # Add blank line to separate sentences
            output_lines.append("")
            sentence_count += 1

    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

    print(f"✅ Converted {sentence_count} sentences, {token_count} tokens")
    print(f"📄 Output: {output_path}")
    print("\nFirst 10 lines:")
    for line in output_lines[:10]:
        if line:
            print(f"  {line}")
        else:
            print("  ---")


def main():
    parser = argparse.ArgumentParser(
        description="Convert Doccano JSON annotations to CONLL 2003 format"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Input Doccano JSONL file",
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output CONLL 2003 file",
    )

    args = parser.parse_args()
    convert_doccano_to_conll(args.input, args.output)


if __name__ == "__main__":
    main()
