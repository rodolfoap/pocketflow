#!/bin/bash
set -x

#apt-get update
#apt-get install -y python3 python3-pip docker.io
rm -v /usr/lib/python3.11/EXTERNALLY-MANAGED
[ -f "requirements.txt" ] && pip3 install -r requirements.txt
python3 --version
pip3 --version

# meta-llama/Meta-Llama-3.1-70B-Instruct
