import webnotes
import json
from webnotes.utils import flt

def execute():
	for doctype in ["Purchase Taxes and Charges", "Sales Taxes and Charges"]:
		for tax_name, item_wise_tax_detail in \
			webnotes.conn.sql("""select name, item_wise_tax_detail from `tab%s`""" % doctype):
				if not item_wise_tax_detail or not isinstance(item_wise_tax_detail, basestring):
					continue
				
				try:
					json.loads(item_wise_tax_detail)
				except ValueError:
					out = {}
					for t in item_wise_tax_detail.split("\n"):
						if ":" in t:
							account_head, amount = t.split(":")
							out[account_head.strip()] = flt(amount.strip())
							
					if out:
						webnotes.conn.sql("""update `tab%s` set item_wise_tax_detail=%s
							where name=%s""" % (doctype, "%s", "%s"), (json.dumps(out), tax_name))