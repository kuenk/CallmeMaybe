PYTHON = python3
BIN = $(VENV)/bin
PIP = $(BIN)/pip
BUILD_TOOL = $(BIN)/python3 -m build

all: run

$(VENV):
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip

#install: $(VENV)
#	$(PIP) install -r requirements.txt

run:
	$(BIN)/python3 -m mazegen.a_maze_ing || true

debug: install
	$(BIN)/python3 -m pdb a_maze_ing.py

clean:
	@echo "Cleaning python cache..."
	@rm -rf $(VENV)
	@rm -rf .mypy_cache .pytest_cache
	@echo "Removing extra .txt files (excluding requirements.txt, readme.txt, config.txt)..."
	@find . -type f -name '*.txt' \
		-not -path './.venv/*' \
		-not -name 'requirements.txt' \
		-not -name 'readme.txt' \
		-not -name 'config.txt' -print -exec rm -f {} + || true

lint: install
	@echo "--- RUNNING FLAKE8 ---"
	@$(BIN)/flake8 . --exclude .venv,venv
	@echo "--- RUNNING MYPY ---"
	@$(BIN)/mypy . --explicit-package-bases

lint-strict: install
	@echo "--- RUNNING FLAKE8 (STRICT) ---"
	@$(BIN)/flake8 . --exclude=$(VENV),venv --max-line-length=88 --statistics
	@echo "--- RUNNING MYPY (STRICT MODE) ---"
	@$(BIN)/mypy . \
		--strict \
		--disallow-untyped-defs \
		--check-untyped-defs \
		--warn-return-any \
		--warn-unused-ignores \
		--ignore-missing-imports

.PHONY: all install run lint lint-strict clean debug