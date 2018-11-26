# -*- coding: utf-8 -*-
# Copyright (c) 2018, Stephen and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class WaterUtilityMeasurement(Document):

    def set_billed(self, invoice):
        """ Sets the invoice that billed this item and updates to billed """
        self.set('billing_invoice', invoice.get('name'))
        self.set('billing_date', invoice.posting_date)
        self.set('billing_period', invoice.billing_period)
        self.set('measurement_status', 'Billed')
        # If it's the first billing (Previous is opening Entry) we set the opening_entry as billed.
        prev = self.get_previous_measurement()
        if prev and prev.is_opening_entry:
            prev.set_billed(invoice)

    def cancel_billing(self):
        """ Cancels the billing and resets the measurement """
        self.set('billing_invoice', '')
        self.set('billing_date', '')
        self.set('billing_period', '')
        self.set('measurement_status', 'New')
        if self.get_utility_item().measurement_type != 'Usage Units':
            self.set('usage_units', 0)

    def validate(self):
        self.check_opening_item()
        self.check_if_older_exists()
        self.validate_dates()
        self.validate_reading()

    def get_utility_item(self):
        return frappe.get_doc('Utility Items', self.get('water_as_utility'))

    def get_previous_measurement(self):
        prev = frappe.db.sql("SELECT name FROM `tabWater Utility  Measurement` WHERE "
                             "measurement_status != 'Cancelled' AND owner_contract = %(tc)s "
                             "AND water_as_utility = %(ui)s "
                             "AND NAME != %(me)s AND reading_date < %(rd)s "
                             "ORDER BY reading_date DESC LIMIT 0, 1", {'tc': self.owner_contract,
                                                                       'ui': self.water_as_utility,
                                                                       'me': self.name,
                                                                       'rd': self.reading_date
                                                                       })
        if not prev:
            return None

        return frappe.get_doc('Water Utility  Measurement', prev[0][0])

    def validate_reading(self):
        utility_item = self.get_utility_item()
        if utility_item.measurement_type == 'Meter Reading' and not self.is_opening_entry:
            prev = self.get_previous_measurement()

            if flt(self.meter_reading) < flt(prev.meter_reading):
                frappe.throw(
                    _(
                        "Current reading cannot be less than previous reading"))

    def validate_dates(self):
        if self.measurement_status == 'New' and not self.is_opening_entry:
            count = frappe.db.sql("SELECT count(*) FROM `tabWater Utility  Measurement` WHERE "
                                  "measurement_status != 'Cancelled' AND owner_contract = %(tc)s "
                                  "AND water_as_utility = %(ui)s "
                                  "AND NAME != %(me)s AND reading_date >= %(rd)s ", {'tc': self.owner_contract,
                                                                                     'ui': self.water_as_utility,
                                                                                     'me': self.name,
                                                                                     'rd': self.reading_date
                                                                                     })
            if count[0][0]:
                frappe.throw(
                    _(
                        "The Reading date you entered is the same as or less than the previous reading."
                        "Enter a valid reading date"))

    def check_if_older_exists(self):
        if self.measurement_status == 'New' and not self.is_opening_entry:
            count = frappe.db.sql("SELECT count(*) FROM `tabWater Utility  Measurement` WHERE "
                                  "measurement_status = 'New' AND owner_contract = %(tc)s "
                                  "AND water_as_utility = %(ui)s AND is_opening_entry = 0 "
                                  "AND NAME != %(me)s", {'tc': self.owner_contract,
                                                         'ui': self.water_as_utility,
                                                         'me': self.name
                                                         })
            if count[0][0]:
                frappe.throw(
                    _(
                        "An unbilled measurement already exists. Cancel / Bill or Modify that entry "
                        "before making another"))

    def check_opening_item(self):
        utility_item = self.get_utility_item()
        if self.measurement_status == 'New' and utility_item.measurement_type == 'Meter Reading':
            count = frappe.db.sql("SELECT count(*) FROM `tabWater Utility  Measurement` WHERE "
                                  "measurement_status != 'Cancelled' AND owner_contract = %(tc)s "
                                  "AND water_as_utility = %(ui)s AND is_opening_entry = 1 "
                                  "AND NAME != %(me)s", {'tc': self.owner_contract,
                                                         'ui': self.water_as_utility,
                                                         'me': self.name
                                                         })
            if not count[0][0] and not self.is_opening_entry:
                frappe.throw(
                    _("For an item of measurement type of 'Meter Reading', the first entry must be an opening item."))

            if count[0][0] and self.is_opening_entry:
                frappe.throw(
                    _("Opening Entry already exists for this Tenancy Contract."))
