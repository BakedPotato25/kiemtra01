from django.core.management.base import BaseCommand

from chatbot.behavior_ai import TRAINING_DATA_PATH, train_and_save_behavior_model


class Command(BaseCommand):
    help = "Train and save model_behavior artifact for chatbot_service"

    def add_arguments(self, parser):
        parser.add_argument("--epochs", type=int, default=120)
        parser.add_argument("--lr", type=float, default=0.02)

    def handle(self, *args, **options):
        epochs = max(10, int(options.get("epochs") or 120))
        lr = float(options.get("lr") or 0.02)

        payload = train_and_save_behavior_model(epochs=epochs, lr=lr)
        metrics = payload.get("metrics") or {}

        self.stdout.write(self.style.SUCCESS("model_behavior trained and saved."))
        self.stdout.write(f"samples={metrics.get('samples', 0)}")
        self.stdout.write(f"loss={metrics.get('loss')}")
        self.stdout.write(f"training_data_file={TRAINING_DATA_PATH}")
