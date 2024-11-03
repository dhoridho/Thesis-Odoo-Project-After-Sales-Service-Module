odoo.define('equip3_mining_dashboard.KanbanSiteControl', function(require){
    "use strict";

    var kanbanView = require('web.KanbanView');
    var kanbanRenderer = require('web.KanbanRenderer');
    var kanbanRecord = require('web.KanbanRecord');
    var viewRegistry = require('web.view_registry');

    var KanbanSiteRecord = kanbanRecord.extend({
        _openRecord: function(){
            return this.do_action({
                type: 'ir.actions.client',
                name: this.recordData.mining_site + ' Weather',
                tag: 'mining_site_dashboard',
                res_model: 'mining.site.control',
                res_id: this.recordData.id,
            });
        }
    });

    var KanbanSiteRenderer = kanbanRenderer.extend({
        config: _.extend({}, kanbanRenderer.prototype.config, {
            KanbanRecord: KanbanSiteRecord
        })
    });

    var KanbanSiteView = kanbanView.extend({
        config: _.extend({}, kanbanView.prototype.config, {
            Renderer: KanbanSiteRenderer
        })
    });

    viewRegistry.add('mining_site_kanban', KanbanSiteView);
    
    return {
        KanbanSiteRecord: KanbanSiteRecord,
        KanbanSiteRenderer: KanbanSiteRenderer,
        KanbanSiteView: KanbanSiteView
    };

});