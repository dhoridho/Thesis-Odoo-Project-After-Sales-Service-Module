odoo.define('equip3_agri_operations.budget_analysis_report', function (require) {
    'use strict';

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var monthYear = require('equip3_date_year.month_year');
    var field_utils = require('web.field_utils');
    var QWeb = core.qweb;
    var _t = core._t;

    var BudgetAnalysisReport = AbstractAction.extend({
        template: 'BudgetAnalysisReportTemplate',

        events: {
            'click .o_print_pdf': 'printPdf',
            'click .o_print_xlsx': 'printXlsx',
            'click .o_row': 'toggleCaret',
            'click .o_filter_date_custom_btn': 'toggleCustomDate',
            'click .o_apply_custom_date': 'onApplyCustomDate',
            'click .o_filter_date_item': 'onSelectDate',
            'click .o_apply_filter': 'applyFilter',
            'click .o_view_record': 'onClickViewRecord',
            'click .o_view_activity_record': 'onClickViewActivityRecord',
            'click .o_view_budget_plan': 'onClickViewBudgetPlan'
        },

        init: function(parent, action) {
            this._super(parent, action);
            this.currency = action.currency;
            this.wizard_id = action.context.wizard | null;
            this.formatFloat = field_utils.format.float;
            this.filterDate = 'this_year';
            this.filterDateFrom = null;
            this.filterDateTo = null;
            this.searchModelConfig.modelName = 'agriculture.budget.analysis.report'
        },
        
        start: async function() {
            this._super(...arguments);
            var self = this;
            this._rpc({
                model: 'agriculture.budget.analysis.report',
                method: 'create',
                args: [{filter_date: self.filterDate}]
            }).then(function(res) {
                self.wizard_id = res;
                self.loadData(true);
            });
        },

        loadData: function (initial_render) {
            var self = this;
            self._rpc({
                model: 'agriculture.budget.analysis.report',
                method: 'get_report_values',
                args: [[this.wizard_id]],
            }).then(function(result) {
                if (initial_render) {
                    self.$('.o_agri_report_header').html(QWeb.render('BudgetAnalysisReportHeader', {
                        filters: result['filters']
                    }));
                }
                return self._renderContent(result).then(function(){
                    self._calculateWidth();
                    var $tbodies = $('tbody.collapse');
                    $tbodies.on('shown.bs.collapse hidden.bs.collapse', self._calculateWidth);
                });
            });
        },

        _calculateWidth: function(e){
            $('.o_freeze:nth-child(1)').each(function(){
                $(this).next('.o_freeze').css('left', $(this).outerWidth());
            });
        },

        _renderContent: function(content){
            this.$('.o_agri_report_content').html(QWeb.render('BudgetAnalysisReportTable', {
                'formatFloat': this.formatFloat,
                'data': content['data'],
                'header': content['months']
            }));
            return Promise.resolve();
        },

        loadDatePicker: function(){
            var self = this;
            this.dateFromWidget = new monthYear.dateMonthYearWidget(this);
            this.dateToWidget = new monthYear.dateMonthYearWidget(this);

            this.dateFromWidget.appendTo('.o_custom_date_from').then(function(){
                self.dateFromWidget.setValue(moment.utc('01-01-2022', 'DD-MM-YYYY'));
            });
            this.dateToWidget.appendTo('.o_custom_date_to').then(function(){
                self.dateToWidget.setValue(moment.utc('31-12-2022', 'DD-MM-YYYY'));
            });
        },

        toggleCustomDate: function(event){
            event.preventDefault();
            var $target = $(event.currentTarget);
            var $customDate = $target.next('.collapse');
            $customDate.toggleClass('show');
            if ($customDate.hasClass('show') && !this.dateFromWidget && !this.dateToWidget){
                this.loadDatePicker();
            }
            event.stopPropagation();
        },

        onApplyCustomDate: function(event){
            event.preventDefault();
            if (!this.dateFromWidget || !this.dateToWidget){
                return;
            }
            var isValid = this.dateFromWidget.isValid() && this.dateToWidget.isValid();
            if (isValid){
                this.filterDateFrom = this.dateFromWidget.getValue();
                this.filterDateTo = this.dateToWidget.getValue();
                this.setActiveFilterDate('custom', 'Custom');
            }
        },

        onSelectDate: function(event){
            event.preventDefault();
            var $target = $(event.currentTarget);
            var value = $target.data('filter-date');
            var label = $target.html();
            this.setActiveFilterDate(value, label);

            var $customDate = $('.o_filter_date_custom_collapse');
            if ($customDate.hasClass('show')){
                $customDate.removeClass('show');
            }
        },

        setActiveFilterDate: function(value, label){
            var $parentId = $('.o_filter_date_btn');
            $parentId.data('filter-date', value);
            $parentId.html(label);
            this.filterDate = value;
        },

        printPdf: function(e) {
            e.preventDefault();
            return this.do_action('equip3_agri_operations.action_print_agriculture_budget_analysis_report', {
                additional_context: {
                    'active_id': this.wizard_id,
                    'active_ids': [this.wizard_id],
                    'active_model': 'agriculture.budget.analysis.report'
                }
            });
        },

        printXlsx: function() {
            var self = this;
            self._rpc({
                model: 'agriculture.budget.analysis.report',
                method: 'print_xlsx_report',
                args: [[self.wizard_id]],
            }).then(function(attachmentId) {
                if (attachmentId) {
                    return self.do_action({
                        'type': 'ir.actions.act_url',
                        'url': '/web/content/' + attachmentId + '?download=true',
                        'target': 'self'
                    });
                }
            });
        },

        toggleCaret(event){
            event.preventDefault();
            var $caret = $(event.currentTarget).find('span.fa');
            $caret.toggleClass('fa-caret-right');
            $caret.toggleClass('fa-caret-down');
        },

        applyFilter: function(event){
            event.preventDefault();
            var self = this;
            return this._rpc({
                model: 'agriculture.budget.analysis.report',
                method: 'write',
                args: [self.wizard_id, {
                    filter_date: this.filterDate,
                    custom_date_from: this.filterDateFrom,
                    custom_date_to: this.filterDateTo
                }],
            }).then(function(success) {
                if (success){
                    self.loadData(false);
                }
            });
        },

        onClickViewRecord: function(event){
            event.preventDefault();
            var $target = $(event.currentTarget);
            var resModel = $target.data('model');
            var resId = $target.data('res_id');
            var resName = $target.data('name');
            var action = {
                name: _t(resName),
                type: 'ir.actions.act_window',
                view_mode: 'form',
                res_model: resModel,
                res_id: resId,
                views: [[false, 'form']],
                target: 'current'
            };
            return this.do_action(action);
        },

        onClickViewActivityRecord: function(event){
            event.preventDefault();
            var $target = $(event.currentTarget);
            var divisionId = $target.data('division-id');
            var activityId = $target.data('activity-id');

            var self = this;
            return this._rpc({
                model: 'agriculture.budget.analysis.report',
                method: 'search_read',
                args: [[['id', '=', this.wizard_id]], ['date_from', 'date_to']],
            }).then(function(result) {
                var action = {
                    name: _t('Activity Record'),
                    type: 'ir.actions.act_window',
                    view_mode: 'list,form',
                    res_model: 'agriculture.daily.activity.record',
                    domain: [
                        ['division_id', '=', divisionId], 
                        ['activity_id', '=', activityId], 
                        ['state', '=', 'confirm'],
                        ['date_scheduled', '>=', result[0].date_from],
                        ['date_scheduled', '<=', result[0].date_to]
                    ],
                    views: [[false, 'list'], [false, 'form']],
                    target: 'current'
                };
                return self.do_action(action);
            });
        },

        onClickViewBudgetPlan: function(event){
            event.preventDefault();
            var $target = $(event.currentTarget);
            var divisionId = $target.data('division-id');
            var activityId = $target.data('activity-id');
            
            var self = this;
            return this._rpc({
                model: 'agriculture.budget.analysis.report',
                method: 'search_read',
                args: [[['id', '=', this.wizard_id]], ['date_from', 'date_to']],
            }).then(function(result) {
                var yearList = [];
                for (let i = parseInt(result[0].date_from.split('-')[0]); i < parseInt(result[0].date_to.split('-')[0]) + 1; i++){
                    yearList.push(String(i));
                }
                var action = {
                    name: _t('Budget Planning'),
                    type: 'ir.actions.act_window',
                    view_mode: 'list,form',
                    res_model: 'agriculture.budget.planning',
                    domain: [
                        ['division_id', '=', divisionId],
                        ['year', 'in', yearList],
                        ['month_ids.activity_id', 'in', [activityId]]
                    ],
                    views: [[false, 'list'], [false, 'form']],
                    target: 'current'
                };
                return self.do_action(action);
            });
        }

    });
    core.action_registry.add("agriculture_budget_analysis_report", BudgetAnalysisReport);
    return BudgetAnalysisReport;
});