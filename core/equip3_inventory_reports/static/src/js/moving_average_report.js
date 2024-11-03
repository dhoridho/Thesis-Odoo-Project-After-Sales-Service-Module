odoo.define('equip3_inventory_reports.MovingAverageReport', function(require){
    "use strict";

    var PivotController = require('web.PivotController');
    var PivotView = require('web.PivotView');
    var viewRegistry = require('web.view_registry');

    var core = require('web.core');
    var Qweb = core.qweb;

    var MovingPivotController = PivotController.extend({
        events: _.extend({}, PivotController.prototype.events, {
            'change .o_report_filter': '_onChangeReportFilter',
        }),

        willStart: function(){
            var self = this;
            var def_warehouse = this._rpc({
                method: 'search_read',
                model: 'stock.warehouse',
                fields: ['id', 'display_name']
            }).then(function(warehouses){
                self.warehouseIds = warehouses;
            });
            return Promise.all([this._super.apply(this, arguments), def_warehouse]);
        },

        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                self.$el.addClass('o_moving_average_report');

                var $controlPanel = self.$el.find('.o_control_panel');
                if ($controlPanel.length){
                    self._renderReportFilters($controlPanel);
                }
            });
        },


        _renderReportFilters: function($container){
            var today = new Date();
            var from_date = new Date(today);
            from_date.setDate(today.getDate() - 30);

            var to_date = new Date(today);
            to_date.setDate(today.getDate() - 1);

            var formattedfrom_date = from_date.toISOString().split('T')[0];
            var formattedto_date = to_date.toISOString().split('T')[0];

            var $content = Qweb.render('MovingAverageReportFilter', {
                warehouseIds: this.warehouseIds,
                warehouseId: this.warehouseId,
                defaultDateFrom: formattedfrom_date,
                defaultDateTo: formattedto_date
            });
            $container.append($content);
        },

        _onChangeReportFilter: function(ev){
            var warehouseId = parseInt(this.$el.find('.o_report_filter.o_warehouse').val());
            var dateFrom = this.$el.find('.o_report_filter.o_date_from').val();
            var dateTo = this.$el.find('.o_report_filter.o_date_to').val();

            var domain = [];
            if (warehouseId > 0){
                domain.push(['warehouse_id', '=', warehouseId]);
            }

            if (dateFrom){
                domain.push(['date', '>=', dateFrom]);
            }

            if (dateTo){
                domain.push(['date', '<=', dateTo]);
            }
            this.reload({domain: domain});
        },
    });

    var MovingPivotView = PivotView.extend({
        config: _.extend({}, PivotView.prototype.config, {
            Controller: MovingPivotController,
        }),
    });

    viewRegistry.add('moving_average_report_pivot', MovingPivotView);

    return {
        MovingPivotController: MovingPivotController,
        MovingPivotView: MovingPivotView,
    };
});