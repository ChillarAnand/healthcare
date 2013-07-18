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
"""Global Defaults"""
import webnotes
import webnotes.defaults
from webnotes.utils import cint

keydict = {
	# "key in defaults": "key in Global Defaults"
	"print_style": "print_style",
	"fiscal_year": "current_fiscal_year",
	'company': 'default_company',
	'currency': 'default_currency',
	'hide_currency_symbol':'hide_currency_symbol',
	'date_format': 'date_format',
	'number_format': 'number_format',
	'float_precision': 'float_precision',
	'account_url':'account_url',
	'session_expiry': 'session_expiry',
	'disable_rounded_total': 'disable_rounded_total',
	'maintain_same_sales_rate' : 'maintain_same_sales_rate',
}

class DocType:
	def __init__(self, d, dl):
		self.doc, self.doclist = d, dl
		
	def on_update(self):
		"""update defaults"""
		self.validate_session_expiry()
		
		for key in keydict:
			webnotes.conn.set_default(key, self.doc.fields.get(keydict[key], ''))
			
		# update year start date and year end date from fiscal_year
		ysd = webnotes.conn.sql("""select year_start_date from `tabFiscal Year` 
			where name=%s""", self.doc.current_fiscal_year)
			
		ysd = ysd and ysd[0][0] or ''
		from webnotes.utils import get_first_day, get_last_day
		if ysd:
			webnotes.conn.set_default('year_start_date', ysd.strftime('%Y-%m-%d'))
			webnotes.conn.set_default('year_end_date', \
				get_last_day(get_first_day(ysd,0,11)).strftime('%Y-%m-%d'))
		
		# enable default currency
		if self.doc.default_currency:
			webnotes.conn.set_value("Currency", self.doc.default_currency, "enabled", 1)
		
		# clear cache
		webnotes.clear_cache()
	
	def validate_session_expiry(self):
		if self.doc.session_expiry:
			parts = self.doc.session_expiry.split(":")
			if len(parts)!=2 or not (cint(parts[0]) or cint(parts[1])):
				webnotes.msgprint("""Session Expiry must be in format hh:mm""",
					raise_exception=1)
				
	
	def get_defaults(self):
		return webnotes.defaults.get_defaults()
