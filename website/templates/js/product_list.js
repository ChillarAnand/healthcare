// Copyright (c) 2013, Web Notes Technologies Pvt. Ltd.
// License: GNU General Public License v3. See license.txt

window.get_product_list = function() {
	$(".more-btn .btn").click(function() {
		window.get_product_list()
	});
	
	if(window.start==undefined) {
		throw "product list not initialized (no start)"
	}
	
	$.ajax({
		method: "GET",
		url: "server.py",
		dataType: "json",
		data: {
			cmd: "selling.utils.product.get_product_list",
			start: window.start,
			search: window.search,
			product_group: window.product_group
		},
		dataType: "json",
		success: function(data) {
			window.render_product_list(data.message);
		}
	})
}

window.render_product_list = function(data) {
	if(data.length) {
		var table = $("#search-list .table");
		if(!table.length)
			var table = $("<table class='table'>").appendTo("#search-list");
			
		$.each(data, function(i, d) {
			$(d).appendTo(table);
		});
	}
	if(data.length < 10) {
		if(!table) {
			$(".more-btn")
				.replaceWith("<div class='alert alert-warning'>No products found.</div>");
		} else {
			$(".more-btn")
				.replaceWith("<div class='text-muted'>Nothing more to show.</div>");
		}
	} else {
		$(".more-btn").toggle(true)
	}
	window.start += (data.length || 0);
}
