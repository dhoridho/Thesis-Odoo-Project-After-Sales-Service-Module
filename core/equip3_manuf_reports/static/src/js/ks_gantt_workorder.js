odoo.define('equip3_manuf_reports.ksGanttWorkorder', function(require){
    "use strict";

    var ksGanttRenderer = require('ks_gantt_view.Renderer');
    var ksGanttView = require('ks_gantt_view.View');
    var viewRegistry = require('web.view_registry');

    var ksGanttWorkorderRenderer = ksGanttRenderer.extend({
        template: "equip3_manuf_reports.ks_gantt_content",
        
        ks_gantt_plugins: function(){
            gantt.config.drag_resize = false;
            this._super.apply(this, arguments);
        },

        init: function (parent, state, params) {
            this._super.apply(this, arguments);
            gantt.ext.zoom.setLevel("month");
        },

        _render: function () {
            Promise.resolve();

            if (this.ks_gantt_rendered) {
                gantt.clearAll();
                this.ks_task_drag_and_drop();
                delete gantt.config.ks_owner_task_list;
                gantt.config.ks_gantt_task_data = this.ks_parse_gantt_data();
                gantt.config.counter = true;
                if (gantt.config.ks_show_resource_panel && gantt.config.ks_owner_task_list && gantt.config.counter) {
                    gantt.config.ks_resources_store.parse(gantt.config.ks_owner_task_list);
                    gantt.config.counter = false;
                }
                gantt.parse(gantt.config.ks_gantt_task_data);
                // Add markers
                this.ks_handle_gantt_view_marker();
            }
        },

        ks_parse_gantt_data: function () {
            var data = this._super.apply(this, arguments);
            var tasks = _.filter(data.data, o => o.type !== 'project' && o.date_planned_start);
            var groups = _.map(tasks, o => o.parent);
            data.data = _.filter(data.data, o => (o.type !== 'project' && o.date_planned_start) || groups.includes(o.id));
            data.data = _.sortBy(data.data, function(d){
                if (d.type === 'project'){
                    var dates = _.map(_.filter(data.data, task => task.parent === d.id), o => o.date_planned_start);
                    return Math.min.apply(Math, dates);
                } else {
                    return d.date_planned_start;
                }
            });
            return data;
        }
    });

    var ksGanttWorkorderView = ksGanttView.extend({
        config: _.extend({}, ksGanttView.prototype.config, {
            Renderer: ksGanttWorkorderRenderer,
        }),

        ks_manage_gantt_arch: function () {
            this.ks_get_gantt_no_field_attribute().forEach(function (field_info) {
                if (field_info === 'js_class'){
                    delete this.arch.attrs[field_info];
                }
            }.bind(this));
            this._super.apply(this, arguments);
        },

        ks_get_gantt_no_field_attribute: function () {
            var result = this._super.apply(this, arguments);
            result.push('js_class');
            return result
        },
    });

    viewRegistry.add('ks_gantt_workorder', ksGanttWorkorderView);

    return {
        ksGanttWorkorderRenderer: ksGanttWorkorderRenderer,
        ksGanttWorkorderView: ksGanttWorkorderView
    };
});