// Copyright (c) 2018, Stephen and contributors
// For license information, please see license.txt

frappe.ui.form.on('Water Owner Contract', {
	refresh: function(frm) {
	if (frm.doc.contract_status == 'Active' || frm.doc.contract_status == 'Suspended') {
                frm.add_custom_button(__("Create Invoice"), function() {
                    frm.events.make_invoice(frm);
                }).addClass("btn-primary");
    }
            if (frm.doc.contract_status !== "New") {
                frm.toggle_enable('*', 0);
                if (frm.doc.contract_status != 'Terminated') {
                    frm.toggle_enable(['items','grace_period', 'auto_generate_invoice', 'email_invoice', 'termination_date'], 1);
                }
            }

	},
	    validate: function(frm) {
            if (!frm.doc.start_date && frm.doc.contract_status == "Active") {
                msgprint(__("You must set the contract start date before approving"));
                frappe.validated = false;
                return
            }
            if (!frm.doc.end_date && frm.doc.contract_status == "Active") {
                msgprint(__("You must set the contract end date before approving"));
                frappe.validated = false;
                return
            }
            if (!frm.doc.termination_date && frm.doc.contract_status == "Terminated") {
                msgprint(__("Please set the contract termination date."));
                frappe.validated = false;
                return;
            }
            if (!frm.doc.cancellation_date && frm.doc.contract_status == "Cancelled") {
                frm.set_value('cancellation_date', get_today());
                frappe.validated = true;
            }

            if (frm.doc.contract_status != "New") {
                var items = frm.doc.items;
                if(!items.length){
                    msgprint(__("You Cannot approve a water contract with no billing items. Not Saved."));
                    frappe.validated = false;
                    return;
                }
                var items_grid = frm.fields_dict["items"].grid;
                for (var i = 0; i < items.length; i++) {
                    if(items[i].is_utility_item){
                        if(!items[i].utility_item){
                            msgprint(__("Item: " + item[i].item_name + " is marked as Utility Item " +
                                "but has no Utility Item choosen"));
                            frappe.validated = false;
                            return;
                        }
                    }
                }
                frappe.validated = true;
            }

    },
    make_invoice: function(frm) {
            frappe.model.open_mapped_doc({
                method: "water_management.water_management.doctype.water_owner_contract.water_owner_contract.make_sales_invoice",
                frm: frm
            });
    },
	start_date: function(frm) {
            if (frm.doc.start_date) {
                frm.set_value('date_of_first_billing', frm.doc.start_date);
                var msg = __('Date of First Billing set to: ') + frm.doc.start_date + __('. Note that you can select a different date if you wish.');
                msgprint(msg);
            } else {

            }
    },
    date_of_first_billing: function(frm) {
        if (frm.doc.start_date) {
            if (frappe.datetime.get_diff(frm.doc.start_date, frm.doc.date_of_first_billing) > 0) {
                msgprint(__('Date of First Billing cannot be earlier than start date.'));
                frm.set_value('date_of_first_billing', '');
            }
        }
    },

});

cur_frm.cscript.item_code = function(doc, cdt, cdn) {
    var d = locals[cdt][cdn];
    if (d.item_code) {
        return frappe.call({
            method: "water_management.water_management.doctype.water_owner_contract.water_owner_contract.get_item_details",
            args: {
                "item_code": d.item_code,
                "start_date": cur_frm.doc.start_date
            },
            callback: function(r, rt) {
                if (r.message) {
                    $.each(r.message, function(k, v) {
                        frappe.model.set_value(cdt, cdn, k, v);
                    });
                    refresh_field('image_view', d.name, 'items');
                }
            }
        })
    }
};
