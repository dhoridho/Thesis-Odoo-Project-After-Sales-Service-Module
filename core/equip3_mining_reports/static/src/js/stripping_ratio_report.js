odoo.define('equip3_mining_reports.stripping_ratio_report', function (require) {
    'use strict';

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var yearWidget = require('equip3_date_year.date_year');
    var relationalField = require('web.relational_fields');
    var field_utils = require('web.field_utils');
    var QWeb = core.qweb;
    var _t = core._t;

    var StrippingRatioReport = AbstractAction.extend({
        template: 'StrippingRatioReportTemplate',

        events: {
            'click .o_print_pdf': 'printPdf',
            'click .o_print_xlsx': 'printXlsx',
            'click .o_row': 'toggleCaret',
            'click .o_filter_site_item': 'onSelectSite',
            'click .o_apply_filter': 'applyFilter',
            'click .o_view_record': 'onClickViewRecord'
        },

        init: function(parent, action) {
            this._super(parent, action);
            this.currency = action.currency;
            this.wizard_id = action.context.wizard | null;
            this.formatFloat = field_utils.format.float;
            this.filterSite = 'all';
            this.searchModelConfig.modelName = 'mining.stripping.ratio.report'
        },
        
        start: async function() {
            await this._super(...arguments);
            var self = this;
            this._rpc({
                model: 'mining.stripping.ratio.report',
                method: 'create',
                args: [{'filter_site': self.filterSite}]
            }).then(function(res) {
                self.wizard_id = res;
                self.loadData(true);
            });
        },

        loadData: function (initial_render) {
            var self = this;
            self._rpc({
                model: 'mining.stripping.ratio.report',
                method: 'get_report_values',
                args: [[this.wizard_id]],
            }).then(function(result) {
                if (initial_render) {
                    var $header = QWeb.render('StrippingRatioReportHeader', {
                        filters: result['filters']
                    })
                    self.$('.o_mining_stripping_report_header').html($header);
                }
                if (!result['data'].length){
                    self.$('.o_mining_stripping_report_content').html(QWeb.render('StrippingRatioNoContentHelper'));
                } else {
                    self.$('.o_mining_stripping_report_content').html(QWeb.render('StrippingRatioReportTable', {
                        'formatFloat': self.formatFloat,
                        'data': result['data'],
                        'digits': result['digits'],
                        'filters': result['filters']
                    }));
                }
                return result;
            }).then(function(result) {
                var filterYear = result['filters']['filter_year'];
                
                if (!self.yearWidget){
                    self.yearWidget = new yearWidget.dateYearWidget(self);
                    self.yearWidget.appendTo('.o_year_filter_widget').then(function(){
                        self.yearWidget.setValue(moment.utc(filterYear, 'YYYY-MM-DD'));
                    });
                } else {
                    self.yearWidget.setValue(moment.utc(filterYear, 'YYYY-MM-DD'));
                }
            });
        },

        onSelectSite: function(event){
            event.preventDefault();
            var $target = $(event.currentTarget);
            var value = $target.data('filter-site');
            var label = $target.html();
            this.setActiveFilterSite(value, label);
        },

        setActiveFilterSite: function(value, label){
            var $parentId = $('.o_filter_site_btn');
            $parentId.data('filter-site', value);
            $parentId.html(label);
            this.filterSite = value;
        },

        printPdf: function(e) {
            e.preventDefault();
            return this.do_action('equip3_mining_reports.action_print_mining_stripping_ratio_report', {
                additional_context: {
                    'active_id': this.wizard_id,
                    'active_ids': [this.wizard_id],
                    'active_model': 'mining.stripping.ratio.report'
                }
            });
        },

        printXlsx: function() {
            var self = this;
            self._rpc({
                model: 'mining.stripping.ratio.report',
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
            var $target =  $(event.currentTarget);
            var $caret = $target.find('span.fa');
            $caret.toggleClass('fa-caret-right');
            $caret.toggleClass('fa-caret-down');
        },

        applyFilter: function(event){
            event.preventDefault();
            var $checkedPeriod = $('input[name="filter-period"]:checked');
            var values = {
                filter_site: String(this.filterSite),
                filter_year: this.yearWidget.getValue(),
                filter_period: $checkedPeriod.val()
            };
            var self = this;
            return this._rpc({
                model: 'mining.stripping.ratio.report',
                method: 'write',
                args: [self.wizard_id, values],
            }).then(function(success) {
                if (success){
                    self.loadData(false);
                }
            });
        },

        onClickViewRecord: function(event){
            event.preventDefault();
            var $target = $(event.currentTarget);
            var resDescription = $target.data('desc');
            var resModel = $target.data('model');
            var resId = $target.data('res_id');
            var action = {
                name: _t(resDescription),
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
    core.action_registry.add("mining_stripping_ratio_report", StrippingRatioReport);
    return StrippingRatioReport;
});