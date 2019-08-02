## Automate local deployment from a checkout


# OS-specific support
PYTHON_BIN_DIR = bin
ifeq ($(OS),Windows_NT)
PYTHON_BIN_DIR = Scripts
PYTHON_EXT = .exe
endif


## Top-level targets

.PHONY: default
default: .venv/$(PYTHON_BIN_DIR)/guessit$(PYTHON_EXT)
	.venv/$(PYTHON_BIN_DIR)/python$(PYTHON_EXT) manual.py -h


## Real targets

.venv/$(PYTHON_BIN_DIR)/guessit$(PYTHON_EXT): .venv setup.py requirements.txt
	.venv/$(PYTHON_BIN_DIR)/pip install -r requirements.txt
	touch "$(@)"

.venv:
	virtualenv "$(@)"
