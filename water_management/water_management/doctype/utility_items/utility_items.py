# -*- coding: utf-8 -*-
# Copyright (c) 2018, Stephen and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.desk.reportview import get_match_cond
from frappe.utils import cstr


class UtilityItems(Document):
    pass

    def autoname(self):
        # group name and id
        self.name = "-".join(filter(None,
                                    [cstr(self.get(f)).strip() for f in ["property_name", "item_name"]]))



def utility_item_query(doctype, txt, searchfield, start, page_len, filters):
    return frappe.db.sql(("select ui.name from `tabUtility Items` as ui,\n"
                          "     `tabWater Bills Items` as tci\n"
                          "		where ui.{key} like %(txt)s\n"
                          "			{mcond}\n"
                          "     and tci.utility_item = ui.name and tci.parent = %(tc)s\n"
                          "		order by\n"
                          "			if(locate(%(_txt)s, ui.name), locate(%(_txt)s, ui.name), 99999),\n"
                          "			ui.idx desc,\n"
                          "			ui.name\n"
                          "		limit %(start)s, %(page_len)s").format(**{
        'key': searchfield,
        'mcond': get_match_cond(doctype)
    }), {
                             'txt': "%%%s%%" % txt,
                             '_txt': txt.replace("%", ""),
                             'start': start,
                             'page_len': page_len,
                             'tc': filters["owner_contract"]
                         })
