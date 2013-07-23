import webnotes
import os

def execute():
	from webnotes.utils import get_base_path
	website_py = os.path.join(get_base_path(), "app", "startup", "website.py")
	website_pyc = os.path.join(get_base_path(), "app", "startup", "website.pyc")
	if not os.path.exists(website_py) and os.path.exists(website_pyc):
		os.remove(website_pyc)