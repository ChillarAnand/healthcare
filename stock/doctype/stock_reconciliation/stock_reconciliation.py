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
import json
from webnotes import msgprint, _
from webnotes.utils import cstr, flt
from webnotes.model.controller import DocListController

class DocType(DocListController):
	def validate(self):
		self.validate_data()
		
	def on_submit(self):
		self.insert_stock_ledger_entries()
		
	def on_cancel(self):
		self.delete_stock_ledger_entries()
		
	def validate_data(self):
		data = json.loads(self.doc.reconciliation_json)
		if data[0] != ["Item Code", "Warehouse", "Quantity", "Valuation Rate"]:
			msgprint(_("""Hey! You seem to be using the wrong template. \
				Click on 'Download Template' button to get the correct template."""),
				raise_exception=1)
				
		def _get_msg(row_num, msg):
			return _("Row # ") + ("%d: " % (row_num+2)) + _(msg)
		
		self.validation_messages = []
		item_warehouse_combinations = []
		for row_num, row in enumerate(data[1:]):
			# find duplicates
			if [row[0], row[1]] in item_warehouse_combinations:
				self.validation_messages.append(_get_msg(row_num, "Duplicate entry"))
			else:
				item_warehouse_combinations.append([row[0], row[1]])
			
			self.validate_item(row[0], row_num)
			# note: warehouse will be validated through link validation
			
			# if both not specified
			if row[2] == "" and row[3] == "":
				self.validation_messages.append(_get_msg(row_num,
					"Please specify either Quantity or Valuation Rate or both"))
			
			# do not allow negative quantity
			if flt(row[2]) < 0:
				self.validation_messages.append(_get_msg(row_num, 
					"Negative Quantity is not allowed"))
			
			# do not allow negative valuation
			if flt(row[3]) < 0:
				self.validation_messages.append(_get_msg(row_num, 
					"Negative Valuation Rate is not allowed"))
		
		# throw all validation messages
		if self.validation_messages:
			for msg in self.validation_messages:
				msgprint(msg)
			
			raise webnotes.ValidationError
			
	def validate_item(self, item_code, row_num):
		from stock.utils import validate_end_of_life, validate_is_stock_item, \
			validate_cancelled_item
		
		# using try except to catch all validation msgs and display together
		
		try:
			item = webnotes.doc("Item", item_code)
			
			# end of life and stock item
			validate_end_of_life(item_code, item.end_of_life, verbose=0)
			validate_is_stock_item(item_code, item.is_stock_item, verbose=0)
		
			# item should not be serialized
			if item.has_serial_no == "Yes":
				raise webnotes.ValidationError, (_("Serialized Item: '") + item_code +
					_("""' can not be managed using Stock Reconciliation.\
					You can add/delete Serial No directly, to modify stock of this item."""))
		
			# docstatus should be < 2
			validate_cancelled_item(item_code, item.docstatus, verbose=0)
				
		except Exception, e:
			self.validation_messages.append(_("Row # ") + ("%d: " % (row_num+2)) + cstr(e))
			
	def insert_stock_ledger_entries(self):
		"""	find difference between current and expected entries
			and create stock ledger entries based on the difference"""
		from stock.utils import get_previous_sle, get_valuation_method
			
		row_template = ["item_code", "warehouse", "qty", "valuation_rate"]
		
		data = json.loads(self.doc.reconciliation_json)
		for row_num, row in enumerate(data[1:]):
			row = webnotes._dict(zip(row_template, row))
			
			previous_sle = get_previous_sle({
				"item_code": row.item_code,
				"warehouse": row.warehouse,
				"posting_date": self.doc.posting_date,
				"posting_time": self.doc.posting_time
			})
			
			if get_valuation_method(row.item_code) == "Moving Average":
				self.sle_for_moving_avg(row, previous_sle)
					
			else:
				self.sle_for_fifo(row, previous_sle)
					
	def sle_for_moving_avg(self, row, previous_sle):
		"""Insert Stock Ledger Entries for Moving Average valuation"""
		def _get_incoming_rate(qty, valuation_rate, previous_qty, previous_valuation_rate):
			if previous_valuation_rate == 0:
				return valuation_rate
			else:
				return (qty * valuation_rate - previous_qty * previous_valuation_rate) \
					/ flt(qty - previous_qty)
		
		change_in_qty = row.qty != "" and \
			(flt(row.qty) != flt(previous_sle.get("qty_after_transaction")))

		change_in_rate = row.valuation_rate != "" and \
			(flt(row.valuation_rate) != flt(previous_sle.get("valuation_rate")))
			
		if change_in_qty:
			incoming_rate = _get_incoming_rate(flt(row.qty), flt(row.valuation_rate),
				flt(previous_sle.qty_after_transaction),
				flt(previous_sle.valuation_rate))
			
			self.insert_entries({"actual_qty": qty_diff, "incoming_rate": incoming_rate}, row)
			
		elif change_in_rate and previous_sle.qty_after_transaction >= 0:

			incoming_rate = _get_incoming_rate(flt(previous_sle.qty_after_transaction) + 1,
				flt(row.valuation_rate), flt(previous_sle.qty_after_transaction),
				flt(previous_sle.valuation_rate))
			
			# +1 entry
			self.insert_entries({"actual_qty": 1, "incoming_rate": incoming_rate}, row)
			
			# -1 entry
			self.insert_entries({"actual_qty": -1}, row)
		
	def sle_for_fifo(self, row, previous_sle):
		"""Insert Stock Ledger Entries for FIFO valuation"""
		previous_stock_queue = json.loads(previous_sle.stock_queue)
		
		if previous_stock_queue != [[row.qty, row.valuation_rate]]:
			# make entry as per attachment
			self.insert_entries({"actual_qty": row.qty, "incoming_rate": row.valuation_rate},
				row)
		
			# Make reverse entry
			qty = sum((flt(fifo_item[0]) for fifo_item in previous_stock_queue))
			self.insert_entries({"actual_qty": -1 * qty}, row)
	
					
	def insert_entries(self, opts, row):
		"""Insert Stock Ledger Entries"""
		args = {
			"item_code": row.item_code,
			"warehouse": row.warehouse,
			"posting_date": self.doc.posting_date,
			"posting_time": self.doc.posting_time,
			"voucher_type": self.doc.doctype,
			"voucher_no": self.doc.name,
			"company": webnotes.conn.get_default("company"),
			"is_cancelled": "No"
		}
		args.update(opts)
		
		return webnotes.model_wrapper([args]).insert()
		
	def delete_stock_ledger_entries(self):
		"""	Delete Stock Ledger Entries related to this Stock Reconciliation
			and repost future Stock Ledger Entries"""
			
		from stock.stock_ledger import update_entries_after
			
		existing_entries = webnotes.conn.sql("""select item_code, warehouse 
			from `tabStock Ledger Entry` where voucher_type='Stock Reconciliation'
			and voucher_no=%s""", self.doc.name, as_dict=1)
		
		# delete entries
		webnotes.conn.sql("""delete from `tabStock Ledger Entry` 
			where voucher_type='Stock Reconciliation' and voucher_no=%s""", self.doc.name)
		
		# repost future entries for selected item_code, warehouse
		for entries in existing_entries:
			update_entries_after({
				"item_code": entries.item_code,
				"warehouse": entries.warehouse,
				"posting_date": self.doc.posting_date,
				"posting_time": self.doc.posting_time
			})
	
		
@webnotes.whitelist()
def upload():
	from webnotes.utils.datautils import read_csv_content_from_uploaded_file
	return read_csv_content_from_uploaded_file()