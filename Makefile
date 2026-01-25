.PHONY: help install test lint format deploy clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt
	pip install pytest pytest-cov pytest-mock moto black flake8 mypy

test: ## Run tests
	pytest tests/ -v --cov=src/lambda --cov-report=term --cov-report=html

test-integration: ## Run integration tests
	pytest tests/integration/ -v --tb=short

lint: ## Run linters
	flake8 src/ tests/ --max-line-length=120
	black --check src/ tests/
	mypy src/lambda/ --ignore-missing-imports

format: ## Format code
	black src/ tests/

package: ## Package Lambda functions
	cd src/lambda && \
	pip install -r ../../requirements.txt -t . --upgrade && \
	zip -r ../../lambda_package.zip . -x "*.pyc" -x "__pycache__/*" -x "*.dist-info/*"

terraform-init: ## Initialize Terraform
	cd terraform && terraform init

terraform-plan: ## Plan Terraform changes
	@if [ -z "$(S3_BUCKET_NAME)" ]; then echo "Error: S3_BUCKET_NAME not set"; exit 1; fi
	@if [ -z "$(GDRIVE_FOLDER_ID)" ]; then echo "Error: GDRIVE_FOLDER_ID not set"; exit 1; fi
	cd terraform && terraform plan \
		-var="s3_bucket_name=$(S3_BUCKET_NAME)" \
		-var="gdrive_folder_id=$(GDRIVE_FOLDER_ID)" \
		-var="environment=$(ENVIRONMENT)"

terraform-apply: ## Apply Terraform changes
	cd terraform && terraform apply

deploy: package ## Deploy to AWS
	./scripts/deploy.sh

setup-google: ## Setup Google Drive authentication
	./scripts/setup_google_auth.sh $(SERVICE_ACCOUNT_KEY)

invoke-webhook: ## Test webhook handler locally
	aws lambda invoke \
		--function-name gdrive-webhook-webhook-handler-$(ENVIRONMENT) \
		--payload file://tests/fixtures/webhook_payload.json \
		/tmp/response.json && \
	cat /tmp/response.json | jq .

invoke-renewal: ## Trigger channel renewal
	aws lambda invoke \
		--function-name gdrive-webhook-channel-renewal-$(ENVIRONMENT) \
		--payload '{}' \
		/tmp/response.json && \
	cat /tmp/response.json | jq .

logs-webhook: ## Tail webhook handler logs
	aws logs tail /aws/lambda/gdrive-webhook-webhook-handler-$(ENVIRONMENT) --follow

logs-renewal: ## Tail channel renewal logs
	aws logs tail /aws/lambda/gdrive-webhook-channel-renewal-$(ENVIRONMENT) --follow

clean: ## Clean build artifacts
	rm -rf __pycache__ .pytest_cache .coverage htmlcov/
	rm -f lambda_package.zip
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

destroy: ## Destroy Terraform infrastructure
	@echo "WARNING: This will destroy all infrastructure!"
	@read -p "Are you sure? (yes/no): " confirm && [ "$$confirm" = "yes" ] || exit 1
	cd terraform && terraform destroy

# Default values
ENVIRONMENT ?= dev
