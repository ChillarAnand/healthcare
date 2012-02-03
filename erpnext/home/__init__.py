import webnotes
from webnotes import msgprint

feed_dict = {
	# Project
	'Project':		       ['[%(status)s]', '#000080'],

	# Sales
	'Lead':			 ['%(lead_name)s', '#000080'],
	'Quotation':	    ['[%(status)s] To %(customer_name)s worth %(currency)s %(grand_total_export)s', '#4169E1'],
	'Sales Order':	  ['[%(status)s] To %(customer_name)s worth %(currency)s %(grand_total_export)s', '#4169E1'],

	# Purchase
	'Supplier':		     ['%(supplier_name)s, %(supplier_type)s', '#6495ED'],
	'Purchase Order':       ['[%(status)s] %(name)s To %(supplier_name)s for %(currency)s  %(grand_total_import)s', '#4169E1'],

	# Stock
	'Delivery Note':	['[%(status)s] To %(customer_name)s', '#4169E1'],
	'Purchase Receipt': ['[%(status)s] From %(supplier)s', '#4169E1'],

	# Accounts
	'Journal Voucher':      ['[%(voucher_type)s] %(name)s', '#4169E1'],
	'Payable Voucher':      ['To %(supplier_name)s for %(currency)s %(grand_total_import)s', '#4169E1'],
	'Receivable Voucher':['To %(customer_name)s for %(currency)s %(grand_total_export)s', '#4169E1'],

	# HR
	'Expense Voucher':      ['[%(approval_status)s] %(name)s by %(employee_name)s', '#4169E1'],
	'Salary Slip':	  ['%(employee_name)s for %(month)s %(fiscal_year)s', '#4169E1'],
	'Leave Transaction':['%(leave_type)s for %(employee)s', '#4169E1'],

	# Support
	'Customer Issue':       ['[%(status)s] %(description)s by %(customer_name)s', '#000080'],
	'Maintenance Visit':['To %(customer_name)s', '#4169E1'],
	'Support Ticket':       ['[%(status)s] %(subject)s', '#000080']	
}

def make_feed(feedtype, doctype, name, owner, subject, color):
	"makes a new Feed record"
	#msgprint(subject)
	from webnotes.model.doc import Document

	if feedtype in ('Login', 'Comment'):
		# delete old login, comment feed
		webnotes.conn.sql("""delete from tabFeed where 
			datediff(curdate(), creation) > 7 and doc_type in ('Comment', 'Login')""")
	else:
		# one feed per item
		webnotes.conn.sql("""delete from tabFeed
			where doc_type=%s and doc_name=%s 
			and ifnull(feed_type,'') != 'Comment'""", (doctype, name))

	f = Document('Feed')
	f.owner = owner
	f.feed_type = feedtype
	f.doc_type = doctype
	f.doc_name = name
	f.subject = subject
	f.color = color
	f.save()

def update_feed(doc, method=None):   
	"adds a new feed"
	if method=='on_update':
		subject, color = feed_dict.get(doc.doctype, [None, None])
		if subject:			
			make_feed('', doc.doctype, doc.name, doc.owner, subject % doc.fields, color)
