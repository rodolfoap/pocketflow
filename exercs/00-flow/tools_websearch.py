from ddgs import DDGS
from urllib.request import urlopen, Request
from bs4 import BeautifulSoup
import re
from tools_debug import debug

def cleanup(text):
	text = re.sub('[^a-zA-Z0-9@_,.$£+]', ' ', text).strip()
	text = re.sub("\\n"," ",text)
	text = re.sub("\\t"," ",text)
	text = re.sub("\\s+"," ",text)
	return text

def getpage(url):
	req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
	html = urlopen(req)
	soup = BeautifulSoup(html, 'html.parser')
	for script in soup(["script", "style"]): script.extract()
	return cleanup(soup.get_text())

def websearch(query, max_results=3, crawl=False):
	debug(f'call_llm({query})')
	answers = DDGS().text(query, max_results=max_results)
	if not crawl: return answers
	s=[]
	for r in answers:
		# r has `title`, `body`, `href`, we add `text`
		r['text']=getpage(r['href'])
		s.append(r)
	return s
