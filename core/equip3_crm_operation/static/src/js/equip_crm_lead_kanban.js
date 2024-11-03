odoo.define('equip3_crm_operation.EquipCrmLeadKanban', function(require){
    "use strict";

    const KanbanModel = require('web.KanbanModel');
    const KanbanColumn = require('web.KanbanColumn');
    const KanbanRenderer = require('web.KanbanRenderer');
    const KanbaView = require('web.KanbanView');
    
    const field_registry = require('web.field_registry');
    const view_registry = require('web.view_registry');

    const KanbanActivity = field_registry.get('kanban_activity');


    const EquipKanbanActivity = KanbanActivity.extend({
        _render: function () {
            const spanClasses = [];
            if (this.recordData.activity_exception_decoration) {
                spanClasses.push('text-' + this.recordData.activity_exception_decoration);
            }
            let $span = this.$('.o_activity_btn > span');
            let $activityBtn = $span.parent('.o_activity_btn');
            $activityBtn
                .attr('class', (index, className) => className.replace(/(^|\s)o_activity_color_-\S+/g, ''))
                .addClass('o_activity_color_' + (this.activityState || 'default'));
            $span.append($('<img src="/equip3_crm_operation/static/img/gala_clock.svg" alt="Activity"></img>'));
    
            if (this.$el.hasClass('show')) {
                this._renderDropdown();
            }
        },
    });

    const EquipKanbanModel = KanbanModel.extend({
        _load: function (dataPoint, options) {
            if (dataPoint.groupedBy.length && this.loadParams) {
                return this._readColorGroup(dataPoint, options)
            }
            return this._super.apply(this, arguments);
        },

        __get: function () {
            let result = this._super.apply(this, arguments);
            let dp = result && this.localData[result.id];
            if (dp && dp.headerColor) {
                result.headerColor = dp.headerColor;
            }
            return result;
        },

        _readColorGroup: function(list, options) {
            var progressBarDef, colorDef;
            
            if (list.progressBar) {
                progressBarDef = this._readProgressBarGroup(list, options);
            }
            var self = this;
            let optionColor = _.find(this.loadParams.fieldsInfo.kanban, (field) => field.name === list.groupedBy[0] && field.options && field.options.field_color);
            if (optionColor){
                colorDef = this._rpc({
                    model: this.loadParams.fields[[optionColor.name]].relation,
                    method: 'search_read',
                    domain: [],
                    fields: [optionColor.options.field_color]
                });
            }
            return Promise.all([progressBarDef, colorDef]).then((results) => {
                if (optionColor){
                    let result = results[1];
                    _.each(list.data, (groupID) => {
                        let group = self.localData[groupID];
                        let record = _.find(result, (res) => res.id === group.res_id);
                        if (record){
                            group.headerColor = record[[optionColor.options.field_color]];
                        }
                    });
                }
                return list;
            });
        }
    });


    const EquipKanbanColumn = KanbanColumn.extend({
        template: 'EquipKanbanView.Group',

        init: function (parent, data, options, recordOptions) {
            this._super.apply(this, arguments);
            this.headerColor = data.headerColor || '#4C4C4C'; // default to color #4C4C4C
        }
    });

    const EquipKanbanRenderer = KanbanRenderer.extend({
        config: _.extend({}, KanbanRenderer.prototype.config, {
            KanbanColumn: EquipKanbanColumn
        }),

        start: function(){
            this.$el.addClass('o_equip_crm_lead_kanban');
            return this._super.apply(this, arguments);
        }
    });

    const EquipKanbanView = KanbaView.extend({
        config: _.extend({}, KanbaView.prototype.config, {
            Model: EquipKanbanModel,
            Renderer: EquipKanbanRenderer
        })
    });

    field_registry.add('equip_kanban_activity', EquipKanbanActivity);
    view_registry.add('o_equip_crm_lead_kanban', EquipKanbanView);

    return {
        EquipKanbanActivity: EquipKanbanActivity,
        EquipKanbanModel: EquipKanbanModel,
        EquipKanbanColumn: EquipKanbanColumn,
        EquipKanbanRenderer: EquipKanbanRenderer,
        EquipKanbanView: EquipKanbanView
    };
});