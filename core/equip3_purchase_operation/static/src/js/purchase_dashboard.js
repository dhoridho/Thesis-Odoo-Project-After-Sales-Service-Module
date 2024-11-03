odoo.define('equip3_purchase_operation.dashboard', function (require) {
    "use strict";


let dashboardValues;
var PurchaseListDashboardModel = require('purchase.dashboard').PurchaseListDashboardModel;
PurchaseListDashboardModel.include({

    _loadDashboard: function (super_def) {
        var self = this;
        var context = {}
        if (this.loadParams !== undefined) {
            context = this.loadParams.context;
        }
        else if (this.getParent() !== undefined && this.getParent().loadParams !== undefined) {
            context = this.getParent().loadParams;
        }
        var dashboard_def = this._rpc({
            model: 'purchase.order',
            method: 'retrieve_dashboard',
            context: context,
        });
        return Promise.all([super_def, dashboard_def]).then(function(results) {
            var id = results[0];
            dashboardValues = results[1];
            self.dashboardValues[id] = dashboardValues;
            return id;
        });
    },

});
});    