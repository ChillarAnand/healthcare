erpnext.updates = [
	["13th November 2012", [
		"Trial Balance (new): Feature to export Ledgers or Groups selectively. Indent Groups with spaces",
		"General Ledger (new): Will show entries with 'Is Opening' as Opening.",
		"General Ledger (new): Show against account entries if filtered by account.",
	]],
	["12th November 2012", [
		"Document Lists: Automatically Refresh lists when opened (again).",	
		"Messages: Popups will not be shown (annoying).",	
		"Email Digest: New option to get ten latest Open Support Tickets.",
		"Journal Voucher: 'Against JV' will now be filtered by the Account selected.",
		"Query Report: Allow user to rename and save reports.",
		"Employee Leave Balance Report: Bugfix"
	]]
]


wn.pages['latest-updates'].onload = function(wrapper) { 
	wn.ui.make_app_page({
		parent: wrapper,
		title: 'Latest Updates',
		single_column: true
	});
		
	var parent = $(wrapper).find(".layout-main");
	
	$("<p class='help'>Report issues by sending a mail to <a href='mailto:support@erpnext.com'>support@erpnext.com</a> or \
		via <a href='https://github.com/webnotes/erpnext/issues'>GitHub Issues</a></p><hr>").appendTo(parent);
	
	
	$.each(erpnext.updates, function(i, day) {
		$("<h4>" + day[0] + "</h4>").appendTo(parent);
		$.each(day[1], function(j, item) {
			$("<p>").html(item).appendTo(parent);
		})
		$("<hr>").appendTo(parent);
	});
}