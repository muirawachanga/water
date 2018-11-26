from __future__ import unicode_literals

from frappe import _


def get_data():
    return [
        {
            "label": _("Documents"),
            "icon": "icon-star",
            "items": [
                {
                    "type": "doctype",
                    "name": "Water Owner Contract",
                    "description": _("Water Owner Contract database.")
                },
                {
                    "type": "doctype",
                    "name": "Water Utility  Measurement",
                    "description": _("Water Utility Measurement database.")
                }
            ]
        },
        {
            "label": _("Utility Flow"),
            "icon": "icon-star",
            "items": [
                {
                    "type": "doctype",
                    "name": "Utility Items",
                    "description": _("Utility Items database.")
                },
                {
                    "type": "doctype",
                    "name": "Billing Periods",
                    "description": _("Supplier database.")
                }
            ]
        }
    ]
