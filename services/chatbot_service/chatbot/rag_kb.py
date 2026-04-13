import json
import os
import re
from pathlib import Path

import requests

from .content import FAQ_ITEMS

ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"
KB_PATH = ARTIFACT_DIR / "knowledge_base.json"


def _service_urls():
    return {
        "laptop": os.getenv("LAPTOP_SERVICE_URL", "http://laptop-service:8000"),
        "mobile": os.getenv("MOBILE_SERVICE_URL", "http://mobile-service:8000"),
        "accessory": os.getenv("ACCESSORY_SERVICE_URL", "http://accessory-service:8000"),
    }


def _tokenize(text):
    return [token for token in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(token) > 1]


def _ensure_artifact_dir():
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def _fetch_products(service_name, base_url, limit=120):
    try:
        response = requests.get(f"{base_url}/api/products/", timeout=6)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        return []

    items = payload.get("results", payload) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        return []

    docs = []
    for item in items[: max(1, limit)]:
        product_id = int(item.get("id") or 0)
        if product_id <= 0:
            continue

        name = str(item.get("name") or "").strip()
        brand = str(item.get("brand") or "").strip()
        description = str(item.get("description") or "").strip()
        price = str(item.get("price") or "0")
        stock = int(item.get("stock") or 0)

        docs.append(
            {
                "doc_id": f"product:{service_name}:{product_id}",
                "doc_type": "product",
                "service": service_name,
                "product_id": product_id,
                "title": name,
                "text": f"{name}. Brand: {brand}. Price: {price}. Stock: {stock}. Description: {description}",
                "url": f"/customer/products/{service_name}/{product_id}/",
                "brand": brand,
                "price": price,
                "stock": stock,
            }
        )

    return docs


def _faq_docs():
    docs = []
    for idx, item in enumerate(FAQ_ITEMS, start=1):
        question = str(item.get("question") or "").strip()
        answer = str(item.get("answer") or "").strip()
        docs.append(
            {
                "doc_id": f"faq:{idx}",
                "doc_type": "faq",
                "service": "",
                "product_id": 0,
                "title": question or f"FAQ {idx}",
                "text": f"Q: {question}. A: {answer}",
                "url": "/customer/dashboard/#section-faq",
            }
        )
    return docs


def build_and_save_knowledge_base(max_products_per_service=120):
    docs = []
    docs.extend(_faq_docs())

    for service_name, base_url in _service_urls().items():
        docs.extend(_fetch_products(service_name, base_url, limit=max_products_per_service))

    for doc in docs:
        doc["tokens"] = _tokenize(" ".join([doc.get("title") or "", doc.get("text") or ""]))

    payload = {
        "version": 1,
        "documents": docs,
        "stats": {
            "total_docs": len(docs),
            "product_docs": len([d for d in docs if d.get("doc_type") == "product"]),
            "faq_docs": len([d for d in docs if d.get("doc_type") == "faq"]),
        },
    }

    _ensure_artifact_dir()
    KB_PATH.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def load_knowledge_base(auto_build=True):
    if KB_PATH.exists():
        try:
            payload = json.loads(KB_PATH.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and isinstance(payload.get("documents"), list):
                return payload
        except (OSError, ValueError):
            pass

    if auto_build:
        return build_and_save_knowledge_base()

    return {"version": 1, "documents": [], "stats": {}}


def _score_document(doc, question_tokens, preferred_services=None, current_product=None):
    preferred_services = preferred_services or []
    tokens = doc.get("tokens") or []
    if not tokens:
        return -999.0

    token_set = set(tokens)
    overlap = sum(1 for token in question_tokens if token in token_set)
    score = min(6.0, overlap * 1.2)

    if doc.get("doc_type") == "product":
        service = (doc.get("service") or "").strip().lower()
        if service in preferred_services:
            score += 2.4

        stock = int(doc.get("stock") or 0)
        if stock > 0:
            score += 0.8
        else:
            score -= 1.0

        cp_service = (current_product or {}).get("service")
        cp_id = int((current_product or {}).get("id") or 0)
        if cp_service == service:
            score += 0.8
        if cp_service == service and cp_id and cp_id == int(doc.get("product_id") or 0):
            score -= 2.5

    if doc.get("doc_type") == "faq":
        score += 0.6

    return score


def retrieve_rag_context(question, preferred_services=None, current_product=None, top_k=6):
    payload = load_knowledge_base(auto_build=True)
    docs = payload.get("documents") or []
    if not docs:
        return []

    question_tokens = _tokenize(question)
    ranked = []
    for doc in docs:
        ranked.append(
            (
                _score_document(
                    doc,
                    question_tokens=question_tokens,
                    preferred_services=preferred_services,
                    current_product=current_product,
                ),
                doc,
            )
        )

    ranked.sort(key=lambda row: row[0], reverse=True)

    selected = []
    seen = set()
    for _, doc in ranked:
        doc_id = doc.get("doc_id")
        if not doc_id or doc_id in seen:
            continue
        seen.add(doc_id)
        selected.append(doc)
        if len(selected) >= max(1, top_k):
            break

    return selected


def rag_citations_from_docs(docs, limit=3):
    citations = []
    for doc in docs:
        if len(citations) >= max(1, limit):
            break

        if doc.get("doc_type") == "product":
            label = "Product catalog"
            detail = f"[{doc.get('service')}] {doc.get('title') or 'N/A'}"
        else:
            label = "FAQ"
            detail = doc.get("title") or "FAQ"

        citations.append(
            {
                "label": label,
                "detail": detail,
                "url": doc.get("url") or "/customer/dashboard/",
            }
        )

    return citations
