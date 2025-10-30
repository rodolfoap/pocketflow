case "$1" in
e)	vi -p .x
	;;
deps)	docker exec -it --user root claude ./deps.bash
	;;
"")	true
	;;
esac
