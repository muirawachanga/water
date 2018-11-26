# -*- coding: utf-8 -*-
# Copyright (c) 2018, Stephen and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc, _
from frappe.utils import getdate, date_diff, flt, add_days, today
from water_management.water_management import utils
from datetime import timedelta
from frappe.exceptions import ValidationError
from frappe.desk.reportview import get_match_cond


class WaterOwnerContract(Document):
    pass

    def validate(self):
        self.validate_items()
        self.validate_dates()

    def validate_items(self):
        self.old_items_names = []
        if self.contract_status != 'New':
            self.old_items_names = [i.name for i in self.get("items")]
        items = self.get("items")
        if self.get("contract_status") == 'Active':
            if not len(items):
                frappe.async.publish_realtime(doctype=self.doctype, docname=self.name)
                frappe.throw(
                    _("Cannot approve a tenancy contract with no billing items"))

        # Validate items by simple count first. If items were removed.
        for i in items:
            if i.is_utility_item:
                if not i.utility_item:
                    frappe.throw(
                        _("Item {} is marked as Utility Item but no Utility Item is selected.").format(i.item_name))
            if self.get('start_date') and i.start_date < self.get('start_date'):
                frappe.throw(
                    _("Item {} billing start date is less than the contract's billing start date."
                      "Billing start date for items should be greater or equal to the contract billing start date")
                        .format(i.item_name))

    def validate_dates(self):
        if self.contract_status == 'Active':
            if not self.start_date:
                frappe.throw(
                    _("You must set the contract start date before approving"))
            if not self.end_date:
                frappe.throw(
                    _("You must set the contract end date before approving"))

        if self.contract_status == 'Terminated':
            if not self.termination_date:
                frappe.throw(
                    _("You must set the contract termination date before terminating"))

        if self.contract_status == 'Cancelled':
            if not self.cancellation_date:
                frappe.throw(
                    _("You must set the contract cancellation date before cancelling"))


@frappe.whitelist()
def get_item_details(item_code, start_date=None):
    item = frappe.db.sql("""select item_name, stock_uom, image, description, item_group, brand, income_account, selling_cost_center
		from `tabItem` where name = %s""", item_code, as_dict=1)
    return {
        'item_name': item and item[0]['item_name'] or '',
        'stock_uom': item and item[0]['stock_uom'] or '',
        'description': item and item[0]['description'] or '',
        'image': item and item[0]['image'] or '',
        'item_group': item and item[0]['item_group'] or '',
        'brand': item and item[0]['brand'] or '',
        'income_account': item and item[0]['income_account'] or '',
        'cost_center': item and item[0]['selling_cost_center'] or '',
        'start_date': start_date or today()
    }
@frappe.whitelist()
def water_owner_query(doctype, txt, searchfield, start, page_len, filters):
    # Select only property units that don't have Tenancy Contracts that are in specific statuses.
    # Specify these filters in filters["tc_filters"]. e.g:
    # Specify the 'side' (IN or NOT IN) using filters["side"]
    '''
        frm.set_query('property_unit', function(){
                return {
                    query: "property.property_management.doctype.property_unit.property_unit.property_unit_query",
                    filters: {
                        tc_filters: ['Active', 'New'],
                        side: "not in",
                        property: "PRO-00001"
                    }
                }
            })
    '''
    property_filter = ""
    if filters.get("property"):
        property_filter = "and property = %s"
    prop = [] if not filters.get("property") else [filters.get("property")]

    return frappe.db.sql("select name, customer from `tabWater Owner Contract` where contract_status in "
                         "({statuses}) and ({key} like %s or customer like %s) {prop} {mcond} "
                         "order by if(locate(%s, name), locate(%s, name), 99999), "
                         "if(locate(%s, customer), locate(%s, customer), 99999), "
                         "idx desc, name, customer limit %s, %s".format(**{
        'key': searchfield,
        'mcond': get_match_cond(doctype),
        'prop': property_filter,
        'statuses': ','.join(['%s'] * len(filters["tc_filters"]))
    }), filters["tc_filters"] + ["%%%s%%" % txt, "%%%s%%" % txt] + prop + [txt.replace("%", ""),
                                                                           txt.replace("%", ""),
                                                                           txt.replace("%", ""),
                                                                           txt.replace("%", ""),
                                                                           start, page_len])


def get_last_tc_invoice(name):
    """
    Load the last invoice of a particular tenancy contract
    """
    doc = frappe.get_all("Sales Invoice", ["name"], [["docstatus", "!=", 2], ["is_return", "!=", 1],
                                                     ["water_owner_contract", "=", name]],
                         order_by="creation desc", limit_page_length=1)
    if doc:
        return frappe.get_doc("Sales Invoice", doc[0].name)
    else:
        return None


def set_missing_values(source, target):
    target.set('due_date', add_days(target.get('posting_date'), source.due_date_days or 0))
    target.is_pos = 0
    target.ignore_pricing_rule = 1
    target.flags.ignore_permissions = True
    target.run_method("set_missing_values")
    target.run_method("calculate_taxes_and_totals")


def set_period(source, target):
    """
    Set invoice billing period
    :param source: Tenancy Contract doc
    :param target: Sales Invoice doc to set billing period
    :return: None
    """
    last_inv = get_last_tc_invoice(source.name)
    if last_inv:
        pn = utils.get_next_period(last_inv.get("billing_period"))
        if not pn:
            frappe.throw(_("Could not determine period for this invoice. Looking for the next period from {}")
                         .format(last_inv.get("billing_period")))
        target.set("billing_period", pn)
        period = frappe.get_doc("Billing Periods", target.get("billing_period"))
        target.set("posting_date", period.get("start_date"))
        return

    # This is the first invoice. Try to determine the period to use
    pn = utils.get_billing_period_for_date(getdate(source.get("date_of_first_billing")), source.get('billing_period'))
    if not pn:
        frappe.throw(_("Could not determine period for this invoice. Looking for a period covering "
                       "the billing date: {}").format(source.get("date_of_first_billing")))
    target.set("billing_period", pn)
    target.set("posting_date", source.get("date_of_first_billing"))


def remove_items(target, items):
    curr_items = target.get("items")
    item_codes_to_remove = [i.item_code for i in items]
    items_to_remove = [item for item in curr_items if item.item_code in item_codes_to_remove]
    for i in items_to_remove:
        curr_items.remove(i)


def validate_items(source, target):
    tc_items = source.get('items')
    inv_items_to_remove = []
    # Remove items that should not be included in this invoice based on their characteristics in TC items

    for tc_i in tc_items:
        # Remove non recurring items that have already been billed
        if not tc_i.get('recurring') and tc_i.get('is_billed'):
            inv_items_to_remove.append(tc_i)
        # Remove items whose start of billing is not yet due
        if getdate(tc_i.get('start_date')) > target.get('posting_date'):
            if tc_i not in inv_items_to_remove:
                inv_items_to_remove.append(tc_i)
    if inv_items_to_remove:
        remove_items(target, inv_items_to_remove)



def prorate(item, tc_item, period):
    """
    Prorates an item cost based on the period and the start_date of billing for that item.
    :param item: Invoice item to prorate
    :param tc_item: TC Item with the required attributes
    :param period: The period being billed
    :return: The same item with the adjusted rate
    """
    days_in_period = date_diff(period.end_date, period.start_date) + 1
    daily_rate = flt(flt(item.rate) / flt(days_in_period))
    days_to_bill = date_diff(period.end_date, tc_item.start_date) + 1
    item.rate = flt(flt(daily_rate) * flt(days_to_bill))
    item.description = "{} - Prorated {} Days".format(item.description, days_to_bill)
    return item


def prorate_items(source, target):
    period = frappe.get_doc("Billing Periods", target.get("billing_period"))

    inv_items = target.get("items")
    tc_items = source.get("items")

    for it in inv_items:
        tc_it = [i for i in tc_items if i.item_code == it.item_code][0]
        if not tc_it.is_utility_item and getdate(tc_it.start_date) > getdate(period.start_date):
            prorate(it, tc_it, period)


def bill_utility_item(ui_measurement_doc, item, source, target):
    utility_item = ui_measurement_doc.get_utility_item()
    frappe.msgprint(_(utility_item))
    usage = 1.0  # Default for monetary items
    if utility_item.measurement_type == 'Meter Reading':
        prev_measurement = ui_measurement_doc.get_previous_measurement()
        usage = ui_measurement_doc.meter_reading - prev_measurement.meter_reading
    if utility_item.measurement_type == 'Usage Units':
        usage = ui_measurement_doc.usage_units

    inv_item = [i for i in target.get('items') if i.item_code == item.item_code][0]
    inv_item.set('qty', int(usage))
    if utility_item.measurement_type == 'Monetary Amount':
        inv_item.set('rate', ui_measurement_doc.monetary_amount)
    ui_measurement_doc.set('usage_units', inv_item.get('qty'))

    # Improve the item description
    if utility_item.measurement_type != 'Monetary Amount':
        desc = inv_item.get('description') + ' - ' + 'Based on: ' + utility_item.measurement_type \
               + ': ' + str(usage)
        inv_item.set('description', desc)

    # Check for minimum charges..
    if utility_item.measurement_type != 'Monetary Amount' and utility_item.minimum_charge > 0:
        if ui_measurement_doc.usage_units < utility_item.minimum_charge_units:
            inv_item.set('rate', utility_item.minimum_charge)
            inv_item.set('qty', 1)
            desc = inv_item.get('description') + " (Minimum Charges Applied)"
            inv_item.set('description', desc)


def process_utility_items(source, target):
    u_items = [i for i in source.get('items') if i.is_utility_item]

    """We hold all the uim items that we bill here. We update them later after saving this invoice."""
    target.utility_items_measurements = []
    for item in u_items:
        """If we are not to invoice this utility item (it is not in the inv items), we skip it..."""
        utility_inv_item = [i for i in target.get('items') if i.item_code == item.item_code]
        if not utility_inv_item:
            continue
        utility_item = frappe.get_doc('Utility Items', item.utility_item)
        frappe.msgprint(_(utility_item.name))
        ui_measurement = frappe.get_list('Water Utility  Measurement', fields=['*'], filters=[
            ['owner_contract', '=', source.name], ['water_as_utility', '=', utility_item.name],
            ['measurement_status', '=', 'New'], ['is_opening_entry', '=', 0]
        ])
        if not ui_measurement:
            msg = _("This Water Owner Contract's item '{}' contains a Utility Items '{}' that should be billed with "
                    "this invoice but no measurement / reading exists for it in the invoice period. "
                    "Please enter the Measurement Reading for the current period. "
                    "Cannot generate invoice.").format(item.item_name, item.utility_item)
            frappe.throw(msg, utils.MissingUtilityItemException(msg))
        if len(ui_measurement) > 1:
            msg = _("Invalid Utility Item Measurements for item '{}', Utility Items '{}'. Found more than "
                    "one measurement pending billing. "
                    "Cannot generate invoice.").format(item.item_name, item.utility_item)
            frappe.throw(msg, ValidationError(msg))

        ui_measurement_doc = frappe.get_doc('Water Utility  Measurement', ui_measurement[0].name)
        bill_utility_item(ui_measurement_doc, item, source, target)
        target.utility_items_measurements.append(ui_measurement_doc)


def validate_dates_before_invoice_gen(tc_doc):
    delta = timedelta(days=tc_doc.grace_period)
    # Account for Grace Period to allow invoice generation if today is >= date_of_first_billing - grace_period (days)
    if getdate() < getdate(tc_doc.date_of_first_billing) + delta:
        frappe.throw(_('Cannot create invoice for this contract. Date of First Billing plus Billing Grace Period'
                       ' is greater than today.'))


def set_billed_non_recurrent_items(tc, inv):
    i_items = inv.get("items")
    tc_items = tc.get("items")

    for it in i_items:
        tc_it = [i for i in tc_items if i.item_code == it.item_code][0]
        if not tc_it.recurring:
            tc_it.set('is_billed', True)
            tc_it.db_update()


@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None, ignore_permissions=False):
    tc_doc = frappe.get_doc("Water Owner Contract", source_name)
    verify_items(tc_doc)
    validate_dates_before_invoice_gen(tc_doc)

    def postprocess(source, target):
        set_period(source, target)
        validate_items(source, target)
        process_utility_items(source, target)
        prorate_items(source, target)
        #Update non recurrent tenancy contract items to billed.
        set_billed_non_recurrent_items(source, target)
        set_missing_values(source, target)
        # Get the advance paid Journal Entries in Sales Invoice Advance
        target.run_method('set_advances')

    invoice = get_mapped_doc("Water Owner Contract", source_name, {
        "Water Owner Contract": {
            "doctype": "Sales Invoice",
            "field_map": {
                "party_account_currency": "party_account_currency",
                # "property_unit_name": "property_unit"
            },
            "validation": {
                "contract_status": ["=", "Active"]
            }
        },
        "Water Bills Items": {
            "doctype": "Sales Invoice Item",
        },
        "Sales Taxes and Charges": {
            "doctype": "Sales Taxes and Charges",
            "add_if_empty": True
        }
    }, target_doc, postprocess, ignore_permissions=ignore_permissions)
    invoice.save()
    # Link the Utility Item Measurements billed in this invoice.
    for uim in invoice.utility_items_measurements:
        uim.set_billed(invoice)
        uim.save()
    invoice.submit()
    return invoice


def verify_items(tc_doc):
    if not len(tc_doc.items):
        frappe.throw(_('No Contract Items to invoice for this contract.'))
