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

from webnotes.utils import cint, cstr, getdate, now, nowdate, get_defaults
from webnotes.model.doc import Document, addchild
from webnotes.model.code import get_obj
from webnotes import session, form, msgprint

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
	
	def setup_account(self, args):
		import webnotes, json
		args = json.loads(args)
		webnotes.conn.begin()

		self.update_profile_name(args)
		add_all_roles_to(webnotes.session.user)
		self.create_fiscal_year_and_company(args)
		self.set_defaults(args)
		create_territories()
		self.create_price_lists(args)
		self.create_feed_and_todo()
		self.create_email_digest()

		webnotes.clear_cache()
		msgprint("Company setup is complete. This page will be refreshed in a moment.")
		webnotes.conn.commit()

		return {
			'sys_defaults': get_defaults(), 
			'user_fullname': (args.get('first_name') or '') + (args.get('last_name')
					and (" " + args.get('last_name')) or '')
		}
	
	def update_profile_name(self, args):
		args['name'] = webnotes.session.get('user')

		# Update Profile
		if not args.get('last_name') or args.get('last_name')=='None': args['last_name'] = None
		webnotes.conn.sql("""\
			UPDATE `tabProfile` SET first_name=%(first_name)s,
			last_name=%(last_name)s
			WHERE name=%(name)s AND docstatus<2""", args)
	
	def create_fiscal_year_and_company(self, args):
		curr_fiscal_year, fy_start_date, fy_abbr = self.get_fy_details(args.get('fy_start'))
		# Fiscal Year
		webnotes.bean([{
			"doctype":"Fiscal Year",
			'year': curr_fiscal_year,
			'year_start_date': fy_start_date,
		}]).insert()
		
		# Company
		webnotes.bean([{
			"doctype":"Company",
			'company_name':args.get('company_name'),
			'abbr':args.get('company_abbr'),
			'default_currency':args.get('currency')
		}]).insert()
		
		self.curr_fiscal_year = curr_fiscal_year
	
	def create_price_lists(self, args):
		webnotes.bean({
			'doctype': 'Price List', 
			'price_list_name': 'Standard Selling',
			"buying_or_selling": "Selling",
			"currency": args["currency"]
		}).insert(),
		webnotes.bean({
			'doctype': 'Price List', 
			'price_list_name': 'Standard Buying',
			"buying_or_selling": "Buying",
			"currency": args["currency"]
		}).insert(),
	
	def set_defaults(self, args):
		# enable default currency
		webnotes.conn.set_value("Currency", args.get("currency"), "enabled", 1)
		
		global_defaults = webnotes.bean("Global Defaults", "Global Defaults")
		global_defaults.doc.fields.update({
			'current_fiscal_year': self.curr_fiscal_year,
			'default_currency': args.get('currency'),
			'default_company':args.get('company_name'),
			'date_format': webnotes.conn.get_value("Country", args.get("country"), "date_format"),
			'emp_created_by':'Naming Series',
			"float_precision": 4
		})
		global_defaults.save()
		
		webnotes.conn.set_value("Accounts Settings", None, "auto_inventory_accounting", 1)
		webnotes.conn.set_default("auto_inventory_accounting", 1)

		stock_settings = webnotes.bean("Stock Settings")
		stock_settings.doc.item_naming_by = "Item Code"
		stock_settings.doc.valuation_method = "FIFO"
		stock_settings.doc.stock_uom = "Nos"
		stock_settings.doc.auto_indent = 1
		stock_settings.save()
		
		selling_settings = webnotes.bean("Selling Settings")
		selling_settings.doc.cust_master_name = "Customer Name"
		selling_settings.doc.so_required = "No"
		selling_settings.doc.dn_required = "No"
		selling_settings.save()

		buying_settings = webnotes.bean("Buying Settings")
		buying_settings.doc.supp_master_name = "Supplier Name"
		buying_settings.doc.po_required = "No"
		buying_settings.doc.pr_required = "No"
		buying_settings.doc.maintain_same_rate = 1
		buying_settings.save()

		notification_control = webnotes.bean("Notification Control")
		notification_control.doc.quotation = 1
		notification_control.doc.sales_invoice = 1
		notification_control.doc.purchase_order = 1
		notification_control.save()

		# control panel
		cp = webnotes.doc("Control Panel", "Control Panel")
		for k in ['industry', 'country', 'timezone', 'company_name']:
			cp.fields[k] = args[k]
			
		cp.save()
			
	def create_feed_and_todo(self):
		"""update activty feed and create todo for creation of item, customer, vendor"""
		import home
		home.make_feed('Comment', 'ToDo', '', webnotes.session['user'],
			'<i>"' + 'Setup Complete. Please check your <a href="#!todo">\
			To Do List</a>' + '"</i>', '#6B24B3')

		d = Document('ToDo')
		d.description = '<a href="#Setup">Complete ERPNext Setup</a>'
		d.priority = 'High'
		d.date = nowdate()
		d.save(1)

	def create_email_digest(self):
		"""
			create a default weekly email digest
			* Weekly Digest
			* For all companies
			* Recipients: System Managers
			* Full content
			* Enabled by default
		"""
		import webnotes
		companies_list = webnotes.conn.sql("SELECT company_name FROM `tabCompany`", as_list=1)

		from webnotes.profile import get_system_managers
		system_managers = get_system_managers()
		if not system_managers: return
		
		from webnotes.model.doc import Document
		for company in companies_list:
			if company and company[0]:
				edigest = Document('Email Digest')
				edigest.name = "Default Weekly Digest - " + company[0]
				edigest.company = company[0]
				edigest.frequency = 'Weekly'
				edigest.recipient_list = "\n".join(system_managers)
				for f in ['new_leads', 'new_enquiries', 'new_quotations',
						'new_sales_orders', 'new_purchase_orders',
						'new_transactions', 'payables', 'payments',
						'expenses_booked', 'invoiced_amount', 'collections',
						'income', 'bank_balance', 'stock_below_rl',
						'income_year_to_date', 'enabled']:
					edigest.fields[f] = 1
				exists = webnotes.conn.sql("""\
					SELECT name FROM `tabEmail Digest`
					WHERE name = %s""", edigest.name)
				if (exists and exists[0]) and exists[0][0]:
					continue
				else:
					edigest.save(1)
		
	# Get Fiscal year Details
	# ------------------------
	def get_fy_details(self, fy_start):
		st = {'1st Jan':'01-01','1st Apr':'04-01','1st Jul':'07-01', '1st Oct': '10-01'}
		curr_year = getdate(nowdate()).year
		if cint(getdate(nowdate()).month) < cint((st[fy_start].split('-'))[0]):
			curr_year = getdate(nowdate()).year - 1
		stdt = cstr(curr_year)+'-'+cstr(st[fy_start])
		#eddt = sql("select DATE_FORMAT(DATE_SUB(DATE_ADD('%s', INTERVAL 1 YEAR), INTERVAL 1 DAY),'%%d-%%m-%%Y')" % (stdt.split('-')[2]+ '-' + stdt.split('-')[1] + '-' + stdt.split('-')[0]))
		if(fy_start == '1st Jan'):
			fy = cstr(getdate(nowdate()).year)
			abbr = cstr(fy)[-2:]
		else:
			fy = cstr(curr_year) + '-' + cstr(curr_year+1)
			abbr = cstr(curr_year)[-2:] + '-' + cstr(curr_year+1)[-2:]
		return fy, stdt, abbr
			
	def create_profile(self, user_email, user_fname, user_lname, pwd=None):
		pr = Document('Profile')
		pr.first_name = user_fname
		pr.last_name = user_lname
		pr.name = pr.email = user_email
		pr.enabled = 1
		pr.save(1)
		if pwd:
			webnotes.conn.sql("""insert into __Auth (user, `password`) 
				values (%s, password(%s)) 
				on duplicate key update `password`=password(%s)""", 
				(user_email, pwd, pwd))
				
		add_all_roles_to(pr.name)
				
def add_all_roles_to(name):
	profile = webnotes.doc("Profile", name)
	for role in webnotes.conn.sql("""select name from tabRole"""):
		if role[0] not in ["Administrator", "Guest", "All", "Customer", "Supplier", "Partner"]:
			d = profile.addchild("user_roles", "UserRole")
			d.role = role[0]
			d.insert()
			
def create_territories():
	"""create two default territories, one for home country and one named Rest of the World"""
	from setup.utils import get_root_of
	country = webnotes.conn.get_value("Control Panel", None, "country")
	root_territory = get_root_of("Territory")
	for name in (country, "Rest Of The World"):
		if not webnotes.conn.exists("Territory", name):
			webnotes.bean({
				"doctype": "Territory",
				"territory_name": name,
				"parent_territory": root_territory,
				"is_group": "No"
			}).insert()
		
