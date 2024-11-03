odoo.define('equip3_manuf_masterdata.mrp_bom_report', function (require) {
    'use strict';
    
    var MrpBomReport = require('mrp.mrp_bom_report');
    var core = require('web.core');

    var MrpBomReportExtend = MrpBomReport.extend({
        events: _.extend({}, MrpBomReport.prototype.events, {
            'click .o_mrp_bom_print_excel': '_onClickPrintExcel',
        }),
        _onClickPrintExcel: function(ev){
            ev.preventDefault();
            var self = this;
            self._rpc({
                model: 'mrp.bom',
                method: 'print_xlsx_report',
                args: [[self.given_context.active_id]],
            }).then(function(attachmentId) {
                if (attachmentId) {
                    return self.do_action({
                        'type': 'ir.actions.act_url',
                        'url': '/web/content/' + attachmentId + '?download=true',
                        'target': 'self'
                    });
                }
            });
        }
    });
    core.action_registry.add('mrp_bom_report', MrpBomReportExtend);
    return MrpBomReportExtend;
});