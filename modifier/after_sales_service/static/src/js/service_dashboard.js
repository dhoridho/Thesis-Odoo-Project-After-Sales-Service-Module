odoo.define('service_dashboard.dashboard', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var QWeb = core.qweb;
    var rpc = require('web.rpc');

    var ServiceDashboard = AbstractAction.extend({
        template: 'service_dashboard_template',

        events: {
            'click .service-request-card': '_onServiceRequestClick',
            'click .warranty-claim-card': '_onWarrantyClaimClick',
        },

        init: function (parent, action) {
            this._super.apply(this, arguments);
            this.dashboardData = {
                serviceRequests: {},
                warrantyClaims: {}
                // You can add more data keys here as needed
            };
        },

        willStart: function () {
            var self = this;
            return Promise.all([
                // Service Requests RPC
                rpc.query({
                    model: 'service.dashboard',
                    method: 'get_service_request_stats',
                }).then(function (service_result) {
                    self.dashboardData.serviceRequests = service_result;
                }),

                // Warranty Claims RPC
                rpc.query({
                    model: 'service.dashboard',
                    method: 'get_warranty_claim_stats',
                }).then(function (warranty_result) {
                    self.dashboardData.warrantyClaims = warranty_result;
                })

                // You can add more RPC queries here following the same pattern
                // For example:
                // rpc.query({
                //     model: 'service.dashboard',
                //     method: 'get_another_stat',
                // }).then(function (another_result) {
                //     self.dashboardData.anotherStat = another_result;
                // })
            ]).catch(function(error) {
                console.error("Error fetching dashboard data:", error);
                // Optionally set default empty values or handle the error
            });
        },

        start: function () {
            var self = this;
            if (this.dashboardData.serviceRequests && this.dashboardData.warrantyClaims) {
                this._renderDashboard();
            } else {
                console.error("Data is not available to render dashboard.");
            }
            return this._super.apply(this, arguments);
        },

        _renderDashboard: function () {
            var self = this;

            self.$('.o_service_dashboard').empty();

            var content = QWeb.render(self.template, {
                widget: self,
                dashboard_data: self.dashboardData // Update this to match your template
            });

            self.$('.o_service_dashboard').append(content);
        },

        // ... rest of the methods remain the same
    });

    core.action_registry.add('service_dashboard', ServiceDashboard);
    return ServiceDashboard;
});