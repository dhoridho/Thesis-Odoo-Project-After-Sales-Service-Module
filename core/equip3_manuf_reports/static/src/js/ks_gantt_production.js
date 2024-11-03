odoo.define('equip3_manuf_reports.ksGanttProduction', function(require){
    "use strict";

    var ksGanttRenderer = require('ks_gantt_view.Renderer');
    var ksGanttView = require('ks_gantt_view.View');
    var viewRegistry = require('web.view_registry');
    var core = require('web.core');
    var _t = core._t;

    var ksGanttProductionRenderer = ksGanttRenderer.extend({

        ks_renderGantt: function () {
            this._super.apply(this, arguments);
            gantt.templates.tooltip_text = function(start, end, task){
                var ks_tooltip_text = "";

                // Task Name
                if (gantt.config.ks_project_tooltip_config) {
                    if (gantt.config.ks_project_tooltip_config.ks_tooltip_task_name) {
                        ks_tooltip_text += "<b>" + _t("Title : ") + "</b> " + task.text + "<br/>";
                    }
                }
                else {
                    ks_tooltip_text += "<b>" + _t("Title : ") + "</b> " + task.text + "<br/>";
                }

                if (task.product_id){
                    ks_tooltip_text += "<b>" + _t("Product : ") + "</b> " + task.product_id[1] + "<br/>";
                } else if (task.plan_name){
                    ks_tooltip_text += "<b>" + _t("Name : ") + "</b> " + task.plan_name + "<br/>";
                }

                // Task duration
                if (gantt.config.ks_project_tooltip_config) {
                    if (gantt.config.ks_project_tooltip_config.ks_tooltip_task_duration) {
                        if(task.ks_task_duration){
                            ks_tooltip_text += "<b>" + _t("Duration :") + "</b> " + task.ks_task_duration + " <br/>";
                        }
                        else{
                            ks_tooltip_text += "<b>" + _t("Duration :") + "</b> " + task.ks_task_difference + "<br/>";
                        }
                    }
                }
                else {
                    if (task.ks_task_duration){
                        ks_tooltip_text += "<b>" + _t("Duration :") + "</b> " + task.ks_task_duration + " <br/>";
                    }
                    else{
                        ks_tooltip_text += "<b>" + _t("Duration :") + "</b> " + task.ks_task_difference + "<br/>";
                    }
                }

                // Task start date
                if (gantt.config.ks_project_tooltip_config) {
                    if (gantt.config.ks_project_tooltip_config.ks_tooltip_task_start_date) {
                        ks_tooltip_text += "<b>" + _t("Start Date : ") + "</b> " + gantt.ks_gantt_view_datetime_format(task.start_date) + "<br/>";
                    }
                }
                else {
                    ks_tooltip_text += "<b>" + _t("Start Date : ") + "</b> " + gantt.ks_gantt_view_datetime_format(task.start_date) + "<br/>";
                }

                // Task end date
                if (gantt.config.ks_project_tooltip_config) {
                    if (gantt.config.ks_project_tooltip_config.ks_tooltip_task_end_date) {
                        ks_tooltip_text += "<b>" + _t("End Date : ") + "</b> " + gantt.ks_gantt_view_datetime_format(task.end_date) + "<br/>";
                    }
                }
                else {
                    ks_tooltip_text += "<b>" + _t("End Date : ") + "</b> " + gantt.ks_gantt_view_datetime_format(task.end_date) + "<br/>";
                }


                // Task Stage Id
                if (gantt.config.ks_project_tooltip_config && ['task', 'milestone'].includes(task.type)) {
                    if (gantt.config.ks_project_tooltip_config.ks_tooltip_task_stage) {
                        ks_tooltip_text += "<b>" + _t("Stage : ") + "</b> " + (task.stage_id ? task.stage_id[1] : task.stage_id) + "<br/>";
                    }
                }
                else if(['task', 'milestone'].includes(task.type)) {
                    ks_tooltip_text += "<b>" + _t("Stage : ") + "</b> " + (task.stage_id ? task.stage_id[1] : task.stage_id) + "<br/>";
                }
                else if(!task.type && gantt.config.ks_project_tooltip_config && gantt.config.ks_project_tooltip_config.ks_tooltip_task_stage){
                    ks_tooltip_text += "<b>" + _t("Stage : ") + "</b> " + (task.stage_id ? task.stage_id : false) + "<br/>";
                }

                // Task Deadline
                if (gantt.config.ks_project_tooltip_config && ['task', 'milestone'].includes(task.type)) {
                    if (gantt.config.ks_project_tooltip_config.ks_tooltip_task_deadline && task.ks_deadline_tooltip) {
                        ks_tooltip_text += "<b>" + _t("Deadline : ") + "</b> " + gantt.ks_gantt_view_datetime_format(task.ks_deadline_tooltip) + "<br/>";;
                    }
                }
                else if (task.ks_deadline_tooltip && ['task', 'milestone'].includes(task.type)) {
                    ks_tooltip_text += "<b>" + _t("Deadline : ") + "</b> " + gantt.ks_gantt_view_datetime_format(task.ks_deadline_tooltip) + "<br/>";;
                }

                // Task Progress
                if (gantt.config.ks_project_tooltip_config && ['task', 'milestone'].includes(task.type)) {
                    if (gantt.config.ks_project_tooltip_config.ks_tooltip_task_progress) {
                        ks_tooltip_text += "<b>" + _t("Progress : ") + "</b> " + Math.round(task.progress * 100) + '%' + "<br/>";
                    }
                }
                else if(['task', 'milestone'].includes(task.type)) {
                    ks_tooltip_text += "<b>" + _t("Progress : ") + "</b> " + Math.round(task.progress * 100) + '%' + "<br/>";
                }
                else if(!task.type && gantt.config.ks_project_tooltip_config && gantt.config.ks_project_tooltip_config.ks_tooltip_task_progress){
                    ks_tooltip_text += "<b>" + _t("Progress : ") + "</b> " + Math.round(task.progress * 100) + '%' + "<br/>";
                }

                // Task Constraint Type
                if (gantt.config.ks_project_tooltip_config && ['task', 'milestone'].includes(task.type)) {
                    if (gantt.config.ks_project_tooltip_config.ks_tooltip_task_constraint_type) {
                        ks_tooltip_text += "<b>" + _t("Constraint Type : ") + "</b> " + gantt.locale.labels[task.constraint_type] + "<br/>";
                    }
                }
                else if(['task', 'milestone'].includes(task.type)) {
                    ks_tooltip_text += "<b>" + _t("Constraint Type : ") + "</b> " + gantt.locale.labels[task.constraint_type] + "<br/>";
                }
                else if(!task.type && gantt.config.ks_project_tooltip_config && gantt.config.ks_project_tooltip_config.ks_tooltip_task_constraint_type){
                    ks_tooltip_text += "<b>" + _t("Constraint Type : ") + "</b> " + gantt.locale.labels[task.constraint_type] + "<br/>";
                }

                // Task Constraint Date
                if (task.constraint_date && !['asap', 'alap'].includes(task.constraint_type)){
                    if (gantt.config.ks_project_tooltip_config && ['task', 'milestone'].includes(task.type)) {
                        if (gantt.config.ks_project_tooltip_config.ks_tooltip_task_constraint_date && task.constraint_date && ['asap', 'alap'].indexOf(task.constraint_type) < 0) {
                            ks_tooltip_text += "<b>" + _t("Constraint Date : ") + "</b> " + gantt.ks_gantt_view_datetime_format(task.constraint_date) + "<br/>";
                        }
                    }
                    else if (task.constraint_date && ['asap', 'alap'].indexOf(task.constraint_type) < 0 && ['task', 'milestone'].includes(task.type)) {
                        ks_tooltip_text += "<b>" + _t("Constraint Date : ") + "</b> " + gantt.ks_gantt_view_datetime_format(task.constraint_date) + "<br/>";
                    }
                    else if(!task.type && gantt.config.ks_project_tooltip_config && gantt.config.ks_project_tooltip_config.ks_tooltip_task_constraint_date){
                        ks_tooltip_text += "<b>" + _t("Constraint Date : ") + "</b> " + gantt.ks_gantt_view_datetime_format(task.constraint_date) + "<br/>";
                    }
                }

                return ks_tooltip_text;
            }
        },

        ks_left_grid_columns: function(){
            this._super.apply(this, arguments);
            for (let i=0; i < gantt.config.columns.length; i++){
                if (gantt.config.columns[i].name === 'text'){
                    gantt.config.columns[i].label = _t('Reference');

                    var product = {
                        name: "product",
                        label: _("Product"),
                        tree: true,
                        width: 200,
                        resize: true,
                        template: function (obj) {
                            if (obj.product_id){
                                return obj.product_id[1];
                            }
                            return obj.mrp_plan_name;
                        },
                    };
                    gantt.config.columns.splice(i + 1, 0, product);
                    break;
                }
            }
            for (let i=0; i < gantt.config.columns.length; i++){
                if (gantt.config.columns[i].name === 'owner'){
                    gantt.config.columns.splice(i, 1);
                }
            }
        },

        init: function (parent, state, params) {
            this._super.apply(this, arguments);
            gantt.ext.zoom.setLevel("month");
        },

        ks_render_data_group_by: function(){
            var result = this._super.apply(this, arguments);
            for (let i=0; i < result.data.length; i++){
                if (typeof(result.data[i].id) == 'string'){
                    var orders = _.filter(result.data, function(item){
                        return item.parent === result.data[i].id;
                    });
                    if (orders){
                        result.data[i].plan_name = orders[0].mrp_plan_name;
                    }
                }
            }
            return result;
        },
    });
    
    var ksGanttProductionView = ksGanttView.extend({
        config: _.extend({}, ksGanttView.prototype.config, {
            Renderer: ksGanttProductionRenderer,
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

    viewRegistry.add('ks_gantt_production', ksGanttProductionView);

    return {
        ksGanttProductionRenderer: ksGanttProductionRenderer,
        ksGanttProductionView: ksGanttProductionView
    };
});