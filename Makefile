.PHONY: style

PYTHON := python3
CHECK_DIRS := bilibili blog buildmd proxy util

style:
	black $(CHECK_DIRS)
	isort $(CHECK_DIRS)
	flake8 $(CHECK_DIRS)