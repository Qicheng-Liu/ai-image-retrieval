# server.py
from pathlib import Path
from flask import Flask, render_template, request, jsonify
from ImageRetrieval.image_retrieval import (
    gpt_agent_with_indexed_images,
    load_indexed_images,
)

ROOT = Path(__file__).parent.resolve()

app = Flask(__name__, static_folder="static", template_folder="templates")

@app.route("/", methods=["GET"])
def render_index_page():
    return render_template("index.html")

@app.route("/imageretrieval", methods=["POST"])
def sent_keyword():
    data = request.get_json(silent=True) or {}
    keyword = (data.get("keyword") or "").strip()
    profile_labels = data.get("profile_labels", [])  # list[str]

    # Be explicit about where the index lives in your repo
    index_path = ROOT / "ImageRetrieval" / "image_index.json"
    jpg_paths = load_indexed_images(index_path=str(index_path))

    response = gpt_agent_with_indexed_images(
        keyword, jpg_paths, profile_labels=profile_labels
    )
    return jsonify(response)

if __name__ == "__main__":
    # Local dev only; Render uses gunicorn to import `app`
    app.run(host="0.0.0.0", port=5000, debug=True)
