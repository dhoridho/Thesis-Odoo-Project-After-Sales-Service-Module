odoo.define('equip3_manuf_it_inventory.ItListViewReport', function(require){
    'use strict';

    var ListController = require('web.ListController');
    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');
    var core = require('web.core');
    var datepicker = require('web.datepicker');
    var QWeb = core.qweb;


    var ListControllerReport = ListController.extend({
        buttons_template: 'ItListViewReport.buttons',
        events: _.extend({}, ListController.prototype.events, {
            'click .o_list_print_pdf': '_onPrintPdf',
            'click .o_list_print_xlsx': '_onPrintXlsx',
            'change .o_warehouse_select': '_onWarehouseChange'
        }),

        willStart: function(){
            var self = this;
            var warehouseProm = this._rpc({
                model: 'stock.warehouse',
                method: 'search_read',
//                domain: [['is_it_inventory_warehouse', '=', true]],
                fields: ['id', 'name', 'city']
            }).then(function(result){
                var warehouseIds = [{id: false, name: '', city: ''}];
                for (var i=0; i < result.length; i++){
                    warehouseIds.push(result[i]);
                }
                self.warehouseIds = warehouseIds;
            });
            var reportNameProm = this._rpc({
                model: this.modelName,
                method: 'get_report_name',
                args: []
            }).then(function(reportName){
                self.reportName = reportName;
            })
            return Promise.all([this._super.apply(this, arguments), warehouseProm, reportNameProm]);
        },

        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                self.$el.find('.o_cp_bottom_bottom').remove();

                var state = self.model.get(self.handle);
                var context = state.getContext();
//                var ItFilters = QWeb.render('ItFilters', {
//                });
                self.warehouseId = self._getActiveWarehouse(context.warehouse);

                var ItFilters = QWeb.render('ItFilters', {
                    warehouseId: self.warehouseId,
                    warehouseIds: self.warehouseIds
                });
                self.$el.find('.o_control_panel').append(ItFilters);

                self.dateFromWidget = new datepicker.DateWidget(self, {defaultDate: context.date_from});
                self.dateToWidget = new datepicker.DateWidget(self, {defaultDate: context.date_to});

                self.dateFromWidget.appendTo(self.$el.find('.o_date_filter_from')).then(function(){
                    self.dateFromWidget.$input.on('blur', function () {
                        var value = self.dateFromWidget.$input.val();
                        return self._onDateChange('date_from', value);
                    });
                });
                self.dateToWidget.appendTo(self.$el.find('.o_date_filter_to')).then(function(){
                    self.dateToWidget.$input.on('blur', function () {
                        var value = self.dateToWidget.$input.val();
                        return self._onDateChange('date_to', value);
                    });
                });
            });
        },

        _getActiveWarehouse: function(warehouseId){
            for (var i=0; i < this.warehouseIds.length; i++){
                if (this.warehouseIds[i].id === warehouseId){
                    return this.warehouseIds[i];
                }
            }
            return false;
        },
        _updateFilters: function(key, value){
            var state = this.model.get(this.handle);
            var context = state.getContext();
            context[key] = value;
            
            var action = this.controlPanelProps.action;
            return this.do_action({
                name: action.name,
                type: action.type,
                res_model: action.res_model,
                views: action._views,
                search_view_id: action.search_view_id,
                help: action.help,
                target: 'main',
                context: context,
            }, function (err) {
                return Promise.reject(err);
            });
        },

        _onDateChange: function(key, value){
            var date = false;
            if (value){
                date = moment(new Date(value)).format('YYYY-MM-DD');
//                date = moment(value).format('YYYY-MM-DD');
            }
            return this._updateFilters(key, date)
        },

        _onWarehouseChange: function(ev){
            var $target = $(ev.target);
            var warehouseId = parseInt($target.val());
            if (isNaN(warehouseId)){
                warehouseId = false;
            }
            this.warehouseId = this._getActiveWarehouse(warehouseId);
            return this._updateFilters('warehouse', warehouseId);
        },

        _onPrintPdf: function(e){
            e.preventDefault();
            var state = this.model.get(this.handle);
            var context = state.getContext();

            var selectedIds = this.getSelectedIds();
            if (selectedIds.length > 0){
                state.data = _.filter(state.data, function(d) {
                    return _.contains(selectedIds, d.res_id);
                })
                state.res_ids = selectedIds;
            }

            var filters = {
                warehouse: this.warehouseId,
                date_from: context.date_from,
                date_to: context.date_to
            };

            var self = this;
            return this._rpc({
                model: self.modelName,
                method: 'get_report_values',
                args: [state],
                kwargs: {with_header: true}
            }).then(function(result){
                var reportXmlId = 'equip3_manuf_it_inventory.it_inventory_list_report';
                var action = {
                    type: 'ir.actions.report',
                    display_name: self.reportName,
                    report_type: 'qweb-pdf',
                    report_name: reportXmlId,
                    report_file: reportXmlId,
                    data: {
                        lines: result['lines'],
                        header: result['header'],
                        report_name: self.reportName,
                        filters: filters
                    },
                    context: {
                        active_model: self.modelName
                    }
                };
                return self.do_action(action);
            });
        },

        _onPrintXlsx: async function(e){
            e.preventDefault();
            var state = this.model.get(this.handle);
            var context = state.getContext();

            var selectedIds = this.getSelectedIds();
            if (selectedIds.length > 0){
                state.data = _.filter(state.data, function(d) {
                    return _.contains(selectedIds, d.res_id);
                })
                state.res_ids = selectedIds;
            }

            var self = this;
            self._rpc({
                model: self.modelName,
                method: 'get_xlsx_report',
                args: [state],
                context: context
            }).then(function(attachmentId) {
                if (attachmentId) {
                    return self.do_action({
                        'type': 'ir.actions.act_url',
                        'url': '/web/content/' + attachmentId + '?download=true',
                        'target': 'self'
                    });
                }
            });
        }
    });

    var ListViewReport = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: ListControllerReport
        }),
    });

    viewRegistry.add('it_list_view_report', ListViewReport);

    return {
        ListControllerReport: ListControllerReport,
        ListViewReport: ListViewReport
    };
});