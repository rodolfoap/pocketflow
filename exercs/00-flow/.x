case "$1" in
e)	vi -p main.py
	;;
i)	/usr/local/venv/bin/pip3 install -r requirements.txt
	;;
"")	export OPENAI_API_KEY=$(cat ~/.openai.key)
	/usr/local/venv/bin/python3 main.py
	;;
esac
