case "$1" in
e)	vi -p main.py
	;;
i)	/usr/local/venv/bin/pip3 install -r requirements.txt
	;;
deps)	docker exec -it --user root claude ./deps.bash
	;;
"")	export OPENAI_API_KEY=$(cat ~/.openai.key)
	/usr/local/venv/bin/python3 main.py
	;;
esac
