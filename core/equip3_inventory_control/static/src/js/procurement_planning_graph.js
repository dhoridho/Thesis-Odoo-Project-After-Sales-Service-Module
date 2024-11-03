odoo.define('equip3_inventory_control.ProcurementPlanningGraph', function(require){
    "use strict";
   
    const AbstractAction = require('web.AbstractAction');
    const core = require('web.core');

    const ProcurementPlanningGraphAction = AbstractAction.extend({
        template: 'ProcurementPlanningGraph',

        events: {
            'click .o_action_apply': '_onApplyButtonClick',
            'click .o_action_reset': '_onResetButtonClick'
        },

        init: function (parent, action, options) {
            this._super.apply(this, arguments);
            var context = action.context || {};

            this.stockData = context.line_data || {};

            this.productId = this.stockData.product_id || false;
            this.warehouseId = this.stockData.warehouse_id || false;

            this.defaultForecastMonth = context.default_stock_forecast_month || 3;

            this.startingPoint = 0;
            this.stockForecastMonth = this.defaultForecastMonth;
        },

        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                self._renderChart();
            });
        },

        _getData: function(){
            var self = this;
            var rulesProm = this._rpc({
                method: 'search_read',
                model: 'stock.warehouse.orderpoint',
                domain: [['product_id', '=', this.productId], ['warehouse_id', '=', this.warehouseId]],
                fields: ['product_min_qty', 'product_max_qty']
            });

            var movesProm = this._rpc({
                method: 'search_read',
                model: 'stock.move',
                domain: [
                    ['product_id', '=', this.productId], 
                    ['warehouse_id', '=', this.warehouseId],
                    ['state', '=', 'done'],
                    ['picking_id.picking_type_code', '=', 'outgoing']
                ],
                fields: ['quantity_done', 'date']
            });

            return Promise.all([rulesProm, movesProm]).then(function(results){
                let rules = results[0];
                let moves = results[1];

                let minQty = 0;
                let maxQty = 0;
                _.each(rules, function(rule){
                    minQty += rule.product_min_qty;
                    maxQty += rule.product_max_qty;
                });

                if (rules.length){
                    minQty /= rules.length;
                    maxQty /= rules.length;
                }

                let date = moment();
                let format = 'YYYY-MM-DD HH:mm:ss';

                let runRates = [];
                for (let i=0; i < self.stockForecastMonth; i++){
                    date.subtract(1, 'months');
                    let dateMoves = _.map(
                        _.filter(moves, move => moment(move.date, format) > date.startOf('month') && 
                        moment(move.date, format) <= date.endOf('month')), 
                    m => m.quantity_done);
                    runRates.push(dateMoves.reduce((a, b) => a + b, 0));
                }
                runRates.reverse();

                return {
                    minQty: minQty,
                    maxQty: maxQty,
                    runRates: runRates
                }
            });
        },

        _getMonths: function(){
            var now = moment();
            var months = [];
            for (let i=0; i < 12; i++){
                months.push(now.subtract(1, 'months').format('MMM YY').toUpperCase());
            }
            months.reverse();
            return months;
        },

        _getFutureMonths: function(){
            var months = [];
            for (let i=0; i < this.stockForecastMonth + 1; i++){
                months.push(moment().add(i, 'months').format('MMM YY').toUpperCase());
            }
            return months;
        },

        _renderChart: async function(){
            const {minQty, maxQty, runRates} = await this._getData();
            const months = this._getMonths().concat(this._getFutureMonths());

            const minColor = 'green';
            const maxColor = 'red';
            const stockColor = 'blue';

            var stockPointColor = [stockColor];
            var stock = [{x: 0, y: this.startingPoint}];
            var closing = this.stockData.closing;

            for (let i=1; i <= 12; i++){
                var stockQty = closing[i - 1] || 0.0;
                stock.push({x: i, y: stockQty.toFixed(2)});
                stockPointColor.push(stockQty < minQty ? maxColor : stockColor);
            }

            var availableQty = this.stockData.available_qty;
            var sales = this.stockData.sales;
            var yearRunRate = sales / 365;
            var monthRunRate = sales / 12;
            var dayLeft = this.stockData.day_left;
            var currentPoint = availableQty - (yearRunRate * dayLeft);
            var nextPoint = currentPoint;
            for (let i=13; i < 13 + this.stockForecastMonth + 1; i++){
                stock.push({x: i, y: nextPoint.toFixed(2)});
                stockPointColor.push(nextPoint < minQty ? maxColor : stockColor);
                if (nextPoint <= minQty){
                    nextPoint = maxQty;
                    stock.push({x: i, y: nextPoint.toFixed(2)});
                    stockPointColor.push(stockColor);
                }
                nextPoint = nextPoint - monthRunRate;
            }

            var minimumY = Math.min.apply(Math, _.map(stock, s => s.y).concat(minQty));
            var maximumY = Math.max.apply(Math, _.map(stock, s => s.y).concat(maxQty));
            
            var data = {
                labels: _.map(stock, s => s.x === 0 ? '' : months[s.x - 1]),
                datasets: [
                    {
                        label: 'Stock',
                        borderColor: stockColor,
                        borderWidth: 2,
                        backgroundColor: 'transparent',
                        pointBackgroundColor: stockPointColor,
                        pointBorderColor: stockPointColor,
                        data: stock,
                        showLine: true,
                    },
                    {
                        label: 'Min',
                        borderColor: minColor,
                        borderWidth: 2,
                        backgroundColor: 'transparent',
                        pointBackgroundColor: minColor,
                        pointBorderColor: minColor,
                        data: _.map(stock, function(s){ return {x: s.x, y: minQty.toFixed(2)}; }),
                        showLine: true,
                    },
                    {
                        label: 'Max',
                        borderColor: maxColor,
                        borderWidth: 2,
                        backgroundColor: 'transparent',
                        pointBackgroundColor: maxColor,
                        pointBorderColor: maxColor,
                        data: _.map(stock, function(s){ return {x: s.x, y: maxQty.toFixed(2)}; }),
                        showLine: true,
                    }
                ]
            };
              
            var options = {
                maintainAspectRatio: false,
                scales: {
                    yAxes: [{
                        gridLines: {
                            display: true,
                        },
                        ticks: {
                            min: minimumY < 0 ? (minimumY - 10) : 0,
                            max: maximumY + 10
                        }
                    }],
                    xAxes: [{
                        gridLines: {
                            display: true,
                            offsetGridLines: true
                        },
                        ticks: {
                            maxTicksLimit: 14 + this.stockForecastMonth,
                            stepSize: 1,
                            userCallback: function(label, index, labels){
                                if (label === 0){
                                    return '';
                                }
                                return months[label - 1];
                            }
                        }
                    }]
                },
                elements: {
                    line: {
                        tension: .1, // bezier curves
                    }
                },
                plugins: {
                    datalabels: {
                        display: false,
                    },
                },
                tooltips: {
                    callbacks: {
                        label: function(tooltipItem, data) {
                            return '(' + data.labels[tooltipItem.index] + ', ' + tooltipItem.yLabel + ')';
                        }
                    }
                }
            };

            if (this.chart){
                this.chart.destroy();
            }

            this.chart = new Chart(this.$el.find('#o_procurement_planning_chart'), {
                type: 'scatter',
                data: data,
                options: options
            });
        },

        _onApplyButtonClick: function(ev){
            this.stockForecastMonth = parseInt(this.$el.find('.o_stock_forecast_month').val());
            this._renderChart();
        },

        _onResetButtonClick: function(ev){
            this.$el.find('.o_stock_forecast_month').val(this.defaultForecastMonth);
            this._onApplyButtonClick();
        }
    });

    core.action_registry.add('procurement_planning_graph', ProcurementPlanningGraphAction);
    return ProcurementPlanningGraphAction;
});