// ERPNext - web based ERP (http://erpnext.com)
// Copyright (C) 2012 Web Notes Technologies Pvt Ltd
// 
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
// 
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	See the
// GNU General Public License for more details.
// 
// You should have received a copy of the GNU General Public License
// along with this program.	If not, see <http://www.gnu.org/licenses/>.

wn.provide("erpnext.support");
// TODO commonify this code
erpnext.support.CustomerIssue = wn.ui.form.Controller.extend({
	refresh: function() {
		if((cur_frm.doc.status=='Open' || cur_frm.doc.status == 'Work In Progress')) {
			cur_frm.add_custom_button('Make Maintenance Visit', this.make_maintenance_visit)
		}
	}, 
	
	customer: function() {
		var me = this;
		if(this.frm.doc.customer) {
			this.frm.call({
				doc: this.frm.doc,
				method: "set_customer_defaults",
				callback: function(r) {
					if(!r.exc) me.frm.refresh_fields();
				}
			});
			
			// TODO shift this to depends_on
			unhide_field(['customer_address', 'contact_person']);
		}
	}, 
	
	make_maintenance_visit: function() {
		wn.model.open_mapped_doc({
			method: "support.doctype.customer_issue.customer_issue.make_maintenance_visit",
			source_name: cur_frm.doc.name
		})
	}
});

$.extend(cur_frm.cscript, new erpnext.support.CustomerIssue({frm: cur_frm}));

cur_frm.cscript.onload = function(doc,cdt,cdn){
	if(!doc.status) 
		set_multiple(dt,dn,{status:'Open'});	
	if(doc.__islocal){		
		hide_field(['customer_address','contact_person']);
	} 
}

cur_frm.cscript.customer_address = cur_frm.cscript.contact_person = function(doc,dt,dn) {		
	if(doc.customer) 
		get_server_fields('get_customer_address', 
			JSON.stringify({customer: doc.customer, address: doc.customer_address, contact: doc.contact_person}),'', doc, dt, dn, 1);
}

cur_frm.fields_dict['customer_address'].get_query = function(doc, cdt, cdn) {
	return 'SELECT name,address_line1,city FROM tabAddress WHERE customer = "'+ doc.customer +
		'" AND docstatus != 2 AND name LIKE "%s" ORDER BY name ASC LIMIT 50';
}

cur_frm.fields_dict['contact_person'].get_query = function(doc, cdt, cdn) {
	return 'SELECT name,CONCAT(first_name," ",ifnull(last_name,"")) As FullName,department,designation \
		FROM tabContact WHERE customer = "'	+ doc.customer +
		'" AND docstatus != 2 AND name LIKE "%s" ORDER BY name ASC LIMIT 50';
}

cur_frm.fields_dict['serial_no'].get_query = function(doc, cdt, cdn) {
	var cond = '';
	if(doc.item_code) cond = ' AND `tabSerial No`.item_code = "'+ doc.item_code +'"';
	if(doc.customer) cond += ' AND `tabSerial No`.customer = "' + doc.customer + '"';
	return 'SELECT `tabSerial No`.name, `tabSerial No`.description \
		FROM `tabSerial No` \
		WHERE `tabSerial No`.docstatus != 2 AND `tabSerial No`.status = "Delivered" \
		AND `tabSerial No`.name LIKE "%s" ' + cond + ' ORDER BY `tabSerial No`.name ASC LIMIT 50';
}

cur_frm.add_fetch('serial_no', 'item_code', 'item_code');
cur_frm.add_fetch('serial_no', 'item_name', 'item_name');
cur_frm.add_fetch('serial_no', 'description', 'description');
cur_frm.add_fetch('serial_no', 'maintenance_status', 'warranty_amc_status');
cur_frm.add_fetch('serial_no', 'warranty_expiry_date', 'warranty_expiry_date');
cur_frm.add_fetch('serial_no', 'amc_expiry_date', 'amc_expiry_date');
cur_frm.add_fetch('serial_no', 'customer', 'customer');
cur_frm.add_fetch('serial_no', 'customer_name', 'customer_name');
cur_frm.add_fetch('serial_no', 'delivery_address', 'customer_address');

cur_frm.fields_dict['item_code'].get_query = function(doc, cdt, cdn) {
	if(doc.serial_no) {
		return 'SELECT `tabSerial No`.item_code, `tabSerial No`.description \
			FROM `tabSerial No` \
			WHERE `tabSerial No`.docstatus != 2 AND `tabSerial No`.name = "' + doc.serial_no +
			'" AND `tabSerial No`.item_code LIKE "%s" ORDER BY `tabSerial No`.item_code ASC LIMIT 50';
	}
	else{
		return 'SELECT `tabItem`.name, `tabItem`.item_name, `tabItem`.description \
			FROM `tabItem` \
			WHERE `tabItem`.docstatus != 2 AND `tabItem`.%(key)s LIKE "%s" ORDER BY `tabItem`.name ASC LIMIT 50';
	}
}

cur_frm.add_fetch('item_code', 'item_name', 'item_name');
cur_frm.add_fetch('item_code', 'description', 'description');

cur_frm.fields_dict['territory'].get_query = function(doc,cdt,cdn) {
	return 'SELECT `tabTerritory`.`name`,`tabTerritory`.`parent_territory` \
		FROM `tabTerritory` \
		WHERE `tabTerritory`.`is_group` = "No" AND `tabTerritory`.`docstatus`!= 2 \
		AND `tabTerritory`.%(key)s LIKE "%s"	ORDER BY	`tabTerritory`.`name` ASC LIMIT 50';
}

cur_frm.fields_dict.customer.get_query = erpnext.utils.customer_query;