odoo.define('equip3_crm_operation.CustomerKanban', function (require) {
    "use strict";

    var viewRegistry = require('web.view_registry');
    var core = require('web.core');
    var _t = core._t;
    
    var kanbanColumn = require('web.KanbanColumn');
    var kanbanRenderer = require('web.KanbanRenderer');
    var kanbanView = require('web.KanbanView');

    var customerKanbanColumn = kanbanColumn.extend({
        init: function (parent, data, options, recordOptions) {
            this._super.apply(this, arguments);
            var value = data.value;
            if (options.grouped_by_m2o && options.groupedBy === 'user_id' && (value === undefined || value === false)){
                this.title = _t('No Salesperson');
            }
        }
    });

    var customerKanbanRenderer = kanbanRenderer.extend({
        config: Object.assign({}, kanbanRenderer.prototype.config, {
            KanbanColumn: customerKanbanColumn,
        })
    });

    var customerKanbanView = kanbanView.extend({
        config: _.extend({}, kanbanView.prototype.config, {
            Renderer: customerKanbanRenderer,
        })
    });


    viewRegistry.add('res_partner_kanban_no_salesperson', customerKanbanView);

    return {
        customerKanbanColumn: customerKanbanColumn,
        customerKanbanRenderer: customerKanbanRenderer,
        customerKanbanView: customerKanbanView
    }

});