#!/usr/bin/env python3
"""
Lightweight Web Annotation Tool for NER
Dùng thay thế Doccano khi có dependency issues
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

try:
    from flask import Flask, render_template, request, jsonify, send_from_directory
    from flask_cors import CORS
except ImportError:
    print("⚠️  Flask not installed. Install: pip install flask flask-cors")
    exit(1)


app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_DIR = Path("./data/training")
ANNOTATIONS_DIR = UPLOAD_DIR / "annotations"
ANNOTATIONS_DIR.mkdir(parents=True, exist_ok=True)

# Entity labels
LABELS = {
    "PERSON": "#1890ff",
    "YEAR": "#ff7a45",
    "RELATION_SPOUSE": "#13c2c2",
    "RELATION_PARENT": "#52c41a",
    "RELATION_SIBLING": "#722ed1",
}


class AnnotationStore:
    def __init__(self, texts_file: str, output_file: str):
        self.texts_file = texts_file
        self.output_file = output_file
        self.texts = self._load_texts()
        self.annotations = self._load_annotations()
        self.current_index = 0

    def _load_texts(self) -> List[Dict]:
        """Load texts from JSONL file"""
        texts = []
        if os.path.exists(self.texts_file):
            with open(self.texts_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        texts.append(json.loads(line))
        return texts

    def _load_annotations(self) -> Dict:
        """Load existing annotations"""
        annotations = {}
        if os.path.exists(self.output_file):
            with open(self.output_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        annotations[data["id"]] = data
        return annotations

    def get_current_text(self) -> Optional[Dict]:
        """Get current text to annotate"""
        if self.current_index < len(self.texts):
            text_data = self.texts[self.current_index]
            text_id = text_data.get("id", self.current_index)
            return {
                "id": text_id,
                "text": text_data.get("text", ""),
                "index": self.current_index,
                "total": len(self.texts),
                "annotated": text_id in self.annotations,
                "annotation": self.annotations.get(text_id),
            }
        return None

    def save_annotation(self, text_id: str, entities: List[Dict]) -> bool:
        """Save annotation for current text"""
        if 0 <= self.current_index < len(self.texts):
            self.annotations[text_id] = {
                "id": text_id,
                "text": self.texts[self.current_index].get("text", ""),
                "label": entities,
            }
            self._persist_annotations()
            return True
        return False

    def _persist_annotations(self):
        """Save annotations to file"""
        with open(self.output_file, "w", encoding="utf-8") as f:
            for text_id, annotation in self.annotations.items():
                f.write(json.dumps(annotation, ensure_ascii=False) + "\n")

    def next_text(self):
        """Move to next text"""
        if self.current_index < len(self.texts) - 1:
            self.current_index += 1

    def prev_text(self):
        """Move to previous text"""
        if self.current_index > 0:
            self.current_index -= 1

    def get_stats(self) -> Dict:
        """Get annotation statistics"""
        return {
            "total": len(self.texts),
            "annotated": len(self.annotations),
            "remaining": len(self.texts) - len(self.annotations),
            "progress_percent": int(
                (len(self.annotations) / len(self.texts) * 100)
                if self.texts
                else 0
            ),
        }


# Initialize annotation store
store = AnnotationStore(
    texts_file=UPLOAD_DIR / "sample_vietnamese_texts.jsonl",
    output_file=ANNOTATIONS_DIR / "vietnamese_annotations.jsonl",
)


@app.route("/")
def index():
    """Main annotation interface"""
    return render_template("annotation.html", labels=LABELS)


@app.route("/api/current")
def get_current():
    """Get current text to annotate"""
    current = store.get_current_text()
    stats = store.get_stats()
    return jsonify({**current, **stats})


@app.route("/api/save", methods=["POST"])
def save_annotation():
    """Save annotation"""
    data = request.json
    text_id = data.get("id")
    entities = data.get("entities", [])

    success = store.save_annotation(text_id, entities)
    stats = store.get_stats()

    return jsonify({"success": success, "stats": stats})


@app.route("/api/next", methods=["POST"])
def next_text():
    """Move to next text"""
    store.next_text()
    current = store.get_current_text()
    return jsonify(current)


@app.route("/api/prev", methods=["POST"])
def prev_text():
    """Move to previous text"""
    store.prev_text()
    current = store.get_current_text()
    return jsonify(current)


@app.route("/api/stats")
def get_stats():
    """Get annotation statistics"""
    return jsonify(store.get_stats())


if __name__ == "__main__":
    print("🚀 Annotation tool starting on http://localhost:8001")
    print(f"📄 Texts: {store.get_stats()['total']} loaded")
    app.run(host="0.0.0.0", port=8001, debug=False)
