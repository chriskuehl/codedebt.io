VENV := venv
BIN := $(VENV)/bin

.PHONY: minimal
minimal: $(VENV)

$(VENV): setup.py requirements.txt requirements-dev.txt
	vendor/venv-update venv= -ppython3 venv install= -r requirements.txt -r requirements-dev.txt

.PHONY: test
test: $(VENV)
	$(BIN)/pre-commit install -f --install-hooks
	$(BIN)/pre-commit run --all-files

.PHONY: update-requirements
update-requirements:
	$(eval TMP := $(shell mktemp -d))
	python vendor/venv-update venv= $(TMP) -ppython3 install= -r requirements-minimal.txt
	. $(TMP)/bin/activate && \
		pip freeze | sort | grep -vE '^(wheel|venv-update|virtualenv|codedebt-io)==' > requirements.txt
	rm -rf $(TMP)
