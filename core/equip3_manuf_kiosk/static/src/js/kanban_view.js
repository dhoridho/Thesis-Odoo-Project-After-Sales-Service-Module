odoo.define('equip3_manuf_kiosk.KanbanRecordKiosk', function(require){
    "use strict";

    var kanbanView = require('web.KanbanView');
    var kanbanRenderer = require('web.KanbanRenderer');
    var kanbanRecord = require('web.KanbanRecord');
    var viewRegistry = require('web.view_registry');

    var kanbanRecordKiosk = kanbanRecord.extend({
        _openRecord: function(){
            var context = this.state.context;
            var previousContext = {};
            _.each(['pending', 'progress', 'ready', 'late'], function(state){
                previousContext['search_default_' + state] = context['search_default_' + state] ? true: false;
            });

            return this.do_action({
                type: 'ir.actions.client',
                name: this.recordData.name,
                tag: 'mrp_kiosk_home',
                res_model: 'mrp.workorder',
                res_id: this.recordData.id,
                previousContext: previousContext
            });
        }
    });

    var kanbanRendererKiosk = kanbanRenderer.extend({
        config: _.extend({}, kanbanRenderer.prototype.config, {
            KanbanRecord: kanbanRecordKiosk
        })
    });

    var kanbanViewKiosk = kanbanView.extend({
        config: _.extend({}, kanbanView.prototype.config, {
            Renderer: kanbanRendererKiosk
        })
    });

    viewRegistry.add('mrp_workorder_kanban_kiosk', kanbanViewKiosk);
    
    return {
        kanbanRecordKiosk: kanbanRecordKiosk,
        kanbanRendererKiosk: kanbanRendererKiosk,
        kanbanViewKiosk: kanbanViewKiosk
    };

});