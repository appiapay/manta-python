# -*- coding: utf-8 -*-

NIX := $(shell which nix)
export TOPDIR := $(CURDIR)
export VENVDIR := $(TOPDIR)/venv
export SYS_PYTHON := $(shell which python3.7)

ifeq ($(NIX),)
	export PYTHON := $(VENVDIR)/bin/python
else
	export PYTHON := $(SYS_PYTHON)
endif
export SHELL := $(shell which bash)


# This is the default target, when no target is specified on the command line
.PHONY: all
ifneq ($(NIX),)
ifndef IN_NIX_SHELL

all: activate-nix

activate-nix:
	@printf "\nPLEASE ACTIVATE THE ENVIRONMENT USING THE COMMAND \"nix-shell\"\n"
else

VENV_CMD := virtualenv --no-setuptools
all: virtualenv help

endif
else

VENV_CMD := $(SYS_PYTHON) -m venv
all: virtualenv help

endif

ACTIVATE_SCRIPT := $(VENVDIR)/bin/activate
PIP := $(VENVDIR)/bin/pip
REQUIREMENTS ?= requirements-dev.txt
REQUIREMENTS_TIMESTAMP := $(VENVDIR)/$(REQUIREMENTS).timestamp


help::
	@printf "\nVirtualenv\n==========\n"

help::
	@printf "\nvirtualenv\n\tsetup the Python virtualenv and install required packages\n"

.PHONY: virtualenv
virtualenv: $(VENVDIR) requirements

$(VENVDIR):
	@printf "Bootstrapping Python 3 virtualenv...\n"
	@$(VENV_CMD) --prompt $(notdir $(TOPDIR)) $(VENV_EXTRA) $@
	@$(MAKE) -s upgrade-pip

help::
	@printf "\nupgrade-pip\n\tupgrade pip\n"

.PHONY: upgrade-pip
upgrade-pip:
	@printf "Upgrading pip...\n"
	@$(PIP) install --upgrade pip

help::
	@printf "\nrequirements\n\tinstall/update required Python packages\n"

.PHONY: requirements
requirements: $(REQUIREMENTS_TIMESTAMP)

$(REQUIREMENTS_TIMESTAMP): $(REQUIREMENTS)
	@printf "Installing development requirements...\n"
	@PATH=$(TOPDIR)/bin:$(PATH) $(PIP) install -r $(REQUIREMENTS)
	touch $@

distclean::
	rm -rf $(VENVDIR)

help::
	@printf "\nTesting\n=======\n"

help::
	@printf "\ntests\n\trun the configured test\n"

.PHONY: tests
tests: rst-tests type-tests unit-tests

help::
	@printf "\ntype-tests\n\trun the typechecks using mypy\n"

.PHONY: type-tests
type-tests:
	@mypy ./manta
	$(info Running type tests...)

help::
	@printf "\nunit-tests\n\trun the unittests using pytest\n"

.PHONY: unit-tests
unit-tests:
	$(info Running unit and integration tests...)
	@pytest ./tests

help::
	@printf "\nrst-tests\n\tcheck README.rst syntax\n"

.PHONY: rst-tests
	$(info checking README.rst file syntax)
	@rst2html.py README.rst > /dev/null


help::
	@printf "\nDocumentation\n=============\n"

help::
	@printf "\ndocs\n\tcompile the documentation\n"

.PHONY: docs
docs:
	$(info compiling documentation...)
	@cd docs && $(MAKE) html
	$(info index is available at ./docs/_build/html/index.html)

help::
	@printf "\nDistribution\n============\n"

help::
	@printf "\ndist\n\tcreate distribution package\n"

.PHONY: dist
dist:
	$(info generating package...)
	@python setup.py sdist
