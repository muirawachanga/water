from __future__ import unicode_literals

import frappe
from frappe.utils import flt, fmt_money, today


def sales_invoice_arrears(doc, event):
    # Don't do this for returns
    if doc.is_return == 1:
        return
    # Do this only for rental related invoices.
    if doc.water_owner_contract in (None, ''):
        return
    arrears = frappe.db.sql("select sum(outstanding_amount) from `tabSales Invoice` where customer = %s "
                            "and docstatus = 1 and due_date < %s and water_owner_contract = %s and is_return != 1 "
                            "and outstanding_amount > 0",
                            (doc.customer, today(), doc.tenancy_contract))[0][0]
    if arrears is None or arrears <= 0:
        doc.arrears_note = ""
        return
    doc.arrears_note = "You have {0} in pending arrears, your total amount to pay is: {1}" \
        .format(fmt_money(arrears, 2, doc.currency), fmt_money(flt(doc.outstanding_amount + arrears),
                                                               2, doc.currency))


def reset_utility_item_measurement_billing(doc, event):
    ut_measurement = frappe.get_list('Water Utility  Measurement', fields=['*'], filters=[
        ['billing_invoice', '=', doc.name]
    ])

    if not ut_measurement:
        return
    for m in ut_measurement:
        utm = frappe.get_doc('Water Utility  Measurement', m.name)
        utm.cancel_billing()
        utm.save()


def reset_tc_is_billed_items(doc, event):
    if doc.tenancy_contract in (None, ''):
        return
    tc = frappe.get_doc('Water Owner Contract', doc.water_owner_contract)
    i_items = doc.get("items")
    tc_items = tc.get("items")

    for it in i_items:
        tc_it = [i for i in tc_items if i.item_code == it.item_code]
        if len(tc_it) < 1:
            continue
        if not tc_it[0].recurring:
            tc_it[0].set('is_billed', False)
            tc_it[0].db_update()


def sales_invoice_cancel(doc, event):
    reset_tc_is_billed_items(doc, event)
    reset_utility_item_measurement_billing(doc, event)
