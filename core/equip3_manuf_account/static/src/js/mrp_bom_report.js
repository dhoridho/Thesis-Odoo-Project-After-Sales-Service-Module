odoo.define('equip3_manuf_account.mrp_bom_report', function (require) {
    'use strict';

    var MrpBomReport = require('mrp.mrp_bom_report');

    MrpBomReport.include({
        get_labors: function(event) {
            var self = this;
            var $parent = $(event.currentTarget).closest('tr');
            var activeID = $parent.data('bom-id');
            var qty = $parent.data('qty');
            var level = $parent.data('level') || 0;
            return this._rpc({
                    model: 'report.mrp.report_bom_structure',
                    method: 'get_labors',
                    args: [
                        activeID,
                        parseFloat(qty),
                        level + 1
                    ]
                })
                .then(function (result) {
                    self.render_html(event, $parent, result);
                });
          },
    });

});