odoo.define('equip3_purchase_report.DashBoard', function (require) {
    "use strict";

    var Dashboard = require('xf_purchase_dashboard');

    Dashboard.include({
        events: _.extend({}, Dashboard.prototype.events, {
            "click .o_xf_purchase_dashboard_widget_line": function (ev) {
                const self = this;
                ev.preventDefault();
                let domain = $(ev.currentTarget).data('domain');
                var model_name = "Purchase Orders"
                var model = "purchase.order"
                if (eval(domain).includes('bid_selection')) {
                    model_name = "Purchase Tender"
                    model = "purchase.agreement"
                } else if (eval(domain).includes('purchase_request')) {
                    model_name = "Purchase Request Line"
                    model = "purchase.request.line"
                }
                this.do_action({
                    type: 'ir.actions.act_window',
                    name: model_name,
                    res_model: model,
                    views: [[false, 'list'], [false, 'form']],
                    view_mode: 'tree,form',
                    domain: domain,
                });
            },
        })
    });
});