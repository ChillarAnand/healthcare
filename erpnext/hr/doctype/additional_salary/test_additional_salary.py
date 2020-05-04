# -*- coding: utf-8 -*-
# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt
from __future__ import unicode_literals
import unittest
import frappe, erpnext
from frappe.utils import nowdate, add_days
from erpnext.hr.doctype.employee.test_employee import make_employee
from erpnext.hr.doctype.salary_component.test_salary_component import create_salary_component
from erpnext.hr.doctype.salary_slip.test_salary_slip import make_employee_salary_slip


class TestAdditionalSalary(unittest.TestCase):

	def setUp(self):
		from erpnext.hr.doctype.salary_slip.test_salary_slip import TestSalarySlip
		TestSalarySlip().setUp()

	def test_recurring_additional_salary(self):
		emp_id = make_employee("test_additional@salary.com")
		frappe.db.set_value("Employee", emp_id, "relieving_date", add_days(nowdate(), 1800))
		add_sal = get_additional_salary(emp_id)

		ss = make_employee_salary_slip("test_additional@salary.com", "Monthly")
		for earning in ss.earnings:
			if earning.salary_component == "Recurring Salary Component":
				amount = earning.amount
				salary_component = earning.salary_component

		self.assertEqual(amount, add_sal.amount)
		self.assertEqual(salary_component, add_sal.salary_component)



def get_additional_salary(emp_id):
	create_salary_component("Recurring Salary Component")
	add_sal = frappe.new_doc("Additional Salary")
	add_sal.employee = emp_id
	add_sal.salary_component = "Recurring Salary Component"
	add_sal.is_recurring = 1
	add_sal.from_date = add_days(nowdate(), -50)
	add_sal.to_date = add_days(nowdate(), 180)
	add_sal.amount = 5000
	add_sal.save()
	add_sal.submit()

	return add_sal