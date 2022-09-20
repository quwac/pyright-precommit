.PHONY: init
init:
	-asdf plugin add $$(asdf plugin list all | grep -E "^python ")
	-asdf plugin add $$(asdf plugin list all | grep -E "^poetry ")
	-asdf install $$(cat .tool-versions | grep -E "^python ")
	asdf install
	poetry install
