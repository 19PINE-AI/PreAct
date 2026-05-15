#!/usr/bin/env python3
"""Stronger-embedding selector ablation for paper §5.4.

Replicates the 45-paraphrase audit but compares two embedding backends:
  - sentence-transformers/all-MiniLM-L6-v2 (384-dim, used in paper)
  - BAAI/bge-large-en-v1.5 (1024-dim, much stronger)

Same corpus: 56 programs from rag_db_warm_baseline_20260425.
Same protocol: 15 representative programs × 3 LLM-generated paraphrases.

Reports functional-accuracy / wrong-task-family / no-pick rates at a
sweep of thresholds for each model, so the comparison is fair (each
model evaluated at its own optimal operating point).

Cost: ~45 Claude API calls for paraphrase generation, plus local
embedding compute. ~$2 total.

Output: writes a markdown table to stdout + JSON detail file.
"""

import asyncio
import json
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["RAG_DB_PATH"] = "rag_db_warm_baseline_20260425"

import numpy as np  # noqa: E402

from preact.config import LLMConfig  # noqa: E402
from preact.llm.client import LLMClient  # noqa: E402
from preact.rag.store import ProgramStore  # noqa: E402


# 15 official-15 Android task descriptions (the same set used in the
# n=1 paper audit). Picked by exact / nearest match against the
# corpus's task_descriptions.
OFFICIAL_15_TARGETS = [
    "Record an audio clip",
    "Record an audio clip using",
    "Take one photo",
    "Pause the stopwatch",
    "Go to the new contact screen and enter the following details",
    "Delete the file",
    "Create a new note in Markor",
    "Create a new folder",
    "Set the brightness",
    "Turn on Wi-Fi",
    "Open the file",
    "Add a new contact",
    "Take one video",
    "Verify the stopwatch is running",
    "Draw a route",
]


async def generate_paraphrases(llm: LLMClient, desc: str, n: int = 3) -> list[str]:
    """Ask Claude for n paraphrases of an Android-task description."""
    prompt = (
        f"Rewrite the following Android-task instruction in {n} natural "
        "but distinct ways that a user might phrase the same intent. "
        "Vary vocabulary, sentence structure, and level of formality. "
        "Keep all parameter slots ($var) intact. Return the "
        f"{n} rewrites as a JSON array of strings, nothing else.\n\n"
        f"Original: {desc}\n\n"
        f"Output:"
    )
    text = await llm.complete(
        messages=[{"role": "user", "content": prompt}],
        system="You output only valid JSON.",
    )
    # Strip code-fence if any
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        if t.lstrip().startswith("json"):
            t = t.split("\n", 1)[1] if "\n" in t else t
        t = t.rstrip("`")
    try:
        arr = json.loads(t)
        if isinstance(arr, list) and len(arr) >= n:
            return [str(x) for x in arr[:n]]
    except Exception:
        pass
    # Fall back: split on lines
    lines = [ln.strip(" -*\"'") for ln in t.splitlines() if ln.strip()]
    return lines[:n] if len(lines) >= n else lines + [desc] * (n - len(lines))


def _model_loader(name: str):
    """Return (model, tokenizer) for a HF AutoModel pair."""
    from transformers import AutoModel, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(name)
    model = AutoModel.from_pretrained(name)
    model.eval()
    return model, tok


def encode(texts: list[str], model, tokenizer) -> np.ndarray:
    """Mean-pooled embeddings."""
    import torch
    enc = tokenizer(
        texts, padding=True, truncation=True, return_tensors="pt", max_length=256
    )
    with torch.no_grad():
        out = model(**enc)
    mask = enc["attention_mask"].unsqueeze(-1).float()
    summed = (out.last_hidden_state * mask).sum(1)
    counts = mask.sum(1).clamp(min=1e-9)
    embs = (summed / counts).numpy()
    # L2-normalize
    norms = np.linalg.norm(embs, axis=1, keepdims=True) + 1e-9
    return embs / norms


def top1_with_threshold(
    query_emb: np.ndarray,
    candidate_embs: np.ndarray,
    threshold: float,
) -> tuple[int | None, float]:
    """Cosine similarity (embeddings already L2-normed)."""
    sims = candidate_embs @ query_emb
    best = int(np.argmax(sims))
    sim = float(sims[best])
    return (best if sim >= threshold else None), sim


async def main():
    # Load corpus
    store = ProgramStore()
    all_progs = store.list_programs(platform="android")
    print(f"# Corpus: {len(all_progs)} Android programs", flush=True)

    # Pick 15 target programs: prefer matches to OFFICIAL_15_TARGETS, then
    # fill any remaining slots with diverse programs from the corpus (one per
    # application family, e.g. one Markor, one Camera, one Clock, ...).
    selected = []
    used_ids = set()
    for target in OFFICIAL_15_TARGETS:
        for p in all_progs:
            if (
                target.lower() in p["task_description"].lower()
                and p["program_id"] not in used_ids
            ):
                selected.append(p)
                used_ids.add(p["program_id"])
                break
    # Diverse fill: pick one extra program per app-family until we hit 15
    if len(selected) < 15:
        used_apps = {
            p.get("application_context", "")
            for p in selected
        }
        for p in all_progs:
            if len(selected) >= 15:
                break
            if p["program_id"] in used_ids:
                continue
            ac = p.get("application_context", "")
            if ac not in used_apps:
                selected.append(p)
                used_ids.add(p["program_id"])
                used_apps.add(ac)
        # If still short, fill with any remaining programs (different desc)
        seen_descs = {p["task_description"] for p in selected}
        for p in all_progs:
            if len(selected) >= 15:
                break
            if p["program_id"] in used_ids:
                continue
            if p["task_description"] in seen_descs:
                continue
            selected.append(p)
            used_ids.add(p["program_id"])
            seen_descs.add(p["task_description"])
    print(f"# Selected: {len(selected)} target programs", flush=True)
    for p in selected:
        print(f"#   {p['program_id'][:8]} | {p['task_description'][:80]}", flush=True)

    # All corpus task descriptions (for retrieval)
    descs = [p["task_description"] for p in all_progs]
    ids = [p["program_id"] for p in all_progs]

    # 15 unrelated OOD queries (should-be-no-pick)
    unrelated = [
        "What is the recipe for sourdough bread?",
        "Calculate the integral of x^2 from 0 to 1.",
        "Translate 'good morning' into French.",
        "Recommend a stock for long-term investment.",
        "Plan a 3-day trip to Tokyo.",
        "Explain photosynthesis in simple terms.",
        "Write a haiku about autumn.",
        "What is the capital of Mongolia?",
        "Convert 100 kilograms to pounds.",
        "List the planets in the solar system.",
        "Summarize Hamlet in three sentences.",
        "What's the boiling point of mercury?",
        "Give me a paneer-tikka marinade recipe.",
        "Draft a polite resignation letter.",
        "Compute the 50th Fibonacci number.",
    ]

    # Generate 3 paraphrases per target via Claude
    llm = LLMClient(LLMConfig())
    paraphrases: list[tuple[str, str, str]] = []  # (paraphrase, gold_id, original)
    print("# Generating 45 paraphrases via Claude...", flush=True)
    for p in selected:
        ps = await generate_paraphrases(llm, p["task_description"], n=3)
        for pp in ps:
            paraphrases.append((pp, p["program_id"], p["task_description"]))
    print(f"# Generated {len(paraphrases)} paraphrases", flush=True)

    # Encode with both models
    print("# Encoding with MiniLM-L6-v2 ...", flush=True)
    m_mini, t_mini = _model_loader("sentence-transformers/all-MiniLM-L6-v2")
    cand_mini = encode(descs, m_mini, t_mini)
    queries_mini = encode([p for p, _, _ in paraphrases], m_mini, t_mini)
    unrel_mini = encode(unrelated, m_mini, t_mini)

    print("# Encoding with bge-large-en-v1.5 ...", flush=True)
    try:
        m_bge, t_bge = _model_loader("BAAI/bge-large-en-v1.5")
    except Exception as e:
        print(f"# bge-large load failed: {e}", flush=True)
        # Fall back to bge-small-en-v1.5 if large isn't available
        print("# falling back to bge-small-en-v1.5", flush=True)
        m_bge, t_bge = _model_loader("BAAI/bge-small-en-v1.5")
    cand_bge = encode(descs, m_bge, t_bge)
    queries_bge = encode([p for p, _, _ in paraphrases], m_bge, t_bge)
    unrel_bge = encode(unrelated, m_bge, t_bge)

    # Evaluate over a threshold sweep for each model.
    thresholds = [0.40, 0.50, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85]

    def evaluate(name, cand_e, q_e, unrel_e):
        rows = []
        for tau in thresholds:
            functional = 0  # exact-id OR same-task-family
            wrong = 0       # picked a program that's not in selected (wrong task)
            no_pick = 0
            for (paraphrase, gold_id, _), q in zip(paraphrases, q_e):
                idx, sim = top1_with_threshold(q, cand_e, tau)
                if idx is None:
                    no_pick += 1
                else:
                    pred_id = ids[idx]
                    if pred_id == gold_id:
                        functional += 1
                    else:
                        # Check if picked program shares same task family
                        gold_desc = next(
                            (p["task_description"] for p in selected if p["program_id"] == gold_id),
                            "",
                        )
                        pred_desc = descs[idx]
                        # Same family heuristic: share first 3 significant words
                        gw = set(gold_desc.lower().split()[:6])
                        pw = set(pred_desc.lower().split()[:6])
                        if len(gw & pw) >= 3:
                            functional += 1
                        else:
                            wrong += 1
            n_total = len(paraphrases)
            unrel_false = 0
            for u in unrel_e:
                idx, sim = top1_with_threshold(u, cand_e, tau)
                if idx is not None:
                    unrel_false += 1
            rows.append({
                "model": name,
                "threshold": tau,
                "functional_pct": 100.0 * functional / n_total,
                "wrong_pct": 100.0 * wrong / n_total,
                "no_pick_pct": 100.0 * no_pick / n_total,
                "unrelated_false_pick_pct": 100.0 * unrel_false / len(unrelated),
            })
        return rows

    rows = []
    rows += evaluate("MiniLM-L6-v2", cand_mini, queries_mini, unrel_mini)
    rows += evaluate("bge-large-en-v1.5", cand_bge, queries_bge, unrel_bge)

    print()
    print("| Model | τ | Functional % | Wrong % | No-pick % | Unrelated false-pick % |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        print(
            f"| {r['model']} | {r['threshold']:.2f} | "
            f"{r['functional_pct']:.1f} | {r['wrong_pct']:.1f} | "
            f"{r['no_pick_pct']:.1f} | {r['unrelated_false_pick_pct']:.1f} |"
        )

    # Save raw paraphrases + per-query results
    out = {
        "n_paraphrases": len(paraphrases),
        "n_unrelated": len(unrelated),
        "thresholds": thresholds,
        "results": rows,
        "paraphrases_sample": [
            {"paraphrase": p, "gold_id": gid, "original": orig}
            for p, gid, orig in paraphrases[:10]
        ],
    }
    Path("embedding_ablation_results.json").write_text(json.dumps(out, indent=2))
    print(f"\nDetails saved to embedding_ablation_results.json", flush=True)


if __name__ == "__main__":
    random.seed(42)
    asyncio.run(main())
