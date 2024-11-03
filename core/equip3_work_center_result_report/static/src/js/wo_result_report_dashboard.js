odoo.define('equip3_work_center_result_report.work_center_result_report_board', function (require) {
    "use strict";


    var AbstractAction = require('web.AbstractAction');
    var rpc = require('web.rpc');
    var core = require('web.core');
    var _t = core._t;
    var session = require('web.session');
    var QWeb = core.qweb;
        
    var work_center_result_report_board = AbstractAction.extend({
        title: core._t('Work Center Result Report'),
        template: 'equip3_work_center_result_report.wo_result_report_dashboard',
        dashboard_widgets: {},
        events: {
            'change select[name="work_center_select"]': 'change_work_center_select',
            'click .btn_board_clear':'board_clear',
            'click .btn_board_search':'board_search',
            'click .btn_board_reload':'board_reload',
            'click .o_button_remarks': '_onButtonRemarksClick'
        },


        init: function (parent, params) {
            this._super.apply(this, arguments);
            this.list_wo_n_model = []
            this.consumption_list_view_id = false;
        },

        get_consumption_list_view_id: function(){
            var self = this;
            this._rpc({
                model: 'ir.model.data',
                method: 'get_object_reference',
                args: ['equip3_work_center_result_report', 'view_mrp_consumption_tree_workcenter_result_report'],
            })
            .then(function (viewId) {
                self.consumption_list_view_id = viewId[1];
            });
        },

        start: function () {
            const self = this;
            return this._super().then(function () {
                self.get_consumption_list_view_id();
                self.render_dashboard_widgets();
            });
        },

        willStart: function () {
            return $.when(
                this._super.apply(this, arguments),
                this.fetch_data(),
            );
        },

        fetch_data: function () {
            const self = this;
            return this._rpc({
                route: '/wo_result_report_dashboard/fetch_data',
                params: {
                },
            }).then(function (result) {
                self.list_wo_n_model = result.list_wo_n_model;
            });

        },


        render_dashboard_widgets: function () {
            const self = this;    
            var option_workcenter = '<option value=""></option>'
            for (let i = 0; i < self.list_wo_n_model.length; i++) {
                option_workcenter+= '<option value='+self.list_wo_n_model[i].id+'>'+self.list_wo_n_model[i].name+'</option>'
            }
            $(self.$el.find('.wo_result_report_dashboard select[name="work_center_select"]')).append(option_workcenter)
            $(self.$el.find('.wo_result_report_dashboard select[name="work_center_select"]')).select2({})

        },

        change_work_center_select: function (e) {
            const self = this;    
            var work_center_select_id = $('.wo_result_report_dashboard select[name="work_center_select"]').val()
            if(work_center_select_id && work_center_select_id != ''){
                var find_wo = self.list_wo_n_model.filter((line)=>{return parseInt(line.id) == parseInt(work_center_select_id)});
                var model = find_wo[0].model || ''
                $('.wo_result_report_dashboard input[name="work_center_model_input"]').val(model)
            }
        },


        board_clear: function () {
                $('.wo_result_report_dashboard select[name="work_center_select"]').val('').trigger('change')
                $('.wo_result_report_dashboard input[name="work_center_model_input"]').val('')
                $('.wo_result_report_dashboard input[name="period_month_year"]').val('')
                $('.wo_result_report_dashboard .o_website_dashboard_content').html('')
        },

        board_reload: function () {
            this.board_search()
        },

        board_search: function () {
            const self = this;   
            var work_center_select_id = $('.wo_result_report_dashboard select[name="work_center_select"]').val()
            var month_select = $('.wo_result_report_dashboard input[name="period_month_year"]').val()
            if(!work_center_select_id || work_center_select_id == '' || !month_select || month_select == '') {
                self.do_warn(
                    _t("Warning"), _t("Please select workcenter and month first."));
            }
            else{
                $('.wo_result_report_dashboard .o_website_dashboard_content').html('')
                this._rpc({
                    route: '/wo_result_report_dashboard/get_format_table',
                    params: {
                        'period_month':month_select,
                        'work_center_id':parseInt(work_center_select_id)
                    },
                }).then(function (format_table) {
                    $('.wo_result_report_dashboard .o_website_dashboard_content').html(format_table)
                });
                    
            }
        },

        _onButtonRemarksClick: function(ev){
            var $target = $(ev.currentTarget);
            var recordIds = $target.data('record_ids');
            return this.do_action({
                name: 'Production Records',
                res_model: 'mrp.consumption',
                views: [[this.consumption_list_view_id, 'list']],
                view_mode: 'list',
                type: 'ir.actions.act_window',
                target: 'new',
                domain: [['id', 'in', recordIds]]
            });
        }

    });
    core.action_registry.add('tag_work_center_result_report_board', work_center_result_report_board);
    return {
        work_center_result_report_board: work_center_result_report_board,
    };
});
