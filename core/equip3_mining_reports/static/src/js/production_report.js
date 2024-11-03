odoo.define('equip3_mining_reports.production_report', function (require) {
    'use strict';

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var monthYear = require('equip3_date_year.month_year');
    var field_utils = require('web.field_utils');
    var QWeb = core.qweb;
    var _t = core._t;

    var ProductionReport = AbstractAction.extend({
        template: 'ProductionReportTemplate',

        events: {
            'click .o_print_pdf': 'printPdf',
            'click .o_print_xlsx': 'printXlsx',
            'click .o_row': 'toggleCaret',
            'click .o_filter_date_custom_btn': 'toggleCustomDate',
            'click .o_apply_custom_date': 'onApplyCustomDate',
            'click .o_filter_date_item': 'onSelectDate',
            'click .o_apply_filter': 'applyFilter',
            'click .o_view_record': 'onClickViewRecord'
        },

        init: function(parent, action) {
            this._super(parent, action);
            this.currency = action.currency;
            this.wizard_id = action.context.wizard | null;
            this.formatFloat = field_utils.format.float;
            this.filterDate = 'this_year';
            this.filterDateFrom = null;
            this.filterDateTo = null;
            this.searchModelConfig.modelName = 'mining.production.report'
        },
        
        start: async function() {
            this._super(...arguments);
            var self = this;
            this._rpc({
                model: 'mining.production.report',
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
                model: 'mining.production.report',
                method: 'get_report_values',
                args: [[this.wizard_id]],
            }).then(function(result) {
                if (initial_render) {
                    self.$('.o_mining_production_report_header').html(QWeb.render('ProductionReportHeader', {
                        filters: result['filters']
                    }));
                }
                self.$('.o_mining_production_report_content').html(QWeb.render('ProductionReportTable', {
                    'formatFloat': self.formatFloat,
                    'data': result['data'],
                    'month': result['months']
                }));
            });
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
            return this.do_action('equip3_mining_reports.action_print_mining_production_report', {
                additional_context: {
                    'active_id': this.wizard_id,
                    'active_ids': [this.wizard_id],
                    'active_model': 'mining.production.report'
                }
            });
        },

        printXlsx: function() {
            var self = this;
            self._rpc({
                model: 'mining.production.report',
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
            console.log(this.filterDateFrom);
            console.log(this.filterDateTo)
            return this._rpc({
                model: 'mining.production.report',
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
        }

    });
    core.action_registry.add("mining_production_report", ProductionReport);
    return ProductionReport;
});