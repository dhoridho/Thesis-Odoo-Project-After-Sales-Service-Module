odoo.define('equip3_inventory_other_operations.cost_details_report', function (require) {
'use strict';

var core = require('web.core');
var framework = require('web.framework');
var stock_report_generic = require('stock.stock_report_generic');

var QWeb = core.qweb;

var RepairReport = stock_report_generic.extend({
    
    get_html: function() {
        var self = this;
        var args = [
            this.given_context.active_id,
        ];
        return this._rpc({
            model: 'report.equip3_inventory_other_operations.report_cost',
            method: 'get_html',
            args: args,
            context: this.given_context,
        }).then(function (result) {
            self.data = result;
        });
    },
    set_html: function() {
        var self = this;
        return this._super().then(function () {
            self.$('.o_content').html(self.data.lines);
        });
    },
});

core.action_registry.add('cost_details_report', RepairReport);
return RepairReport;

});