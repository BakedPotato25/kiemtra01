param(
    [int]$MaxProducts = 160,
    [switch]$KeepCustomerCopy,
    [switch]$SkipBehaviorTrain
)

$ErrorActionPreference = "Stop"

Write-Host "[1/6] Building chatbot KB inside container..."
docker compose exec chatbot_service python manage.py build_chat_kb --max-products $MaxProducts

if (-not $SkipBehaviorTrain) {
    Write-Host "[2/6] Training behavior model inside container..."
    docker compose exec chatbot_service python manage.py train_behavior_model --epochs 120 --lr 0.02
} else {
    Write-Host "[2/6] Skipping behavior model training (SkipBehaviorTrain=true)."
}

Write-Host "[3/6] Ensuring local chatbot artifacts folder exists..."
$chatbotArtifacts = "services/chatbot_service/chatbot/artifacts"
if (-not (Test-Path $chatbotArtifacts)) {
    New-Item -Path $chatbotArtifacts -ItemType Directory -Force | Out-Null
}

Write-Host "[4/6] Syncing knowledge_base.json to local chatbot_service..."
docker compose cp chatbot_service:/app/chatbot/artifacts/knowledge_base.json "$chatbotArtifacts/knowledge_base.json"

Write-Host "[5/6] Syncing model_behavior.json to local chatbot_service..."
docker compose cp chatbot_service:/app/chatbot/artifacts/model_behavior.json "$chatbotArtifacts/model_behavior.json"

$customerArtifacts = "services/customer_service/customer/artifacts"
$customerKb = "$customerArtifacts/knowledge_base.json"
if (-not $KeepCustomerCopy) {
    Write-Host "[6/6] Removing customer_service KB copy for strict separation..."
    if (Test-Path $customerKb) {
        Remove-Item $customerKb -Force
    }
    if (Test-Path $customerArtifacts) {
        $remaining = Get-ChildItem -Path $customerArtifacts -ErrorAction SilentlyContinue
        if (-not $remaining) {
            Remove-Item $customerArtifacts -Force
        }
    }
} else {
    Write-Host "[6/6] Keeping customer_service KB copy as requested."
}

Write-Host "Done. Artifacts synced:"
Write-Host "- $chatbotArtifacts/knowledge_base.json"
Write-Host "- $chatbotArtifacts/model_behavior.json"
