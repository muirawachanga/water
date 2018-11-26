frappe.listview_settings['Billing Periods'] = {
    add_fields: ['period_name', 'start_date', 'end_date', 'period_type'],
    onload: function(listview) {
        var method_monthly = 'water_management.water_management.utils.create_monthly_periods';
        var method_quarterly = 'water_management.water_management.utils.create_quarterly_periods';

        listview.page.add_action_item(__("Create Monthly Periods"), function() {
            frappe.call({
                method: method_monthly,
                callback: function(data, res){
                    listview.refresh();
                    frappe.msgprint(__('Monthly Periods for current year created successfully.'));
                }
            });
        });

        listview.page.add_action_item(__("Create Quarterly Periods"), function() {
            frappe.call({
                method: method_quarterly,
                callback: function(data, res){
                    listview.refresh();
                    frappe.msgprint(__('Quarterly Periods for current year created successfully.'));
                }
            });
        });
    }
}
