// Copyright (c) 2018, Stephen and contributors
// For license information, please see license.txt

frappe.ui.form.on('Water Utility  Measurement', {
	refresh: function(frm) {
	frm.toggle_display(['meter_reading', 'usage_units', 'monetary_amount'], 0);
            frm.toggle_reqd(['meter_reading', 'usage_units', 'monetary_amount'], 0);
            if(frm.doc.utility_item){
                frm.events.enable_measure(frm);
            }
            if(frm.doc.__islocal){
                frm.set_query('owner_contract', function(){
                    return {
                        query: "water_management.water_management.doctype.water_owner_contract.water_owner_contract.water_owner_query",
                        filters: {
                            tc_filters: ['Active'],
                            property: ''
                        }
                    }
                });
            }

	},
	owner_contract: function (frm) {
            if(frm.doc.owner_contract){
                frm.set_query('water_as_utility', function(doc, doctype, doc_name){
                    return {
                        query: "water_management.water_management.doctype.utility_items.utility_items.utility_item_query",
                        filters: {
                            "owner_contract": doc.owner_contract
                        }
                    }
                });
            }else{
                frm.set_query('utility_item', function(doc, doctype, doc_name){
                    return {
                        filters: {

                        }
                    }
                });
            }
    },
    water_as_utility: function(frm){
            if(frm.doc.water_as_utility) {
                frm.events.enable_measure(frm);
            }
        },
    enable_measure: function(frm){
        frappe.model.with_doc('Utility Items', frm.doc.water_as_utility, function(){
            var ui_doc = frappe.model.get_doc('Utility Items', frm.doc.water_as_utility);
            if(ui_doc.measurement_type === 'Meter Reading'){
                frm.toggle_display('meter_reading', 1);
                frm.toggle_reqd('meter_reading', 1);
            }
            if(ui_doc.measurement_type === 'Usage Units'){
                frm.toggle_display('usage_units', 1);
                frm.toggle_reqd('usage_units', 1);
            }
            if(ui_doc.measurement_type === 'Monetary Amount'){
                frm.toggle_display('monetary_amount', 1);
                frm.toggle_reqd('monetary_amount', 1);
            }
            if(frm.doc.measurement_status === 'Billed'){
                frm.toggle_enable('*', 0);
                if(ui_doc.measurement_type === 'Meter Reading') {
                    frm.toggle_display('usage_units', 1);
                }
            }
        });
    }

});
