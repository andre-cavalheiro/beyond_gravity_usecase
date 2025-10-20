MAKEFLAGS += --no-print-directory --silent

################################################################################
# Makefile Variables
################################################################################
DOCKER_IMAGE = andrecavalheiro/beyond-gravity-usecase-webapp
DOCKERFILE_PATH = ./deploy/Dockerfile

KUBERNETES_CLUSTER = kratos
KUBERNETES_NAMESPACE = beyond-gravity-usecase

################################################################################
# Default
################################################################################
# (...)
.PHONY: start
start:
	@yarn run dev --port 3001

################################################################################
# Setup & Install
################################################################################
# (...)
# Install a package: "yarn add -D @types/canvas-confetti"

################################################################################
# Deploy
################################################################################
.PHONY: deploy
deploy:
	$(MAKE) validate-context && \
	$(MAKE) docker-build-push && \
	$(MAKE) restart-deployment && \
	printf "\nDeployment complete. Would you like to create a new tag? (y/N): "; \
	read confirm; \
	if [ "$$confirm" = "y" ]; then $(MAKE) tag; else echo "Skipping tag creation."; fi

.PHONY: set-context
set-context:
	@kubectl config use-context $(KUBERNETES_CLUSTER) || { echo "Error: Failed to switch to context '$(KUBERNETES_CLUSTER)'."; exit 1; }
	@kubectl config set-context --current --namespace=$(KUBERNETES_NAMESPACE) || { echo "Error: Failed to set namespace '$(KUBERNETES_NAMESPACE)'."; exit 1; }
	@echo "Switched to context '$(KUBERNETES_CLUSTER)' with namespace '$(KUBERNETES_NAMESPACE)'."

.PHONY: validate-context
validate-context:
	@CURRENT_CONTEXT=$$(kubectl config current-context); \
	CURRENT_NAMESPACE=$$(kubectl config view --minify --output 'jsonpath={..namespace}'); \
	if [ "$$CURRENT_CONTEXT" != "$(KUBERNETES_CLUSTER)" ]; then \
		echo "Error: Current context is not '$(KUBERNETES_CLUSTER)'. It is set to '$$CURRENT_CONTEXT'."; \
		exit 1; \
	fi; \
	if [ "$$CURRENT_NAMESPACE" != "$(KUBERNETES_NAMESPACE)" ]; then \
		echo "Error: Current namespace is not '$(KUBERNETES_NAMESPACE)'. It is set to '$$CURRENT_NAMESPACE'."; \
		exit 1; \
	fi

.PHONY: docker-build-push
docker-build-push:
	docker buildx build --platform linux/amd64 \
		-t $(DOCKER_IMAGE):latest \
		-f $(DOCKERFILE_PATH) \
		--push .

.PHONY: push-helm
push-helm:
	@$(MAKE) validate-context
	@helm  upgrade --install beyond-gravity-usecase-webapp ./deploy/helm

.PHONY: restart-deployment
restart-deployment:
	@$(MAKE) validate-context
	@kubectl rollout restart deployment beyond-gravity-usecase-webapp

.PHONY: tag
tag:
	@latest_tag=$$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0"); \
	version=$$(echo $$latest_tag | awk -F. '{print $$1 "." $$2 "." $$3+1}'); \
	if [ -z "$(m)" ]; then \
		printf "Enter a tag message: "; \
		read msg; \
	else \
		msg="$(m)"; \
	fi; \
	echo "Preparing to tag new version: $$version"; \
	printf "Confirm? (y/N): "; \
	read confirm; \
	if [ "$$confirm" != "y" ]; then echo "Aborted."; exit 1; fi; \
	git tag -a $$version -m "$$msg"; \
	git push origin --tags

# kubectl delete secret beyond-gravity-usecase-webapp-env 
# kubectl create secret generic beyond-gravity-usecase-webapp-env --from-env-file=.env.production
# kubectl exec -it beyond-gravity-usecase-webapp-5fd65f6cd9-g8lw2 -- printenv | grep NEXT_PUBLIC