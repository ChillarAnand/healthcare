# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
from webnotes import msgprint, _
from webnotes.utils import flt, cint, comma_and
import json

def get_customer_list(doctype, txt, searchfield, start, page_len, filters):
	if webnotes.conn.get_default("cust_master_name") == "Customer Name":
		fields = ["name", "customer_group", "territory"]
	else:
		fields = ["name", "customer_name", "customer_group", "territory"]
		
	return webnotes.conn.sql("""select %s from `tabCustomer` where docstatus < 2 
		and (%s like %s or customer_name like %s) order by 
		case when name like %s then 0 else 1 end,
		case when customer_name like %s then 0 else 1 end,
		name, customer_name limit %s, %s""" % 
		(", ".join(fields), searchfield, "%s", "%s", "%s", "%s", "%s", "%s"), 
		("%%%s%%" % txt, "%%%s%%" % txt, "%%%s%%" % txt, "%%%s%%" % txt, start, page_len))
		
@webnotes.whitelist()
def get_item_details(args):
	"""
		args = {
			"item_code": "",
			"warehouse": None,
			"customer": "",
			"conversion_rate": 1.0,
			"price_list_name": None,
			"price_list_currency": None,
			"plc_conversion_rate": 1.0
		}
	"""
	if isinstance(args, basestring):
		args = json.loads(args)
	args = webnotes._dict(args)
	
	if args.barcode:
		args.item_code = _get_item_code(args.barcode)
	
	item_bean = webnotes.bean("Item", args.item_code)
	
	_validate_item_details(args, item_bean.doc)
	
	out = _get_basic_details(args, item_bean)
	
	meta = webnotes.get_doctype(args.doctype)
	if meta.get_field("currency"):
		out.base_ref_rate = out.basic_rate = out.ref_rate = out.export_rate = 0.0
		
		if args.price_list_name and args.price_list_currency:
			out.update(_get_price_list_rate(args, item_bean, meta))
	
	if out.warehouse or out.reserved_warehouse:
		out.update(get_available_qty(args.item_code, out.warehouse or out.reserved_warehouse))
	
	out.customer_item_code = _get_customer_item_code(args, item_bean)
	
	if cint(args.is_pos):
		pos_settings = get_pos_settings(args.company)
		out.update(apply_pos_settings(pos_settings, out))
	
	return out
	
def _get_item_code(barcode):
	item_code = webnotes.conn.sql_list("""select name from `tabItem` where barcode=%s""", barcode)
			
	if not item_code:
		msgprint(_("No Item found with Barcode") + ": %s" % barcode, raise_exception=True)
	
	elif len(item_code) > 1:
		msgprint(_("Items") + " %s " % comma_and(item_code) + 
			_("have the same Barcode") + " %s" % barcode, raise_exception=True)
	
	return item_code[0]
	
def _validate_item_details(args, item):
	from utilities.transaction_base import validate_item_fetch
	validate_item_fetch(args, item)
	
	# validate if sales item or service item
	if args.order_type == "Maintenance":
		if item.is_service_item != "Yes":
			msgprint(_("Item") + (" %s: " % item.name) + 
				_("not a service item.") +
				_("Please select a service item or change the order type to Sales."), 
				raise_exception=True)
		
	elif item.is_sales_item != "Yes":
		msgprint(_("Item") + (" %s: " % item.name) + _("not a sales item"),
			raise_exception=True)
			
def _get_basic_details(args, item_bean):
	item = item_bean.doc
	out = webnotes._dict({
			"item_code": item.name,
			"description": item.description_html or item.description,
			"reserved_warehouse": item.default_warehouse or args.warehouse or args.reserved_warehouse,
			"warehouse": item.default_warehouse or args.warehouse,
			"income_account": item.default_income_account or args.income_account,
			"expense_account": item.purchase_account or args.expense_account,
			"cost_center": item.default_sales_cost_center or args.cost_center,
			"qty": 1.0,
			"adj_rate": 0.0,
			"export_amount": 0.0,
			"amount": 0.0,
			"batch_no": None,
			"item_tax_rate": json.dumps(dict(([d.tax_type, d.tax_rate] for d in 
				item_bean.doclist.get({"parentfield": "item_tax"})))),
		})
	
	for fieldname in ("item_name", "item_group", "barcode", "brand", "stock_uom"):
		out[fieldname] = item.fields.get(fieldname)
			
	return out
	
def _get_price_list_rate(args, item_bean, meta):
	base_ref_rate = item_bean.doclist.get({
		"parentfield": "ref_rate_details",
		"price_list_name": args.price_list_name, 
		"price_list_currency": args.price_list_currency,
		"buying_or_selling": "Selling"})
	
	if not base_ref_rate:
		return {}
	
	# found price list rate - now we can validate
	from utilities.transaction_base import validate_currency
	validate_currency(args, item_bean.doc, meta)
	
	return {"ref_rate": flt(base_ref_rate[0].ref_rate * args.plc_conversion_rate / args.conversion_rate)}

@webnotes.whitelist()
def get_available_qty(item_code, warehouse):
	return webnotes.conn.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, 
		["projected_qty", "actual_qty"], as_dict=True) or {}
		
def _get_customer_item_code(args, item_bean):
	customer_item_code = item_bean.doclist.get({"parentfield": "item_customer_details",
		"customer_name": args.customer})
	
	return customer_item_code and customer_item_code[0].ref_code or None
	
def get_pos_settings(company):
	pos_settings = webnotes.conn.sql("""select * from `tabPOS Setting` where user = %s 
		and company = %s""", (webnotes.session['user'], company), as_dict=1)
		
	if not pos_settings:
		pos_settings = webnotes.conn.sql("""select * from `tabPOS Setting` 
			where ifnull(user,'') = '' and company = %s""", company, as_dict=1)

	return pos_settings and pos_settings[0] or None
	
def apply_pos_settings(pos_settings, opts):
	out = {}
	
	for fieldname in ("income_account", "cost_center", "warehouse", "expense_account"):
		if not opts.get(fieldname):
			out[fieldname] = pos_settings.get(fieldname)
			
	if out.get("warehouse"):
		out["actual_qty"] = get_available_qty(opts.item_code, out.get("warehouse")).get("actual_qty")
	
	return out
