odoo.define('equip3_inventory_reports.InventoryReportListControllerView', function (require) {
"use strict";

    var core = require('web.core');
    var ListController = require('web.ListController');
    var InventoryReportListController = require('stock.InventoryReportListController');
    var qweb = core.qweb;

     var include_inventory_reportlist = {
        _onOpenWizard: function () {
             this._super.apply(this, arguments);
             var self = this;
             var context = {
                 active_model: this.modelName,
             };

             this.do_action({
                res_model: 'stock.quantity.history',
                name : 'Inventory Valuation',
                views: [[false, 'form']],
                target: 'new',
                type: 'ir.actions.act_window',
                context: context,
            });

        },
     };
     InventoryReportListController.include(include_inventory_reportlist);
});

