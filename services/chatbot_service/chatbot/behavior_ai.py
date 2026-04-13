import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path

from .models import BehaviorEvent

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
MODEL_BEHAVIOR_PATH = ARTIFACT_DIR / "model_behavior.json"
TRAINING_DATA_PATH = ARTIFACT_DIR / "training_data_behavior.json"
SERVICE_NAMES = ["laptop", "mobile", "accessory"]
FEATURE_NAMES = [
    "ask_count",
    "mentions_laptop",
    "mentions_mobile",
    "mentions_accessory",
    "current_product_laptop",
    "current_product_mobile",
    "current_product_accessory",
    "cart_items_count",
    "saved_items_count",
    "recent_paid_items_count",
    "avg_phrase_len",
    "english_ratio",
]


def _ensure_artifact_dir():
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _log_scale(value):
    return round(math.log1p(max(0.0, float(value))), 6)


def _softmax(values):
    if not values:
        return []
    max_v = max(values)
    exp_values = [math.exp(v - max_v) for v in values]
    total = sum(exp_values)
    if total <= 0:
        return [1.0 / len(values)] * len(values)
    return [v / total for v in exp_values]


def _sigmoid(value):
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def _relu(value):
    return value if value > 0 else 0.0


def _dense(input_vec, weights, bias):
    output = []
    for out_idx in range(len(bias)):
        value = bias[out_idx]
        for in_idx in range(len(input_vec)):
            value += input_vec[in_idx] * weights[in_idx][out_idx]
        output.append(value)
    return output


def _argmax(values):
    if not values:
        return 0
    best_idx = 0
    best_value = values[0]
    for idx, value in enumerate(values[1:], start=1):
        if value > best_value:
            best_value = value
            best_idx = idx
    return best_idx


def _detect_requested_services(text):
    lowered = (text or "").lower()
    keyword_map = {
        "mobile": ["mobile", "phone", "smartphone", "dien thoai", "điện thoại", "android", "ios"],
        "laptop": ["laptop", "notebook", "ultrabook", "macbook"],
        "accessory": ["accessory", "accessories", "phu kien", "phụ kiện", "headphone", "charger"],
    }

    matches = []
    for service_name, keywords in keyword_map.items():
        if any(keyword in lowered for keyword in keywords):
            matches.append(service_name)
    return matches


def _english_ratio(text):
    if not text:
        return 0.0
    chars = [c for c in text if c.isalpha()]
    if not chars:
        return 0.0
    english = sum(1 for c in chars if "a" <= c.lower() <= "z")
    return english / len(chars)


def _feature_vector_from_events(user_ref):
    events = list(BehaviorEvent.objects.filter(user_ref=user_ref).order_by("-id")[:400])

    ask_count = len(events)
    mention_laptop = 0
    mention_mobile = 0
    mention_accessory = 0
    current_product_laptop = 0
    current_product_mobile = 0
    current_product_accessory = 0
    cart_items_count = 0
    saved_items_count = 0
    recent_paid_items_count = 0
    phrase_lengths = []
    english_ratios = []

    for event in events:
        metadata = event.metadata or {}
        message = str(metadata.get("message") or "")
        requested = _detect_requested_services(message)
        if "laptop" in requested:
            mention_laptop += 1
        if "mobile" in requested:
            mention_mobile += 1
        if "accessory" in requested:
            mention_accessory += 1

        product_service = str(metadata.get("current_product_service") or "").strip().lower()
        if product_service == "laptop":
            current_product_laptop += 1
        elif product_service == "mobile":
            current_product_mobile += 1
        elif product_service == "accessory":
            current_product_accessory += 1

        cart_items_count += _safe_int(metadata.get("cart_items_count"), 0)
        saved_items_count += _safe_int(metadata.get("saved_items_count"), 0)
        recent_paid_items_count += _safe_int(metadata.get("recent_paid_items_count"), 0)

        words = [w for w in message.split() if w.strip()]
        if words:
            phrase_lengths.append(len(words))
        english_ratios.append(_english_ratio(message))

    avg_phrase_len = (sum(phrase_lengths) / len(phrase_lengths)) if phrase_lengths else 0.0
    avg_english_ratio = (sum(english_ratios) / len(english_ratios)) if english_ratios else 0.0

    vector = [
        _log_scale(ask_count),
        _log_scale(mention_laptop),
        _log_scale(mention_mobile),
        _log_scale(mention_accessory),
        _log_scale(current_product_laptop),
        _log_scale(current_product_mobile),
        _log_scale(current_product_accessory),
        _log_scale(cart_items_count),
        _log_scale(saved_items_count),
        _log_scale(recent_paid_items_count),
        min(avg_phrase_len / 20.0, 1.0),
        max(0.0, min(1.0, avg_english_ratio)),
    ]

    category_scores = {
        "laptop": mention_laptop + (2 * current_product_laptop),
        "mobile": mention_mobile + (2 * current_product_mobile),
        "accessory": mention_accessory + (2 * current_product_accessory),
    }

    intent_score_seed = ask_count + cart_items_count + saved_items_count + recent_paid_items_count
    intent_label = 1 if intent_score_seed >= 6 else 0
    category_idx = _argmax([category_scores["laptop"], category_scores["mobile"], category_scores["accessory"]])

    return {
        "vector": vector,
        "intent_label": intent_label,
        "category_idx": category_idx,
        "category_scores": category_scores,
    }


def record_behavior_event(user_ref, message, current_product=None, user_context=None):
    user_ref = str(user_ref or "").strip() or "anonymous"
    current_product = current_product or {}
    user_context = user_context or {}

    cart_count = len(user_context.get("cart_items") or [])
    saved_count = len(user_context.get("saved_items") or [])
    recent_paid_count = len(user_context.get("recent_paid_items") or [])

    BehaviorEvent.objects.create(
        user_ref=user_ref,
        event_type=BehaviorEvent.EVENT_CHATBOT_ASK,
        product_service=str(current_product.get("service") or "").strip().lower()[:20],
        product_id=max(0, _safe_int(current_product.get("id"), 0)),
        metadata={
            "message": str(message or "")[:500],
            "current_product_service": str(current_product.get("service") or "")[:20],
            "cart_items_count": cart_count,
            "saved_items_count": saved_count,
            "recent_paid_items_count": recent_paid_count,
        },
    )


def _init_weights(in_size, hidden1, hidden2, out_size):
    random.seed(42)
    w1 = [[random.uniform(-0.15, 0.15) for _ in range(hidden1)] for _ in range(in_size)]
    b1 = [0.0 for _ in range(hidden1)]
    w2 = [[random.uniform(-0.15, 0.15) for _ in range(hidden2)] for _ in range(hidden1)]
    b2 = [0.0 for _ in range(hidden2)]
    w3 = [[random.uniform(-0.15, 0.15) for _ in range(out_size)] for _ in range(hidden2)]
    b3 = [0.0 for _ in range(out_size)]
    return {"w1": w1, "b1": b1, "w2": w2, "b2": b2, "w3": w3, "b3": b3}


def _forward(x, model):
    z1 = _dense(x, model["w1"], model["b1"])
    a1 = [_relu(v) for v in z1]
    z2 = _dense(a1, model["w2"], model["b2"])
    a2 = [_relu(v) for v in z2]
    z3 = _dense(a2, model["w3"], model["b3"])

    intent_prob = _sigmoid(z3[0])
    category_probs = _softmax(z3[1:4])
    return {
        "z1": z1,
        "a1": a1,
        "z2": z2,
        "a2": a2,
        "intent_prob": intent_prob,
        "category_probs": category_probs,
    }


def _fit_model(dataset, epochs=120, lr=0.02):
    model = _init_weights(len(FEATURE_NAMES), 18, 10, 4)
    if not dataset:
        return model, {"loss": None, "samples": 0}

    for _ in range(max(10, epochs)):
        random.shuffle(dataset)
        for row in dataset:
            x = row["x"]
            out = _forward(x, model)
            y_intent = row["y_intent"]
            y_cat = row["y_category"]

            d3 = [0.0, 0.0, 0.0, 0.0]
            d3[0] = out["intent_prob"] - y_intent
            for cat_idx, prob in enumerate(out["category_probs"]):
                target = 1.0 if cat_idx == y_cat else 0.0
                d3[cat_idx + 1] = prob - target

            d2 = [0.0 for _ in range(10)]
            for h2 in range(10):
                grad = 0.0
                for o in range(4):
                    grad += model["w3"][h2][o] * d3[o]
                if out["z2"][h2] <= 0:
                    grad = 0.0
                d2[h2] = grad

            d1 = [0.0 for _ in range(18)]
            for h1 in range(18):
                grad = 0.0
                for h2 in range(10):
                    grad += model["w2"][h1][h2] * d2[h2]
                if out["z1"][h1] <= 0:
                    grad = 0.0
                d1[h1] = grad

            for h2 in range(10):
                for o in range(4):
                    model["w3"][h2][o] -= lr * (out["a2"][h2] * d3[o])
            for o in range(4):
                model["b3"][o] -= lr * d3[o]

            for h1 in range(18):
                for h2 in range(10):
                    model["w2"][h1][h2] -= lr * (out["a1"][h1] * d2[h2])
            for h2 in range(10):
                model["b2"][h2] -= lr * d2[h2]

            for i in range(len(FEATURE_NAMES)):
                for h1 in range(18):
                    model["w1"][i][h1] -= lr * (x[i] * d1[h1])
            for h1 in range(18):
                model["b1"][h1] -= lr * d1[h1]

    total_loss = 0.0
    for row in dataset:
        out = _forward(row["x"], model)
        intent_prob = min(1 - 1e-8, max(1e-8, out["intent_prob"]))
        cat_probs = [min(1 - 1e-8, max(1e-8, p)) for p in out["category_probs"]]
        bce = -(row["y_intent"] * math.log(intent_prob) + (1.0 - row["y_intent"]) * math.log(1.0 - intent_prob))
        ce = -math.log(cat_probs[row["y_category"]])
        total_loss += (bce + ce)

    return model, {"loss": round(total_loss / max(1, len(dataset)), 6), "samples": len(dataset)}


def _build_training_dataset():
    total_events = BehaviorEvent.objects.count()
    refs = list(BehaviorEvent.objects.values_list("user_ref", flat=True).distinct())
    base_dataset = []
    for user_ref in refs:
        row = _feature_vector_from_events(user_ref)
        if sum(row["category_scores"].values()) <= 0 and _safe_int(row.get("intent_label"), 0) == 0:
            continue
        base_dataset.append(
            {
                "user_ref": str(user_ref or "anonymous"),
                "x": row["vector"],
                "y_intent": float(row["intent_label"]),
                "y_category": int(row["category_idx"]),
            }
        )

    if not base_dataset:
        return {
            "base_dataset": [],
            "augmented_dataset": [],
            "source_stats": {
                "total_events": int(total_events),
                "distinct_users": len(refs),
            },
        }

    augmented = []
    for row in base_dataset:
        augmented.append(row)
        for _ in range(2):
            jittered = []
            for value in row["x"]:
                jittered.append(max(0.0, value + random.uniform(-0.06, 0.06)))
            augmented.append(
                {
                    "user_ref": row["user_ref"],
                    "x": jittered,
                    "y_intent": row["y_intent"],
                    "y_category": row["y_category"],
                }
            )

    return {
        "base_dataset": base_dataset,
        "augmented_dataset": augmented,
        "source_stats": {
            "total_events": int(total_events),
            "distinct_users": len(refs),
        },
    }


def _save_training_data_snapshot(dataset_bundle):
    base_dataset = dataset_bundle.get("base_dataset") or []
    augmented_dataset = dataset_bundle.get("augmented_dataset") or []
    source_stats = dataset_bundle.get("source_stats") or {}

    readable_samples = []
    for row in base_dataset:
        readable_samples.append(
            {
                "user_ref": row.get("user_ref") or "anonymous",
                "intent_label": int(row.get("y_intent") or 0),
                "category_label": SERVICE_NAMES[int(row.get("y_category") or 0)],
                "features": {
                    FEATURE_NAMES[idx]: float(value)
                    for idx, value in enumerate(row.get("x") or [])
                    if idx < len(FEATURE_NAMES)
                },
            }
        )

    payload = {
        "version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "feature_names": FEATURE_NAMES,
        "service_names": SERVICE_NAMES,
        "source_stats": source_stats,
        "base_samples_count": len(base_dataset),
        "augmented_samples_count": len(augmented_dataset),
        "base_samples": readable_samples,
    }
    TRAINING_DATA_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return payload


def train_and_save_behavior_model(epochs=120, lr=0.02):
    dataset_bundle = _build_training_dataset()
    dataset = dataset_bundle.get("augmented_dataset") or []
    model, metrics = _fit_model(dataset, epochs=epochs, lr=lr)

    payload = {
        "feature_names": FEATURE_NAMES,
        "service_names": SERVICE_NAMES,
        "model": model,
        "metrics": metrics,
        "version": 1,
    }

    _ensure_artifact_dir()
    MODEL_BEHAVIOR_PATH.write_text(json.dumps(payload), encoding="utf-8")
    _save_training_data_snapshot(dataset_bundle)
    return payload


def _load_model_behavior():
    if not MODEL_BEHAVIOR_PATH.exists():
        return None
    try:
        payload = json.loads(MODEL_BEHAVIOR_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None

    model = payload.get("model") or {}
    if not all(name in model for name in ["w1", "b1", "w2", "b2", "w3", "b3"]):
        return None
    return payload


def _heuristic_prediction(user_ref, question="", current_product=None, user_context=None):
    row = _feature_vector_from_events(user_ref)
    scores = dict(row.get("category_scores") or {})

    for service in _detect_requested_services(question):
        scores[service] = scores.get(service, 0) + 4

    cp_service = (current_product or {}).get("service")
    if cp_service in scores:
        scores[cp_service] = scores.get(cp_service, 0) + 2

    raw = [
        _safe_float(scores.get("laptop"), 0.0),
        _safe_float(scores.get("mobile"), 0.0),
        _safe_float(scores.get("accessory"), 0.0),
    ]
    cat_probs = _softmax(raw) if sum(raw) > 0 else [0.34, 0.33, 0.33]

    context_bonus = (
        len((user_context or {}).get("cart_items") or [])
        + len((user_context or {}).get("saved_items") or [])
        + len((user_context or {}).get("recent_paid_items") or [])
    )
    intent_score = min(0.95, 0.2 + (row["vector"][0] * 0.25) + (context_bonus * 0.05))

    dominant_idx = _argmax(cat_probs)
    return {
        "intent_score": round(float(intent_score), 4),
        "category_scores": {
            "laptop": round(cat_probs[0], 4),
            "mobile": round(cat_probs[1], 4),
            "accessory": round(cat_probs[2], 4),
        },
        "dominant_service": SERVICE_NAMES[dominant_idx],
        "source": "heuristic",
    }


def predict_behavior_for_user_ref(user_ref, question="", current_product=None, user_context=None):
    user_ref = str(user_ref or "").strip() or "anonymous"

    payload = _load_model_behavior()
    if not payload:
        return _heuristic_prediction(
            user_ref=user_ref,
            question=question,
            current_product=current_product,
            user_context=user_context,
        )

    row = _feature_vector_from_events(user_ref)
    model = payload.get("model")
    out = _forward(row["vector"], model)
    cat_probs = out["category_probs"]
    dominant_idx = _argmax(cat_probs)

    return {
        "intent_score": round(float(out["intent_prob"]), 4),
        "category_scores": {
            "laptop": round(cat_probs[0], 4),
            "mobile": round(cat_probs[1], 4),
            "accessory": round(cat_probs[2], 4),
        },
        "dominant_service": SERVICE_NAMES[dominant_idx],
        "source": "model_behavior",
        "model_metrics": payload.get("metrics") or {},
    }
