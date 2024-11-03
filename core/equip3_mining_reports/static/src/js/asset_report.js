odoo.define('equip3_mining_reports.asset_report', function (require) {
    'use strict';

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var field_utils = require('web.field_utils');
    var QWeb = core.qweb;
    var _t = core._t;

    var AssetReport = AbstractAction.extend({
        template: 'AssetReportTemplate',

        events: {
            'click .o_print_pdf': 'printPdf',
            'click .o_print_xlsx': 'printXlsx',
            'click .o_row': 'toggleCaret',
            'click .o_filter_pit_item': 'onSelectPit',
            'click .o_apply_filter': 'applyFilter',
            'click .o_view_record': 'onClickViewRecord'
        },

        init: function(parent, action) {
            this._super(parent, action);
            this.currency = action.currency;
            this.wizard_id = action.context.wizard | null;
            this.formatFloat = field_utils.format.float;
            this.filterPit = 'all';
            this.searchModelConfig.modelName = 'mining.asset.report'
        },
        
        start: async function() {
            await this._super(...arguments);
            var self = this;
            this._rpc({
                model: 'mining.asset.report',
                method: 'create',
                args: [{'filter_pit': self.filterPit}]
            }).then(function(res) {
                self.wizard_id = res;
                self.loadData(true);
            });
        },

        loadData: function (initial_render) {
            var self = this;
            self._rpc({
                model: 'mining.asset.report',
                method: 'get_report_values',
                args: [[this.wizard_id]],
            }).then(function(result) {
                if (initial_render) {
                    self.$('.o_mining_asset_report_header').html(QWeb.render('AssetReportHeader', {
                        filters: result['filters']
                    }));
                }
                if (!result['data']['children'].length){
                    self.$('.o_mining_asset_report_content').html(QWeb.render('AssetNoContentHelper'));
                } else {
                    self.$('.o_mining_asset_report_content').html(QWeb.render('AssetReportTable', {
                        'formatFloat': self.formatFloat,
                        'data': result['data']
                    }));
                }
            });
        },

        onSelectPit: function(event){
            event.preventDefault();
            var $target = $(event.currentTarget);
            var value = $target.data('filter-pit');
            var label = $target.html();
            this.setActiveFilterPit(value, label);
        },

        setActiveFilterPit: function(value, label){
            var $parentId = $('.o_filter_pit_btn');
            $parentId.data('filter-pit', value);
            $parentId.html(label);
            this.filterPit = value;
        },

        printPdf: function(e) {
            e.preventDefault();
            return this.do_action('equip3_mining_reports.action_print_mining_asset_report', {
                additional_context: {
                    'active_id': this.wizard_id,
                    'active_ids': [this.wizard_id],
                    'active_model': 'mining.asset.report'
                }
            });
        },

        printXlsx: function() {
            var self = this;
            self._rpc({
                model: 'mining.asset.report',
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
            var self = this;
            return this._rpc({
                model: 'mining.asset.report',
                method: 'write',
                args: [self.wizard_id, {filter_pit: String(this.filterPit)}],
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
    core.action_registry.add("mining_asset_report", AssetReport);
    return AssetReport;
});