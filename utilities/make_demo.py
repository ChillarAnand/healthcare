# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

import webnotes, os, datetime
import webnotes.utils
from webnotes.widgets import query_report
import random
import json

webnotes.session = webnotes._dict({"user":"Administrator"})
from core.page.data_import_tool.data_import_tool import upload

# fix price list
# fix fiscal year

company = "Wind Power LLC"
start_date = '2010-01-01'
runs_for = 20
prob = {
	"Quotation": { "make": 0.5, "qty": (1,5) },
	"Sales Order": { "make": 0.5, "qty": (1,4) },
	"Supplier Quotation": { "make": 0.5, "qty": (1, 3) }
}

def make():
	webnotes.connect()
	webnotes.print_messages = True
	webnotes.mute_emails = True
	
	#setup()
	simulate()
	
def setup():
	install()
	complete_setup()
	make_customers_suppliers_contacts()
	make_items()
	make_users_and_employees()
	# make_opening_stock()
	# make_opening_accounts()

def simulate():
	current_date = None
	for i in xrange(runs_for):
		print i
		if not current_date:
			current_date = webnotes.utils.getdate(start_date)
		else:
			current_date = webnotes.utils.add_days(current_date, 1)
			
		if current_date.weekday() in (5, 6):
			continue

		run_sales(current_date)
		run_purchase(current_date)
		run_manufacturing(current_date)
		run_stock(current_date)
		
	webnotes.conn.commit()

def run_sales(current_date):
	if can_make("Quotation"):
		for i in xrange(how_many("Quotation")):
			make_quotation(current_date)
					
	if can_make("Sales Order"):
		for i in xrange(how_many("Sales Order")):
			make_sales_order(current_date)

def run_stock(current_date):
	pass
	# make purchase requests
	
	# make delivery notes (if possible)
	
	# make stock entry (from production order)

def run_purchase(current_date):
	# make supplier quotations
	if can_make("Supplier Quotation"):
		from stock.doctype.material_request.material_request import make_supplier_quotation
		report = "Material Requests for which Supplier Quotations are not created"
		for row in query_report.run(report)["result"][:how_many("Supplier Quotation")]:
			if row[0] != "Total":
				sq = webnotes.bean(make_supplier_quotation(row[0]))
				sq.doc.transaction_date = current_date
				sq.doc.fiscal_year = "2010"
				sq.insert()
				sq.submit()
		
	# make purchase orders
	if can_make("Purchase Order"):
		from stock.doctype.material_request.material_request import make_purchase_order
		report = "Requested Items To Be Ordered"
		for row in query_report.run(report)["result"][:how_many("Purchase Order")]:
			if row[0] != "Total":
				po = webnotes.bean(make_purchase_order(row[0]))
				po.doc.transaction_date = current_date
				po.doc.fiscal_year = "2010"
				po.insert()
				po.submit()
			
def run_manufacturing(current_date):
	ppt = webnotes.bean("Production Planning Tool", "Production Planning Tool")
	ppt.doc.company = company
	ppt.doc.use_multi_level_bom = 1
	ppt.doc.purchase_request_for_warehouse = "Stores - WP"
	ppt.run_method("get_open_sales_orders")
	ppt.run_method("get_items_from_so")
	ppt.run_method("raise_production_order")
	ppt.run_method("raise_purchase_request")
	
	# submit production orders
	for pro in webnotes.conn.get_values("Production Order", {"docstatus": 0}):
		b = webnotes.bean("Production Order", pro[0])
		b.doc.wip_warehouse = "Work in Progress - WP"
		b.submit()
		
	# submit material requests
	for pro in webnotes.conn.get_values("Material Request", {"docstatus": 0}):
		b = webnotes.bean("Material Request", pro[0])
		b.submit()
	
def make_quotation(current_date):
	b = webnotes.bean([{
		"creation": current_date,
		"doctype": "Quotation",
		"quotation_to": "Customer",
		"customer": get_random("Customer"),
		"order_type": "Sales",
		"transaction_date": current_date,
		"fiscal_year": "2010"
	}])
	
	add_random_children(b, {
		"doctype": "Quotation Item", 
		"parentfield": "quotation_details", 
	}, rows=3, randomize = {
		"qty": (1, 5),
		"item_code": ("Item", {"is_sales_item": "Yes"})
	}, unique="item_code")
	
	b.insert()
	b.submit()
	
def make_sales_order(current_date):
	q = get_random("Quotation", {"status": "Submitted"})
	if q:
		from selling.doctype.quotation.quotation import make_sales_order
		so = webnotes.bean(make_sales_order(q))
		so.doc.transaction_date = current_date
		so.doc.delivery_date = webnotes.utils.add_days(current_date, 10)
		so.insert()
		so.submit()
	
def add_random_children(bean, template, rows, randomize, unique=None):
	for i in xrange(random.randrange(1, rows)):
		d = template.copy()
		for key, val in randomize.items():
			if isinstance(val[0], basestring):
				d[key] = get_random(*val)
			else:
				d[key] = random.randrange(*val)
		
		if unique:
			if not bean.doclist.get({"doctype": d["doctype"], unique:d[unique]}):
				bean.doclist.append(d)
		else:
			bean.doclist.append(d)

def get_random(doctype, filters=None):
	condition = []
	if filters:
		for key, val in filters.items():
			condition.append("%s='%s'" % (key, val))
	if condition:
		condition = " where " + " and ".join(condition)
	else:
		condition = ""
		
	out = webnotes.conn.sql("""select name from `tab%s` %s
		order by RAND() limit 0,1""" % (doctype, condition))

	return out and out[0][0] or None

def can_make(doctype):
	return random.random() < prob.get(doctype, {"make": 0.5})["make"]

def how_many(doctype):
	return random.randrange(*prob.get(doctype, {"qty": (1, 3)})["qty"])

def install():
	print "Creating Fresh Database..."
	from webnotes.install_lib.install import Installer
	inst = Installer('root')
	inst.import_from_db("demo", verbose = 1)

def complete_setup():
	print "Complete Setup..."
	webnotes.get_obj("Setup Control").setup_account({
		"first_name": "Test",
		"last_name": "User",
		"fy_start": "1st Jan",
		"industry": "Manufacturing",
		"company_name": company,
		"company_abbr": "WP",
		"currency": "USD",
		"timezone": "America/New York",
		"country": "United States"
	})

	import_data("Fiscal_Year")
	
def make_items():
	import_data(["Item", "Item_Price"])
	import_data("BOM", submit=True)
	
def make_customers_suppliers_contacts():
	import_data(["Customer", "Supplier", "Contact", "Address", "Lead"])

def make_users_and_employees():
	webnotes.conn.set_value("HR Settings", None, "emp_created_by", "Naming Series")
	webnotes.conn.commit()
	
	import_data(["Profile", "Employee", "Salary_Structure"])
	
def import_data(dt, submit=False):
	if not isinstance(dt, (tuple, list)):
		dt = [dt]
	
	for doctype in dt:
		print "Importing", doctype.replace("_", " "), "..."
		webnotes.form_dict = {}
		if submit:
			webnotes.form_dict["params"] = json.dumps({"_submit": 1})
		webnotes.uploaded_file = os.path.join(os.path.dirname(__file__), "demo_docs", doctype+".csv")
		upload()

if __name__=="__main__":
	make()