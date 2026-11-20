REGION ?= us-east-1
STACK  ?= orders-api
ALARM_EMAIL ?=

.PHONY: test lint deploy smoke agent-space budget destroy

test:
	python3 -m pytest -q tests

lint:
	cfn-lint template.yaml

deploy:
	sam build
	sam deploy --stack-name $(STACK) --region $(REGION) \
	  --capabilities CAPABILITY_IAM --resolve-s3 --no-confirm-changeset \
	  --tags app=orders-api environment=lab \
	  $(if $(ALARM_EMAIL),--parameter-overrides AlarmEmail=$(ALARM_EMAIL),)

smoke:
	python3 scripts/smoke_test.py $$(aws cloudformation describe-stacks \
	  --stack-name $(STACK) --region $(REGION) \
	  --query "Stacks[0].Outputs[?OutputKey=='OrdersEndpoint'].OutputValue" \
	  --output text) 5

agent-space:
	REGION=$(REGION) ./scripts/create-agent-space.sh

budget:
	./scripts/create-budget.sh

destroy:
	REGION=$(REGION) ./scripts/destroy.sh
