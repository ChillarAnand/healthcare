def execute():
	import webnotes
	from webnotes import get_obj
	pi_list = webnotes.conn.sql("""select name from `tabPurchase Invoice` 
		where docstatus = 1 and ifnull(against_expense_account, '') = ''""")
		
	for pi in pi_list:
	    pi_obj = get_obj("Purchase Invoice", pi[0], with_children=1)
	    pi_obj.set_against_expense_account()
	    webnotes.conn.set_value("Purchase Invoice", pi[0], 
			"against_expense_account", pi_obj.doc.against_expense_account)