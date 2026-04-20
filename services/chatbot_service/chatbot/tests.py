import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from django.test import Client, TestCase

from .behavior_ai import predict_behavior_for_user_ref, record_behavior_event, train_and_save_behavior_model
from .category_taxonomy import detect_category_matches
from .models import BehaviorEvent
from .rag_kb import load_knowledge_base


RUNTIME_CATEGORIES = [
    {"slug": "business-laptops", "name": "Business Laptops"},
    {"slug": "gaming-laptops", "name": "Gaming Laptops"},
    {"slug": "ultrabooks", "name": "Ultrabooks"},
    {"slug": "smartphones", "name": "Smartphones"},
    {"slug": "tablets", "name": "Tablets"},
    {"slug": "smartwatches", "name": "Smartwatches"},
    {"slug": "audio", "name": "Audio"},
    {"slug": "keyboards-mice", "name": "Keyboards & Mice"},
    {"slug": "chargers-cables", "name": "Chargers & Cables"},
    {"slug": "bags-stands", "name": "Bags & Stands"},
]


def _json_response(payload):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


class ChatbotTaxonomyTests(TestCase):
    def test_detect_category_matches_understands_runtime_taxonomy(self):
        matches = detect_category_matches(
            "Need a business laptop plus a compact charger for travel.",
            categories=RUNTIME_CATEGORIES,
        )
        self.assertIn("business-laptops", matches)
        self.assertIn("chargers-cables", matches)

    def test_record_behavior_event_persists_category_slug(self):
        record_behavior_event(
            user_ref="7",
            message="Need accessories for travel.",
            current_product={"category_slug": "bags-stands", "id": 21},
            user_context={"cart_items": ["Commute Pack 16"], "saved_items": [], "recent_paid_items": []},
        )
        event = BehaviorEvent.objects.get()
        self.assertEqual(event.category_slug, "bags-stands")
        self.assertEqual(event.metadata["current_category_slug"], "bags-stands")

    def test_predict_behavior_prefers_question_and_history_categories(self):
        with patch("chatbot.behavior_ai.fetch_catalog_categories", return_value=RUNTIME_CATEGORIES):
            record_behavior_event(
                user_ref="42",
                message="I want wireless earbuds and good audio for commuting.",
                current_product={"category_slug": "audio", "id": 8},
                user_context={"cart_items": [], "saved_items": [], "recent_paid_items": []},
            )
            prediction = predict_behavior_for_user_ref(
                user_ref="42",
                question="Suggest more audio gear for meetings and travel.",
                current_product={"category_slug": "audio", "id": 8},
                user_context={"cart_items": ["QuietBeat ANC"], "saved_items": [], "recent_paid_items": []},
            )
        self.assertEqual(prediction["dominant_category_slug"], "audio")
        self.assertGreater(prediction["category_scores"]["audio"], 0)


class ChatbotArtifactTests(TestCase):
    def test_train_behavior_model_writes_dynamic_category_slug_artifacts(self):
        record_behavior_event(
            user_ref="audio-user",
            message="Need earbuds, speakers, and better audio for work calls.",
            current_product={"category_slug": "audio", "id": 7},
            user_context={"cart_items": ["QuietBeat ANC"], "saved_items": [], "recent_paid_items": []},
        )
        record_behavior_event(
            user_ref="travel-user",
            message="Looking for a travel bag and a desk stand.",
            current_product={"category_slug": "bags-stands", "id": 21},
            user_context={"cart_items": ["Commute Pack 16"], "saved_items": [], "recent_paid_items": []},
        )
        record_behavior_event(
            user_ref="legacy-user",
            message="Need a phone for daily travel and photos.",
            current_product={"category_slug": "mobile", "id": 99},
            user_context={"cart_items": [], "saved_items": [], "recent_paid_items": []},
        )

        with TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir) / "model_behavior.json"
            training_path = Path(temp_dir) / "training_data_behavior.json"
            with patch("chatbot.behavior_ai.MODEL_BEHAVIOR_PATH", model_path), patch(
                "chatbot.behavior_ai.TRAINING_DATA_PATH",
                training_path,
            ), patch("chatbot.behavior_ai.fetch_catalog_categories", return_value=RUNTIME_CATEGORIES):
                payload = train_and_save_behavior_model()

            self.assertEqual(payload["version"], 3)
            self.assertEqual(payload["metrics"]["category_count"], 10)
            self.assertIn("audio", payload["priors"])
            self.assertNotIn("laptop", payload["priors"])

            training_payload = json.loads(training_path.read_text(encoding="utf-8"))
            dominant_slugs = {sample["dominant_category_slug"] for sample in training_payload["samples"]}
            self.assertIn("audio", dominant_slugs)
            self.assertIn("bags-stands", dominant_slugs)

    def test_load_knowledge_base_rebuilds_legacy_payload_with_runtime_categories(self):
        legacy_payload = {"version": 1, "documents": [{"doc_type": "product", "doc_id": "legacy"}]}
        product_payload = [
            {
                "id": 11,
                "name": "SkyPhone X",
                "brand": "Apple",
                "price": "1099.00",
                "stock": 28,
                "description": "Flagship phone with strong camera output.",
                "category_slug": "smartphones",
                "category_name": "Smartphones",
            }
        ]

        with TemporaryDirectory() as temp_dir:
            kb_path = Path(temp_dir) / "knowledge_base.json"
            kb_path.write_text(json.dumps(legacy_payload), encoding="utf-8")

            with patch("chatbot.rag_kb.KB_PATH", kb_path), patch(
                "chatbot.rag_kb.fetch_catalog_categories",
                return_value=RUNTIME_CATEGORIES,
            ), patch("chatbot.rag_kb.requests.get", return_value=_json_response(product_payload)):
                payload = load_knowledge_base(auto_build=True)

            self.assertEqual(payload["version"], 3)
            self.assertEqual(payload["stats"]["category_count"], 10)
            product_doc = next(doc for doc in payload["documents"] if doc["doc_type"] == "product")
            self.assertEqual(product_doc["category_slug"], "smartphones")
            self.assertEqual(product_doc["service"], "smartphones")
            self.assertEqual(product_doc["url"], "/customer/products/smartphones/11/")


class ChatbotReplyFlowTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_chat_reply_view_keeps_proxy_compatible_shape_for_dynamic_categories(self):
        recommendations = [
            {
                "service": "smartphones",
                "category_slug": "smartphones",
                "category_name": "Smartphones",
                "id": 11,
                "name": "SkyPhone X",
                "brand": "Apple",
                "description": "Flagship phone with strong camera output.",
                "price": "1099.00",
                "stock": 28,
                "image_url": "",
            }
        ]
        rag_docs = [
            {
                "doc_id": "product:smartphones:11",
                "doc_type": "product",
                "service": "smartphones",
                "category_slug": "smartphones",
                "category_name": "Smartphones",
                "product_id": 11,
                "title": "SkyPhone X",
                "text": "SkyPhone X. Category: Smartphones. Brand: Apple.",
                "url": "/customer/products/smartphones/11/",
                "tokens": ["skyphone", "smartphones", "apple"],
            }
        ]

        with patch("chatbot.behavior_ai.fetch_catalog_categories", return_value=RUNTIME_CATEGORIES), patch(
            "chatbot.services.fetch_catalog_categories",
            return_value=RUNTIME_CATEGORIES,
        ), patch("chatbot.services._fetch_products", return_value=recommendations), patch(
            "chatbot.services.retrieve_rag_context",
            return_value=rag_docs,
        ), patch(
            "chatbot.services._call_llm",
            return_value=("Here are strong phone options for travel and daily use.\n- SkyPhone X", None, "gemma_4_31b"),
        ):
            response = self.client.post(
                "/api/chat/reply/",
                data=json.dumps(
                    {
                        "message": "Can you suggest a good smartphone for travel photos?",
                        "user_ref": "reply-user",
                        "current_product": {
                            "category_slug": "smartphones",
                            "category_name": "Smartphones",
                            "service": "smartphones",
                            "id": 11,
                            "name": "SkyPhone X",
                        },
                        "user_context": {"cart_items": [], "saved_items": [], "recent_paid_items": []},
                    }
                ),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["fallback_used"])
        self.assertEqual(payload["source"], "gemma_4_31b")
        self.assertEqual(payload["recommendations"][0]["category_slug"], "smartphones")
        self.assertEqual(payload["citations"][0]["url"], "/customer/products/smartphones/11/")
        self.assertIn("SkyPhone X", payload["answer"])
