# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
# License: GNU General Public License v3. See license.txt

# ERPNext - web based ERP (http://erpnext.com)
# For license information, please see license.txt

from __future__ import unicode_literals
import webnotes, unittest
from webnotes.utils import flt
import json
from accounts.utils import get_fiscal_year, get_stock_and_account_difference, get_balance_on


class TestStockReconciliation(unittest.TestCase):
	def test_reco_for_fifo(self):
		webnotes.defaults.set_global_default("perpetual_accounting", 0)
		# [[qty, valuation_rate, posting_date, 
		#		posting_time, expected_stock_value, bin_qty, bin_valuation]]
		input_data = [
			[50, 1000, "2012-12-26", "12:00", 50000, 45, 48000], 
			[5, 1000, "2012-12-26", "12:00", 5000, 0, 0], 
			[15, 1000, "2012-12-26", "12:00", 15000, 10, 12000], 
			[25, 900, "2012-12-26", "12:00", 22500, 20, 22500], 
			[20, 500, "2012-12-26", "12:00", 10000, 15, 18000], 
			[50, 1000, "2013-01-01", "12:00", 50000, 65, 68000], 
			[5, 1000, "2013-01-01", "12:00", 5000, 20, 23000],
			["", 1000, "2012-12-26", "12:05", 15000, 10, 12000],
			[20, "", "2012-12-26", "12:05", 16000, 15, 18000],
			[10, 2000, "2012-12-26", "12:10", 20000, 5, 6000],
			[1, 1000, "2012-12-01", "00:00", 1000, 11, 13200],
			[0, "", "2012-12-26", "12:10", 0, -5, 0]
		]
			
		for d in input_data:
			self.cleanup_data()
			self.insert_existing_sle("FIFO")
			stock_reco = self.submit_stock_reconciliation(d[0], d[1], d[2], d[3])
		
			# check stock value
			res = webnotes.conn.sql("""select stock_value from `tabStock Ledger Entry`
				where item_code = '_Test Item' and warehouse = '_Test Warehouse - _TC'
				and posting_date = %s and posting_time = %s order by name desc limit 1""", 
				(d[2], d[3]))
			self.assertEqual(res and flt(res[0][0]) or 0, d[4])
			
			# check bin qty and stock value
			bin = webnotes.conn.sql("""select actual_qty, stock_value from `tabBin`
				where item_code = '_Test Item' and warehouse = '_Test Warehouse - _TC'""")
			
			self.assertEqual(bin and [flt(bin[0][0]), flt(bin[0][1])] or [], [d[5], d[6]])
			
			# no gl entries
			gl_entries = webnotes.conn.sql("""select name from `tabGL Entry` 
				where voucher_type = 'Stock Reconciliation' and voucher_no = %s""",
				 stock_reco.doc.name)
			self.assertFalse(gl_entries)
			
		
	def test_reco_for_moving_average(self):
		webnotes.defaults.set_global_default("perpetual_accounting", 0)
		# [[qty, valuation_rate, posting_date, 
		#		posting_time, expected_stock_value, bin_qty, bin_valuation]]
		input_data = [
			[50, 1000, "2012-12-26", "12:00", 50000, 45, 48000], 
			[5, 1000, "2012-12-26", "12:00", 5000, 0, 0], 
			[15, 1000, "2012-12-26", "12:00", 15000, 10, 12000], 
			[25, 900, "2012-12-26", "12:00", 22500, 20, 22500], 
			[20, 500, "2012-12-26", "12:00", 10000, 15, 18000], 
			[50, 1000, "2013-01-01", "12:00", 50000, 65, 68000], 
			[5, 1000, "2013-01-01", "12:00", 5000, 20, 23000],
			["", 1000, "2012-12-26", "12:05", 15000, 10, 12000],
			[20, "", "2012-12-26", "12:05", 18000, 15, 18000],
			[10, 2000, "2012-12-26", "12:10", 20000, 5, 6000],
			[1, 1000, "2012-12-01", "00:00", 1000, 11, 13200],
			[0, "", "2012-12-26", "12:10", 0, -5, 0]
			
		]
		
		for d in input_data:
			self.cleanup_data()
			self.insert_existing_sle("Moving Average")
			stock_reco = self.submit_stock_reconciliation(d[0], d[1], d[2], d[3])
			
			# check stock value in sle
			res = webnotes.conn.sql("""select stock_value from `tabStock Ledger Entry`
				where item_code = '_Test Item' and warehouse = '_Test Warehouse - _TC'
				and posting_date = %s and posting_time = %s order by name desc limit 1""", 
				(d[2], d[3]))
				
			self.assertEqual(res and flt(res[0][0], 4) or 0, d[4])
			
			# bin qty and stock value
			bin = webnotes.conn.sql("""select actual_qty, stock_value from `tabBin`
				where item_code = '_Test Item' and warehouse = '_Test Warehouse - _TC'""")
			
			self.assertEqual(bin and [flt(bin[0][0]), flt(bin[0][1], 4)] or [], 
				[flt(d[5]), flt(d[6])])
				
			# no gl entries
			gl_entries = webnotes.conn.sql("""select name from `tabGL Entry` 
				where voucher_type = 'Stock Reconciliation' and voucher_no = %s""", 
				stock_reco.doc.name)
			self.assertFalse(gl_entries)
			
	def test_reco_fifo_gl_entries(self):
		webnotes.defaults.set_global_default("perpetual_accounting", 1)
		
		# [[qty, valuation_rate, posting_date, posting_time, stock_in_hand_debit]]
		input_data = [
			[50, 1000, "2012-12-26", "12:00"], 
			[5, 1000, "2012-12-26", "12:00"], 
			[15, 1000, "2012-12-26", "12:00"], 
			[25, 900, "2012-12-26", "12:00"], 
			[20, 500, "2012-12-26", "12:00"], 
			["", 1000, "2012-12-26", "12:05"],
			[20, "", "2012-12-26", "12:05"],
			[10, 2000, "2012-12-26", "12:10"],
			[0, "", "2012-12-26", "12:10"],
			[50, 1000, "2013-01-01", "12:00"], 
			[5, 1000, "2013-01-01", "12:00"],
			[1, 1000, "2012-12-01", "00:00"],
			
		]
			
		for d in input_data:
			# print d[0], d[1], d[2], d[3]
			self.cleanup_data()
			self.insert_existing_sle("FIFO")
			stock_reco = self.submit_stock_reconciliation(d[0], d[1], d[2], d[3])
			
			self.assertFalse(get_stock_and_account_difference(["_Test Warehouse - _TC"]))
			# cancel
			stock_reco.cancel()
			self.assertFalse(get_stock_and_account_difference(["_Test Warehouse - _TC"]))
		
		webnotes.defaults.set_global_default("perpetual_accounting", 0)		
			
	def test_reco_moving_average_gl_entries(self):
		webnotes.defaults.set_global_default("perpetual_accounting", 1)
		
		# [[qty, valuation_rate, posting_date, 
		#		posting_time, stock_in_hand_debit]]
		input_data = [
			[50, 1000, "2012-12-26", "12:00", 36500], 
			[5, 1000, "2012-12-26", "12:00", -8500], 
			[15, 1000, "2012-12-26", "12:00", 1500], 
			[25, 900, "2012-12-26", "12:00", 9000], 
			[20, 500, "2012-12-26", "12:00", -3500], 
			["", 1000, "2012-12-26", "12:05", 1500],
			[20, "", "2012-12-26", "12:05", 4500],
			[10, 2000, "2012-12-26", "12:10", 6500],
			[0, "", "2012-12-26", "12:10", -13500],
			[50, 1000, "2013-01-01", "12:00", 50000], 
			[5, 1000, "2013-01-01", "12:00", 5000],
			[1, 1000, "2012-12-01", "00:00", 1000],
			
		]
			
		for d in input_data:
			self.cleanup_data()
			self.insert_existing_sle("Moving Average")
			stock_reco = self.submit_stock_reconciliation(d[0], d[1], d[2], d[3])
			self.assertFalse(get_stock_and_account_difference(["_Test Warehouse - _TC"]))
			
			# cancel
			stock_reco.cancel()
			self.assertFalse(get_stock_and_account_difference(["_Test Warehouse - _TC"]))
		
		webnotes.defaults.set_global_default("perpetual_accounting", 0)


	def cleanup_data(self):
		webnotes.conn.sql("delete from `tabStock Ledger Entry`")
		webnotes.conn.sql("delete from tabBin")
		webnotes.conn.sql("delete from `tabGL Entry`")
						
	def submit_stock_reconciliation(self, qty, rate, posting_date, posting_time):
		stock_reco = webnotes.bean([{
			"doctype": "Stock Reconciliation",
			"posting_date": posting_date,
			"posting_time": posting_time,
			"fiscal_year": get_fiscal_year(posting_date)[0],
			"company": "_Test Company",
			"expense_account": "Stock Adjustment - _TC",
			"cost_center": "_Test Cost Center - _TC",
			"reconciliation_json": json.dumps([
				["Item Code", "Warehouse", "Quantity", "Valuation Rate"],
				["_Test Item", "_Test Warehouse - _TC", qty, rate]
			]),
		}])
		stock_reco.insert()
		stock_reco.submit()
		return stock_reco
		
	def insert_existing_sle(self, valuation_method):
		webnotes.conn.set_value("Item", "_Test Item", "valuation_method", valuation_method)
		webnotes.conn.set_default("allow_negative_stock", 1)
		
		existing_ledgers = [
			{
				"doctype": "Stock Ledger Entry", "__islocal": 1,
				"voucher_type": "Stock Entry", "voucher_no": "TEST",
				"item_code": "_Test Item", "warehouse": "_Test Warehouse - _TC",
				"posting_date": "2012-12-12", "posting_time": "01:00",
				"actual_qty": 20, "incoming_rate": 1000, "company": "_Test Company",
				"fiscal_year": "_Test Fiscal Year 2012",
			},
			{
				"doctype": "Stock Ledger Entry", "__islocal": 1,
				"voucher_type": "Stock Entry", "voucher_no": "TEST",
				"item_code": "_Test Item", "warehouse": "_Test Warehouse - _TC",
				"posting_date": "2012-12-15", "posting_time": "02:00",
				"actual_qty": 10, "incoming_rate": 700, "company": "_Test Company",
				"fiscal_year": "_Test Fiscal Year 2012",
			},
			{
				"doctype": "Stock Ledger Entry", "__islocal": 1,
				"voucher_type": "Stock Entry", "voucher_no": "TEST",
				"item_code": "_Test Item", "warehouse": "_Test Warehouse - _TC",
				"posting_date": "2012-12-25", "posting_time": "03:00",
				"actual_qty": -15, "company": "_Test Company",
				"fiscal_year": "_Test Fiscal Year 2012",
			},
			{
				"doctype": "Stock Ledger Entry", "__islocal": 1,
				"voucher_type": "Stock Entry", "voucher_no": "TEST",
				"item_code": "_Test Item", "warehouse": "_Test Warehouse - _TC",
				"posting_date": "2012-12-31", "posting_time": "08:00",
				"actual_qty": -20, "company": "_Test Company",
				"fiscal_year": "_Test Fiscal Year 2012",
			},
			{
				"doctype": "Stock Ledger Entry", "__islocal": 1,
				"voucher_type": "Stock Entry", "voucher_no": "TEST",
				"item_code": "_Test Item", "warehouse": "_Test Warehouse - _TC",
				"posting_date": "2013-01-05", "posting_time": "07:00",
				"actual_qty": 15, "incoming_rate": 1200, "company": "_Test Company",
				"fiscal_year": "_Test Fiscal Year 2013",
			},
		]
		
		webnotes.get_obj("Stock Ledger").update_stock(existing_ledgers)

		
test_dependencies = ["Item", "Warehouse"]