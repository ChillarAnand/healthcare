import webnotes
from collections import Counter
def execute():
	for name in webnotes.conn.sql("""select name from `tabHoliday List`"""):
		holiday_list_wrapper = webnotes.model_wrapper("Holiday List", name[0])
		
		desc_count = Counter([d.description for d in 
			holiday_list_wrapper.doclist.get({"doctype": "Holiday"})])
			
		holiday_list_obj = webnotes.get_obj(doc=holiday_list_wrapper.doc,
			doclist=holiday_list_wrapper.doclist)
			
		save = False
		
		for desc in desc_count.keys():
			if desc in ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday",
					"Friday", "Saturday"] and desc_count[desc] > 50:
				holiday_list_obj.doclist = holiday_list_obj.doclist.get(
					{"description": ["!=", desc]})
				
				webnotes.conn.sql("""delete from `tabHoliday`
					where parent=%s and parenttype='Holiday List' 
					and `description`=%s""", (holiday_list_obj.doc.name, desc))
				holiday_list_obj.doc.weekly_off = desc
				holiday_list_obj.get_weekly_off_dates()
				save = True
		
		if save:
			holiday_list_wrapper.set_doclist(holiday_list_obj.doclist)
			holiday_list_wrapper.save()
				
			
		
		
		
		
		
		