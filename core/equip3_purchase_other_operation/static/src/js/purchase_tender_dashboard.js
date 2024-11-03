odoo.define("equip3_purchase_other_operation.PurchaseTenderDashboard", function (
    require
) {
    "use strict";

    var AbstractAction = require("web.AbstractAction");
    var core = require("web.core");
    var Qweb = core.qweb;
    var session = require('web.session');

    var PurchaseTenderDashboard = AbstractAction.extend({
        template: "PurchaseTenderDashboard",
        events: {
            'click .total_tender': '_onTotalTenderClick',
            'click .active_tender': '_onActiveTenderClick',
            'click .today_tender': '_onTodayTenderClick',
        },
        start: function () {
            $('body').addClass('purchase_tender_dashboard_page');
            this.load_data();
        },
        load_data: function () {
            var self = this;
            this._rpc({
                model: 'purchase.agreement',
                method: 'get_agreement_data',
                args: [],
            }).then((result) => {
                var content = Qweb.render('PurchaseTenderDashboardContent', result);
                self.$el.append(content);
            });
        },
        _onTotalTenderClick: function(event) {
            event.preventDefault();
            var self = this;
            this._rpc({
                model: 'purchase.agreement',
                method: 'show_total_tender',
            }).then((result) => {
                self.do_action(result);
            });
        },
        _onActiveTenderClick: function(event) {
            event.preventDefault();
            var self = this;
            this._rpc({
                model: 'purchase.agreement',
                method: 'show_active_tender',
            }).then((result) => {
                self.do_action(result);
            });
        },
        _onTodayTenderClick: function(event) {
            event.preventDefault();
            var self = this;
            this._rpc({
                model: 'purchase.agreement',
                method: 'show_today_tender',
            }).then((result) => {
                self.do_action(result);
            });
        },
    });

    core.action_registry.add("purchase_tender_dashboard", PurchaseTenderDashboard);
    return PurchaseTenderDashboard;


});