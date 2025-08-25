import os, json, yaml
from openai import OpenAI

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def load_indexed_images(index_path="image_index.json"):
    full_path = os.path.join(os.path.dirname(__file__), index_path)
    with open(full_path, 'r') as f:
        return json.load(f)


def gpt_agent_with_indexed_images(keyword, jpg_paths, profile_labels=None):
    # Build an ordered ID → path map and a numbered archive string
    id_to_path = {i: p for i, p in enumerate(jpg_paths, start=1)}
    indexed_string = "\n".join(f"[{i}] {p}" for i, p in id_to_path.items())

    safe_labels = [s for s in (profile_labels or []) if isinstance(s, str) and s.strip()]
    labels_only = ", ".join(safe_labels) or "None"

    system_prompt = system_prompt = f"""
Forget all previous context.

You are a Professional PSW Assistant with expert-level knowledge in occupational therapy and daily living support.

CLIENT PROFILE LABELS (soft constraints; prefer strongly when selecting images)
{labels_only}

The following archive is the ONLY source of truth. Each line shows an ID and the exact image path:
{indexed_string}

OBJECTIVE
- Start from the user's input keyword (exactly: {keyword}).
- Generate exactly 5 additional support-relevant keywords that best capture the intent of the input keyword.
  * Be domain-specific (e.g., conditions, activities, environments, equipment, strategies, routines, safety).
  * Each generated keyword must be distinct, specific, and 1–3 words.
  * Do NOT repeat the input keyword or output generic terms (e.g., "image", "photo", "misc").
  * If profile labels are present, prefer keywords that align with those labels (exact wording or close synonym).
  * When labels exist, at least 3 of the 5 generated keywords MUST align with the labels.

MATCHING & RANKING RULES (LABELS ARE MOST IMPORTANT)
- Recommend ONLY images that appear in the numbered archive above.
- For each of the 5 generated keywords (EXCLUDE the original input keyword), search the archive paths.
- Treat hyphens/underscores/spaces as equivalent; match is case-insensitive.
- EXPANSION (matching only; do NOT output these terms):
  * For each generated keyword, derive up to 3 close variants (lemma/singular/plural, common synonyms, clinical shorthand).
  * Match against (keyword OR any variant). Variants are only for matching, not for YAML keys.

SCORING (higher is better):
  LABEL SIGNALS
  - +4 if the path contains ANY profile label text in a leaf folder or filename segment.
  - +3 if the path contains ANY profile label text anywhere else.
  - +1 for each ADDITIONAL distinct profile label matched (beyond the first), up to +2 extra.

  KEYWORD SIGNALS
  - +2 if the (keyword OR its variant) appears in a leaf folder or filename segment.
  - +1 if it appears anywhere else.

  TIE-BREAKERS (apply in order):
  1) More distinct profile labels matched (count).
  2) Generated keyword (or variant) present in a leaf segment.
  3) Shorter full path length.
  4) Alphabetical order.

SELECTION
- For each generated keyword, select the highest-scoring items.
- Per keyword, return 3–6 unique IDs when that many matches exist; otherwise return all available (minimum 1).
- If labels are present and ≥1 label-matching item exists for that keyword, the TOP item for that keyword MUST include a label match.
- Encourage diversity within each keyword's list: prefer items that match different labels and/or different parent folders when scores are close.

MANDATORY OUTPUT RULES (NO RAW PATHS)
- Output only archive IDs (integers). Never write or retype path strings.
- IDs must come from the bracketed numbers shown in the archive listing.

OUTPUT
- Output MUST be valid YAML only. No code fences, no prose, no extra keys.

YAML FORMAT (exact keys, exact order):
Input Keyword: "{keyword}"
keywords:
  <generated_keyword_1>:
    - id: <archive_id_integer>
    - id: <archive_id_integer>
  <generated_keyword_2>:
    - id: <archive_id_integer>

CONSTRAINTS
- Top-level keys MUST be exactly (and in this order): "Input Keyword" and "keywords".
- "Input Keyword" MUST equal "{keyword}" (case and spacing preserved).
- Under "keywords", include exactly 5 generated keywords (input keyword excluded).
- For each generated keyword, list 3–6 IDs when available; otherwise list all available (minimum 1).
- IDs MUST exist in the archive list and must not repeat within the same keyword.
- If labels were provided:
  * ≥3 of the 5 generated keywords MUST align with the labels (exact or close synonym).
  * For each of those label-aligned keywords, the first recommended ID MUST match at least one label.

SELF-CHECK BEFORE OUTPUT
- Confirm there are exactly 5 unique generated keyword keys.
- Confirm each generated keyword lists the required number of IDs (3–6 when available; otherwise ≥1).
- Confirm every "id" exists in the archive list.
- If labels were provided and matches exist, confirm:
  * ≥3 label-aligned generated keywords.
  * The first item under each label-aligned keyword matches at least one label.
- Confirm there are no raw path strings anywhere in the YAML.
"""




    response = client.chat.completions.create(
        model="gpt-4.1-nano-2025-04-14",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Start."}
        ],
        temperature=0,
        max_tokens=800
    )

    # Parse the YAML returned from GPT
    raw = response.choices[0].message.content

    try:
        parsed = yaml.safe_load(raw)
        if not isinstance(parsed, dict):
            raise ValueError("YAML root is not a mapping")

        # Basic shape guards
        if "Input Keyword" not in parsed:
            parsed["Input Keyword"] = keyword
        if not isinstance(parsed.get("keywords"), dict):
            parsed["keywords"] = {}

        # Convert ids → exact paths
        def ids_to_paths(parsed_keywords, id_to_path):
            out = {}
            for kw, items in (parsed_keywords or {}).items():
                paths = []
                if isinstance(items, list):
                    for item in items:
                        idx = item.get("id") if isinstance(item, dict) else item
                        try:
                            idx = int(idx)
                            if idx in id_to_path:
                                paths.append(id_to_path[idx])
                        except (TypeError, ValueError):
                            # ignore bad ids
                            continue
                # de-duplicate while preserving order
                seen, uniq = set(), []
                for p in paths:
                    if p not in seen:
                        seen.add(p); uniq.append(p)
                if uniq:
                    out[kw] = uniq
            return out

        parsed["keywords"] = ids_to_paths(parsed.get("keywords"), id_to_path)
        return parsed

    except Exception as e:
        return {"error": "Failed to parse YAML", "raw_response": raw, "details": str(e)}



if __name__ == "__main__":
    keyword = input("Enter a keyword: ")
    jpg_paths = load_indexed_images()
    response = gpt_agent_with_indexed_images(keyword, jpg_paths)
    print("\n=== YAML OUTPUT ===\n")
    print(response)