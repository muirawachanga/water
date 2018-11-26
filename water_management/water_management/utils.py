# -*- coding: utf-8 -*-
# Copyright (c) 2016, Bituls Company Limited and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from datetime import date

import frappe
from frappe.exceptions import ValidationError, DataError
from frappe.utils import get_first_day, get_last_day
from frappe import _


class MissingUtilityItemException(ValidationError):
    pass


def create_period_if_not_exists(ref_date, type):
    if get_billing_period_for_date(ref_date, type):
        return
    if type == 'Monthly':
        create_monthly_periods(ref_date)
        return
    elif type == 'Quarterly':
        create_quarterly_periods(ref_date)
        return
    elif type == 'Yearly':
        create_yearly_periods(ref_date)
        return

    raise DataError(_('Unsupported Period Type: {}').format(type))


@frappe.whitelist()
def create_yearly_periods(ref_date=None):
    ref_date = ref_date or date.today()
    start = date(ref_date.year, 1, 1)
    end = date(ref_date.year, 12, 31)
    p_name = start.strftime('Year-%Y')
    doc = frappe.get_doc({"doctype": "Billing Periods", "period_name": p_name, "start_date": start, "end_date": end,
                          "period_type": "Yearly"})
    doc.save()


@frappe.whitelist()
def create_quarterly_periods(ref_date=None):
    ref_date = ref_date or date.today()
    q = 1
    for i in range(0, 12, 3):
        start = get_first_day(date(ref_date.year, 1, 1), 0, i)
        tmp = get_first_day(date(ref_date.year, 1, 1), 0, i + 2)
        end = get_last_day(tmp)
        prefix = 'Q{}-'.format(q)
        q += 1
        p_name = prefix + start.strftime('%Y')
        doc = frappe.get_doc({"doctype": "Billing Periods", "period_name": p_name, "start_date": start, "end_date": end,
                              "period_type": "Quarterly"})
        doc.save()


@frappe.whitelist()
def create_monthly_periods(ref_date=None):
    ref_date = ref_date or date.today()
    for i in range(12):
        start = get_first_day(date(ref_date.year, 1, 1), 0, i)
        end = get_last_day(start)
        p_name = start.strftime('%b-%Y')
        doc = frappe.get_doc({"doctype": "Billing Periods", "period_name": p_name, "start_date": start, "end_date": end,
                              "period_type": "Monthly"})
        doc.save()


def get_billing_period_for_date(base_date, type):
    """
    Find a billing period for a given date
    :param base_date: The dateuse when getting a period
    :param type: The period type. (Monthly, Quartely etc)
    :return: A Billing Period name if found or None
    """
    period = frappe.get_all("Billing Periods", ["name"], [["period_type", "=", type], ["start_date", "<=", base_date],
                            ["end_date", ">=", base_date]])
    if period:
        return period[0].name
    else:
        return None


def get_next_period(period_name, offset=1):
    """
    Get the period in relation to another. Offset determines the direction of relation. +ve is forward -ve is backwords
    :param period_name: The period to relate with
    :param offset: Direction of the relation.
    :return: A period, greater than 'period' or less than 'period' depending on the offset direction or None if no
    period is found at given offset
    """
    if offset == 0:
        return period_name
    period = frappe.get_doc('Billing Periods', period_name)
    if offset > 0:
        filt = [["start_date", ">=", period.get('start_date')]]
        order_by = "start_date"
    else:
        filt = [["start_date", "<=", period.get('start_date')]]
        order_by = "start_date desc"

    filt.append(["period_type", "=", period.get('period_type')])
    page_len = abs(offset) + 1
    fetched_periods = frappe.get_all("Billing Periods", fields=["name"], filters=filt, order_by=order_by,
                                     limit_page_length=page_len)

    if len(fetched_periods) < page_len:
        return None
    return fetched_periods[page_len - 1].name


def disable_quick_entry(dtn):
    doc = frappe.get_doc('DocType', dtn)
    doc.set('quick_entry', 0)
    return doc.db_update()
