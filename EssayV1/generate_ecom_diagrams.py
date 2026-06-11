from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT_DIR = Path(__file__).resolve().parent / "generated_diagrams"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def font(size=26, bold=False):
    names = ["arialbd.ttf" if bold else "arial.ttf", "segoeuib.ttf" if bold else "segoeui.ttf"]
    for name in names:
        path = Path("C:/Windows/Fonts") / name
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


FONT = font(24)
FONT_SMALL = font(19)
FONT_TINY = font(16)
FONT_BOLD = font(25, bold=True)
FONT_TITLE = font(34, bold=True)


COLORS = {
    "bg": "#f8fafc",
    "line": "#1f2937",
    "text": "#111827",
    "muted": "#475569",
    "blue": "#dbeafe",
    "green": "#dcfce7",
    "yellow": "#fef3c7",
    "purple": "#ede9fe",
    "rose": "#ffe4e6",
    "white": "#ffffff",
}


def canvas(width, height, title):
    img = Image.new("RGB", (width, height), COLORS["bg"])
    d = ImageDraw.Draw(img)
    d.text((48, 32), title, fill=COLORS["text"], font=FONT_TITLE)
    return img, d


def wrap_text(draw, text, max_width, fnt):
    words = str(text).split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=fnt)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def box(draw, xy, title, body=(), fill="blue", outline=None):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=14, fill=COLORS[fill], outline=outline or COLORS["line"], width=3)
    lines = [title, *body]
    y = y1 + 18
    for index, line in enumerate(lines):
        fnt = FONT_BOLD if index == 0 else FONT_SMALL
        wrapped = wrap_text(draw, line, x2 - x1 - 32, fnt)
        for part in wrapped:
            bbox = draw.textbbox((0, 0), part, font=fnt)
            draw.text((x1 + (x2 - x1 - (bbox[2] - bbox[0])) / 2, y), part, fill=COLORS["text"], font=fnt)
            y += 28 if index == 0 else 24
        if index == 0:
            y += 4


def arrow(draw, start, end, label="", dashed=False):
    sx, sy = start
    ex, ey = end
    if dashed:
        segments = 18
        for i in range(segments):
            if i % 2 == 0:
                x1 = sx + (ex - sx) * i / segments
                y1 = sy + (ey - sy) * i / segments
                x2 = sx + (ex - sx) * (i + 1) / segments
                y2 = sy + (ey - sy) * (i + 1) / segments
                draw.line((x1, y1, x2, y2), fill=COLORS["line"], width=3)
    else:
        draw.line((sx, sy, ex, ey), fill=COLORS["line"], width=3)
    import math

    angle = math.atan2(ey - sy, ex - sx)
    length = 14
    for offset in (math.pi * 0.82, -math.pi * 0.82):
        ax = ex + length * math.cos(angle + offset)
        ay = ey + length * math.sin(angle + offset)
        draw.line((ex, ey, ax, ay), fill=COLORS["line"], width=3)
    if label:
        mx, my = (sx + ex) / 2, (sy + ey) / 2
        bbox = draw.textbbox((0, 0), label, font=FONT_TINY)
        pad = 5
        draw.rectangle((mx - 6, my - 15, mx + (bbox[2] - bbox[0]) + pad, my + 10), fill=COLORS["bg"])
        draw.text((mx, my - 13), label, fill=COLORS["muted"], font=FONT_TINY)


def save(img, name):
    img.save(OUT_DIR / name)


def context_map():
    img, d = canvas(1800, 1050, "DDD Context Map - E-Commerce Project")
    boxes = {
        "user": (70, 190, 420, 340, "User Context", ["user_service", "auth, UI, JWT, proxy"], "green"),
        "product": (570, 160, 930, 320, "Product Context", ["product_service", "categories and products"], "blue"),
        "order": (1080, 160, 1460, 345, "Commerce State", ["order_service", "cart, saved, compare, orders"], "yellow"),
        "payment": (1040, 520, 1400, 670, "Payment Context", ["payment_service", "payment records"], "rose"),
        "shipping": (1440, 520, 1780, 670, "Shipping Context", ["shipping_service", "shipment records"], "rose"),
        "ai": (470, 560, 920, 760, "AI Context", ["chatbot_service", "RAG, model_best, Neo4j context"], "purple"),
    }
    for _, (x1, y1, x2, y2, title, body, fill) in boxes.items():
        box(d, (x1, y1, x2, y2), title, body, fill)
    arrow(d, (420, 265), (570, 240), "browse catalog")
    arrow(d, (420, 305), (1080, 255), "cart/checkout proxy")
    arrow(d, (1270, 345), (1220, 520), "create/confirm")
    arrow(d, (1390, 340), (1535, 520), "create/update")
    arrow(d, (695, 560), (750, 320), "catalog docs", dashed=True)
    arrow(d, (470, 650), (420, 325), "chat proxy")
    arrow(d, (1080, 310), (915, 655), "behavior source", dashed=True)
    save(img, "ecom_context_map.png")


def system_architecture():
    img, d = canvas(1900, 1100, "Runtime Architecture - Docker Compose")
    box(d, (720, 110, 1180, 215), "Browser / Client", ["http://localhost:8080"], "white")
    box(d, (710, 300, 1190, 430), "Nginx API Gateway", ["container gateway", "host port 8080"], "green")
    services = [
        ((60, 610, 360, 760), "user_service", ["UI + auth", "8000, 8003 debug"], "blue"),
        ((430, 610, 730, 760), "product_service", ["catalog API", "8001 debug"], "blue"),
        ((800, 610, 1100, 760), "order_service", ["cart/order API", "internal"], "yellow"),
        ((1170, 610, 1470, 760), "payment_service", ["payments", "internal"], "rose"),
        ((1540, 610, 1840, 760), "shipping_service", ["shipments", "internal"], "rose"),
        ((620, 880, 1040, 1030), "chatbot_service", ["chat/RAG/model", "8005 debug"], "purple"),
    ]
    for xy, title, body, fill in services:
        box(d, xy, title, body, fill)
        arrow(d, (950, 430), ((xy[0] + xy[2]) / 2, xy[1]))
    box(d, (90, 835, 330, 965), "MySQL", ["user_db", "order_db"], "white")
    box(d, (1235, 835, 1510, 1005), "PostgreSQL", ["product_db", "payment_db", "shipping_db", "chatbot_db"], "white")
    box(d, (1540, 835, 1840, 1005), "Neo4j", ["optional graph KB", "7474, 7687"], "white")
    arrow(d, (1100, 650), (1170, 650), "payment")
    arrow(d, (1100, 700), (1540, 700), "shipping")
    arrow(d, (830, 760), (830, 880), "chat proxy")
    arrow(d, (950, 215), (950, 300), "HTTP")
    save(img, "ecom_system_architecture.png")


def database_mapping():
    img, d = canvas(1850, 1120, "Database-Per-Service Mapping")
    boxes = [
        ((70, 160, 480, 350), "user_db (MySQL)", ["auth_user", "customer_blogpost", "customer_testimonial", "legacy_user_mapping"], "green"),
        ((540, 160, 950, 350), "product_db (PostgreSQL)", ["catalog_category", "catalog_product"], "blue"),
        ((1010, 160, 1440, 380), "order_db (MySQL)", ["orders_cartitem", "orders_saveditem", "orders_compareitem", "orders_order", "orders_orderitem", "orders_ordershipping"], "yellow"),
        ((70, 560, 480, 730), "payment_db (PostgreSQL)", ["payments_payment"], "rose"),
        ((540, 560, 950, 730), "shipping_db (PostgreSQL)", ["shipments_shipment"], "rose"),
        ((1010, 560, 1440, 760), "chatbot_db (PostgreSQL)", ["chatbot_behaviorevent"], "purple"),
        ((1480, 560, 1810, 760), "Neo4j + files", ["User, Behavior, Category, Product graph", "artifacts/*.keras, *.json, *.csv"], "white"),
    ]
    for xy, title, body, fill in boxes:
        box(d, xy, title, body, fill)
    arrow(d, (1010, 245), (950, 245), "product snapshots", dashed=True)
    arrow(d, (1225, 380), (275, 560), "order_id", dashed=True)
    arrow(d, (1320, 380), (745, 560), "order_id", dashed=True)
    arrow(d, (1225, 560), (1640, 660), "graph import", dashed=True)
    arrow(d, (950, 245), (1225, 560), "catalog docs", dashed=True)
    save(img, "ecom_database_mapping.png")


def class_diagram():
    img, d = canvas(2200, 1280, "Class Diagram from Django Models")
    boxes = [
        ((60, 170, 420, 360), "Django User", ["id", "username, email", "is_staff, is_superuser"], "green"),
        ((520, 140, 920, 340), "Category", ["name, slug", "description", "sort_order, is_active"], "blue"),
        ((520, 440, 920, 680), "Product", ["category FK", "name, brand", "price, stock", "image_url"], "blue"),
        ((1030, 130, 1460, 365), "CartItem / SavedItem / CompareItem", ["user_id", "category_slug, product_id", "product_name, unit_price", "quantity / stock"], "yellow"),
        ((1030, 480, 1460, 725), "Order", ["user_id", "total_amount", "payment_status", "shipping_status", "source"], "yellow"),
        ((1030, 820, 1460, 1050), "OrderItem", ["order FK", "product snapshot fields", "quantity", "unit_price"], "yellow"),
        ((1510, 500, 1850, 740), "OrderShipping", ["order OneToOne", "recipient_name", "phone, address", "note"], "yellow"),
        ((1510, 160, 1850, 360), "Payment", ["order_id unique", "user_id", "amount", "status, paid_at"], "rose"),
        ((1510, 840, 1850, 1080), "Shipment", ["order_id unique", "user_id", "recipient fields", "status"], "rose"),
        ((520, 820, 920, 1050), "BehaviorEvent", ["user_ref", "event_type", "category_slug, product_id", "metadata JSON"], "purple"),
    ]
    for xy, title, body, fill in boxes:
        box(d, xy, title, body, fill)
    arrow(d, (720, 340), (720, 440), "1..*")
    arrow(d, (920, 540), (1030, 250), "snapshot id", dashed=True)
    arrow(d, (1245, 725), (1245, 820), "1..*")
    arrow(d, (1460, 610), (1510, 610), "1..1")
    arrow(d, (1460, 520), (1510, 260), "order_id", dashed=True)
    arrow(d, (1460, 690), (1510, 940), "order_id", dashed=True)
    # Cross-service user ownership is stored as user_id fields, without a DB foreign key.
    arrow(d, (720, 680), (720, 820), "category/product ref", dashed=True)
    save(img, "ecom_class_diagram.png")


def gateway_routing():
    img, d = canvas(1900, 1120, "Nginx API Gateway Routing")
    box(d, (700, 120, 1200, 250), "gateway", ["nginx:1.27-alpine", "host 8080 -> container 80"], "green")
    routes = [
        ((80, 420, 440, 600), "user-service:8000", ["/", "/customer/", "/staff/", "/admin/", "/gateway/", "/api/auth/"], "blue"),
        ((520, 420, 850, 570), "product-service:8000", ["/api/products/", "/api/categories/"], "blue"),
        ((930, 420, 1260, 570), "order-service:8000", ["/api/cart/", "/api/orders/"], "yellow"),
        ((1340, 420, 1680, 570), "payment-service:8000", ["/api/payments/"], "rose"),
        ((520, 760, 850, 910), "shipping-service:8000", ["/api/shipments/"], "rose"),
        ((930, 760, 1260, 910), "chatbot-service:8000", ["/api/chat/"], "purple"),
    ]
    for xy, title, body, fill in routes:
        box(d, xy, title, body, fill)
        arrow(d, (950, 250), ((xy[0] + xy[2]) / 2, xy[1]))
    save(img, "ecom_gateway_routing.png")


def checkout_sequence():
    img, d = canvas(2200, 1100, "Checkout Sequence")
    xs = [130, 470, 810, 1150, 1490, 1830]
    labels = ["Browser", "Gateway", "user_service", "order_service", "payment_service", "shipping_service"]
    fills = ["white", "green", "blue", "yellow", "rose", "rose"]
    for x, label, fill in zip(xs, labels, fills):
        box(d, (x - 130, 130, x + 130, 220), label, [], fill)
        d.line((x, 220, x, 980), fill="#94a3b8", width=2)
    steps = [
        (0, 1, 300, "POST /customer/checkout/"),
        (1, 2, 370, "route to user_service"),
        (2, 3, 445, "POST /api/checkout/ + X-Internal-Key"),
        (3, 4, 520, "POST /api/payments/ pending"),
        (3, 5, 600, "POST /api/shipments/ pending"),
        (3, 2, 705, "order + snapshots"),
        (2, 1, 790, "render order page"),
        (1, 0, 865, "checkout result"),
    ]
    for a, b, y, label in steps:
        dashed = a > b
        arrow(d, (xs[a], y), (xs[b], y), label, dashed=dashed)
    save(img, "ecom_checkout_sequence.png")


def ai_pipeline():
    img, d = canvas(1700, 1250, "Chatbot / AI Pipeline")
    boxes = [
        ((520, 140, 1180, 260), "Input", ["message, current_product, user_context, user_ref"], "white"),
        ((520, 340, 1180, 490), "Behavior Signal", ["BehaviorEvent in PostgreSQL", "model_behavior + model_best.keras"], "purple"),
        ((100, 610, 520, 760), "Sequence Models", ["RNN, LSTM, BiLSTM artifacts", "metrics_comparison.csv"], "purple"),
        ((640, 610, 1060, 760), "RAG Retrieval", ["knowledge_base.json", "product + FAQ documents"], "blue"),
        ((1180, 610, 1600, 760), "Neo4j Graph Context", ["User-Behavior-Category-Product", "optional fallback"], "green"),
        ((520, 870, 1180, 1020), "Hybrid Ranking + LLM", ["recommend_products()", "Gemma/Gemini or rule-based fallback"], "yellow"),
        ((520, 1100, 1180, 1200), "Response", ["answer, recommendations, citations, source, fallback_used"], "white"),
    ]
    for xy, title, body, fill in boxes:
        box(d, xy, title, body, fill)
    arrow(d, (850, 260), (850, 340))
    arrow(d, (760, 490), (310, 610), "category distribution")
    arrow(d, (850, 490), (850, 610), "preferred categories")
    arrow(d, (940, 490), (1390, 610), "user/category ids")
    arrow(d, (310, 760), (720, 870), "score")
    arrow(d, (850, 760), (850, 870), "docs")
    arrow(d, (1390, 760), (980, 870), "boosted ids/docs")
    arrow(d, (850, 1020), (850, 1100))
    save(img, "ecom_ai_pipeline.png")


def main():
    context_map()
    system_architecture()
    database_mapping()
    class_diagram()
    gateway_routing()
    checkout_sequence()
    ai_pipeline()


if __name__ == "__main__":
    main()
