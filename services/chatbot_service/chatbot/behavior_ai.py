import json
import math
from datetime import datetime, timezone
from pathlib import Path

from .category_taxonomy import category_items, detect_category_matches, fetch_catalog_categories
from .models import BehaviorEvent

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_BEHAVIOR_PATH = ARTIFACT_DIR / "model_behavior.json"
TRAINING_DATA_PATH = ARTIFACT_DIR / "training_data_behavior.json"


def _ensure_artifact_dir():
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _catalog_categories(extra_slugs=None, model_categories=None):
    seed_categories = category_items(fetch_catalog_categories())
    allowed_slugs = {item["slug"] for item in seed_categories}
    normalized_model_categories = [
        item
        for item in (model_categories or [])
        if str((item or {}).get("slug") or "").strip().lower() in allowed_slugs
    ]
    event_slugs = list(
        BehaviorEvent.objects.exclude(category_slug="")
        .values_list("category_slug", flat=True)
        .distinct()
    )
    valid_extra_slugs = [
        str(slug or "").strip().lower()
        for slug in [*(extra_slugs or []), *event_slugs]
        if str(slug or "").strip().lower() in allowed_slugs
    ]
    return category_items(seed_categories + normalized_model_categories, extra_slugs=valid_extra_slugs)


def record_behavior_event(user_ref, message, current_product=None, user_context=None):
    user_ref = str(user_ref or "").strip() or "anonymous"
    current_product = current_product or {}
    user_context = user_context or {}
    category_slug = str(current_product.get("category_slug") or current_product.get("service") or "").strip().lower()

    BehaviorEvent.objects.create(
        user_ref=user_ref,
        event_type=BehaviorEvent.EVENT_CHATBOT_ASK,
        category_slug=category_slug[:120],
        product_id=max(0, _safe_int(current_product.get("id"), 0)),
        metadata={
            "message": str(message or "")[:500],
            "current_category_slug": category_slug[:120],
            "cart_items_count": len(user_context.get("cart_items") or []),
            "saved_items_count": len(user_context.get("saved_items") or []),
            "recent_paid_items_count": len(user_context.get("recent_paid_items") or []),
        },
    )


def _score_event(event, categories):
    metadata = event.metadata or {}
    category_scores = {item["slug"]: 0.0 for item in categories}
    for category_slug in detect_category_matches(metadata.get("message") or "", categories=categories):
        category_scores[category_slug] += 2.0

    current_category_slug = str(metadata.get("current_category_slug") or event.category_slug or "").strip().lower()
    if current_category_slug in category_scores:
        category_scores[current_category_slug] += 3.0

    cart_count = _safe_int(metadata.get("cart_items_count"), 0)
    saved_count = _safe_int(metadata.get("saved_items_count"), 0)
    paid_count = _safe_int(metadata.get("recent_paid_items_count"), 0)
    if current_category_slug in category_scores:
        category_scores[current_category_slug] += min(4.0, cart_count * 0.2 + saved_count * 0.15 + paid_count * 0.25)
    return category_scores


def _history_scores(user_ref, categories):
    scores = {item["slug"]: 0.0 for item in categories}
    events = list(BehaviorEvent.objects.filter(user_ref=user_ref).order_by("-id")[:400])
    for event in events:
        event_scores = _score_event(event, categories)
        for slug, value in event_scores.items():
            scores[slug] += value
    return scores, len(events)


def _normalize_probabilities(scores):
    total = sum(max(0.0, value) for value in scores.values())
    if total <= 0:
        base = 1.0 / max(1, len(scores))
        return {slug: round(base, 4) for slug in scores}
    return {slug: round(max(0.0, value) / total, 4) for slug, value in scores.items()}


def _build_training_samples():
    categories = _catalog_categories()
    user_refs = list(BehaviorEvent.objects.values_list("user_ref", flat=True).distinct())
    samples = []
    global_scores = {item["slug"]: 0.0 for item in categories}
    for user_ref in user_refs:
        scores, event_count = _history_scores(user_ref, categories)
        if sum(scores.values()) <= 0:
            continue
        for slug, value in scores.items():
            global_scores[slug] += value
        dominant_slug = max(scores, key=scores.get)
        samples.append(
            {
                "user_ref": user_ref,
                "event_count": event_count,
                "category_affinity": _normalize_probabilities(scores),
                "dominant_category_slug": dominant_slug,
            }
        )
    return samples, global_scores, len(user_refs), categories


def train_and_save_behavior_model():
    samples, global_scores, distinct_users, categories = _build_training_samples()
    priors = _normalize_probabilities(global_scores)
    payload = {
        "version": 3,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "categories": categories,
        "priors": priors,
        "metrics": {
            "samples": len(samples),
            "distinct_users": distinct_users,
            "total_events": BehaviorEvent.objects.count(),
            "category_count": len(categories),
            "loss": None,
        },
    }

    training_payload = {
        "version": 3,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "categories": categories,
        "source_stats": payload["metrics"],
        "samples": samples,
    }

    _ensure_artifact_dir()
    MODEL_BEHAVIOR_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    TRAINING_DATA_PATH.write_text(json.dumps(training_payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return payload


def _load_behavior_model():
    if not MODEL_BEHAVIOR_PATH.exists():
        return None
    try:
        payload = json.loads(MODEL_BEHAVIOR_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    if int(payload.get("version") or 0) < 3:
        return None
    if not isinstance(payload.get("categories"), list) or not isinstance(payload.get("priors"), dict):
        return None
    return payload


def predict_behavior_for_user_ref(user_ref, question="", current_product=None, user_context=None):
    user_ref = str(user_ref or "").strip() or "anonymous"
    current_product = current_product or {}
    user_context = user_context or {}

    model_payload = _load_behavior_model()
    base_model_payload = model_payload or {"categories": fetch_catalog_categories(), "priors": {}}
    categories = _catalog_categories(
        extra_slugs=[current_product.get("category_slug") or current_product.get("service")],
        model_categories=base_model_payload.get("categories") or [],
    )
    scores = {
        item["slug"]: 0.2 + float(base_model_payload.get("priors", {}).get(item["slug"], 0.0))
        for item in categories
    }

    history_scores, event_count = _history_scores(user_ref, categories)
    for slug, value in history_scores.items():
        scores[slug] += value

    for slug in detect_category_matches(question, categories=categories):
        scores[slug] += 3.0

    current_category_slug = str(current_product.get("category_slug") or current_product.get("service") or "").strip().lower()
    if current_category_slug in scores:
        scores[current_category_slug] += 2.5

    for text in (user_context.get("cart_items") or []) + (user_context.get("saved_items") or []) + (user_context.get("recent_paid_items") or []):
        for slug in detect_category_matches(text, categories=categories):
            scores[slug] += 0.4

    normalized = _normalize_probabilities(scores)
    dominant_category_slug = max(normalized, key=normalized.get) if normalized else ""
    context_count = len(user_context.get("cart_items") or []) + len(user_context.get("saved_items") or []) + len(user_context.get("recent_paid_items") or [])
    intent_score = min(0.95, 0.2 + (math.log1p(event_count) * 0.12) + (context_count * 0.04))

    return {
        "intent_score": round(intent_score, 4),
        "category_scores": normalized,
        "dominant_category_slug": dominant_category_slug,
        "source": "model_behavior" if model_payload else "heuristic",
        "model_metrics": base_model_payload.get("metrics") or {},
        "categories": categories,
    }
