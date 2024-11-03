odoo.define('equip3_manuf_report.list_view_report_js', function(require){
    'use strict';

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
            if (recordId){
                ev.preventDefault();
                return this.do_action({
                    type: 'ir.actions.act_window',
                    name: 'Stock Move',
                    target: 'current',
                    res_id: recordId,
                    res_model: 'stock.move',
                    views: [[false, 'form']],
                });
            }
        },
    });


    var ListViewReport = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Renderer: ListRendererReport
        }),
    });

    viewRegistry.add('list_view_report_js', ListViewReport);

    return {
        ListRendererReport: ListRendererReport
    };
});