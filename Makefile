PYTHON ?= python3

.PHONY: test check sync

test:
	$(PYTHON) -m unittest discover -s skills/update-evo-agents/tests -v
	$(PYTHON) -m pytest -q skills/continuous-learning/tests
	$(PYTHON) skills/stop-slop/scripts/test_vietnamese_blacklist.py
	$(PYTHON) -m py_compile install.py setup.py mcp/tts/server.py skills/harness-engineering/scripts/harness.py

check:
	$(PYTHON) install.py --check

sync:
	$(PYTHON) install.py
