odoo.define('equip3_agri_operations.list_view_report', function(require){
    'use strict';

    var ListController = require('web.ListController');
    var ListRenderer = require('web.ListRenderer');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');

    var ListRendererReport = ListRenderer.extend({
        events: _.extend({}, ListRenderer.prototype.events, {
            'click .o_data_row': '_onClickListRow',
        }),

        _renderRow: function (record) {
            var tr = this._super.apply(this, arguments);
            tr.attr('data-record-id', record.data.id);
            return tr;
        },
    
        _onClickListRow: function (ev) {
            ev.preventDefault();
            var recordId = ev.currentTarget.dataset && ev.currentTarget.dataset.recordId ? parseInt(ev.currentTarget.dataset.recordId) : null;
            var modelName;
            if (['agriculture.nursery.report', 'agriculture.harvest.report'].includes(this.state.model)){
                modelName = 'agriculture.daily.activity.record';
            }
            if (recordId && modelName){
                ev.preventDefault();
                return this.do_action({
                    type: 'ir.actions.act_window',
                    name: 'Activity Record',
                    target: 'current',
                    res_id: recordId,
                    res_model: modelName,
                    views: [[false, 'form']],
                });
            }
        },
    });


    var ListControllerReport = ListController.extend({
        buttons_template: 'ListViewReport.buttons',
        events: _.extend({}, ListController.prototype.events, {
            'click .o_list_print_pdf': '_onPrintPdf',
            'click .o_list_print_xlsx': '_onPrintXlsx'
        }),

        _onPrintPdf: function(e){
            e.preventDefault();
            var state = this.model.get(this.handle);
            var self = this;
            return this._rpc({
                model: self.modelName,
                method: 'get_report_values',
                args: [state]
            }).then(function(result){
                var actionName = 'equip3_agri_operations.' + self.modelName.replace(/\./g, '_');
                var action = {
                    type: 'ir.actions.report',
                    report_type: 'qweb-pdf',
                    report_name: actionName,
                    report_file: actionName,
                    data: {
                        'report_data': result
                    }
                };
                return self.do_action(action);
            });
        },

        _onPrintXlsx: async function(e){
            e.preventDefault();
            var state = this.model.get(this.handle);
            var self = this;
            self._rpc({
                model: self.modelName,
                method: 'get_xlsx_report',
                args: [state]
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

    var ListViewReport = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: ListControllerReport,
            Renderer: ListRendererReport
        }),
    });

    viewRegistry.add('list_view_report', ListViewReport);

    return {
        ListControllerReport: ListControllerReport,
        ListRendererReport: ListRendererReport
    };
});