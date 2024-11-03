odoo.define('equip3_manuf_other_operations.MrpMpsDetailOld', function (require) {
    "use strict";

    var FormView = require('web.FormView');
    var FormRenderer = require('web.FormRenderer');
    var viewRegistry = require('web.view_registry');
    var session = require('web.session');

    var MPSFormRenderer = FormRenderer.extend({
        jsLibs: [
            '/equip3_manuf_other_operations/static/lib/js/Chart.bundle.min.js',
            '/equip3_manuf_other_operations/static/lib/js/chartjs-plugin-datalabels.js'
        ],
        cssLibs: [
            '/equip3_manuf_other_operations/static/lib/css/Chart.min.css'
        ],

        init: function (parent, state, params) {
            this._super.apply(this, arguments);
            this.periods = [];
        },

        willStart: function () {
            var self = this;
            var def_periods = this._rpc({
                model: 'res.company',
                method: 'date_range_to_str',
                args: [[session.company_id]],
                context: this.context
            })
            .then(function (periods) {
                self.periods = periods;
            });
            return Promise.all([this._super.apply(this, arguments), def_periods]);
        },

        _renderView: function(){
            var self = this;
            this._super.apply(this, arguments).then(function(){

                var forecast = JSON.parse(self.state.data.forecasted_data);

                var dict = {
                    minQty: [],
                    maxQty: [],
                    onHandQty: []
                };
                for (var i = 0; i < forecast.length; i++){
                    dict.minQty.push(forecast[i]['low_stock']);
                    dict.maxQty.push(forecast[i]['max_stock']);
                    dict.onHandQty.push(forecast[i]['on_hand_qty']);
                }

                var suggestedMin = Math.min(Math.min.apply(Math, dict.minQty), Math.min.apply(Math, dict.maxQty), Math.min.apply(Math, dict.onHandQty));
                var suggestedMax = Math.max(Math.max.apply(Math, dict.minQty), Math.max.apply(Math, dict.maxQty), Math.max.apply(Math, dict.onHandQty));

                const data = {
                    labels: self.periods,
                    datasets: [
                        {
                            label: 'Min',
                            data: dict.minQty,
                            borderColor: '#FF6384',
                            backgroundColor: 'transparent',
                            yAxisID: 'qty'
                        },
                        {
                            label: 'Max',
                            data: dict.maxQty,
                            borderColor: '#36A2EB',
                            backgroundColor: 'transparent',
                            yAxisID: 'qty'
                        },
                        {
                            label: 'On Hand',
                            data: dict.onHandQty,
                            borderColor: '#008000',
                            backgroundColor: 'transparent',
                            yAxisID: 'qty'
                        }
                    ]
                };

                self.mpsChart = new Chart(self.$el.find('#o_mps_line_chart'), {
                    type: 'line',
                    data: data,
                    options: {
                        // responsive: true,
                        maintainAspectRatio: false,
                        interaction: {
                            mode: 'index',
                            intersect: false,
                        },
                        stacked: false,
                        plugins: {
                            title: {
                                display: true,
                                text: 'Chart.js Line Chart - Multi Axis'
                            }
                        },
                        elements: {
                            line: {
                                tension: 0 // disables bezier curves
                            }
                        },
                        legend: {
                            position: 'right'
                        },
                        scales: {
                            yAxes: [
                                {
                                    type: 'linear',
                                    display: true,
                                    id: "qty",
                                    gridLines: {
                                        display: true
                                    },
                                    labels: {
                                        show: true,
                                    },
                                    ticks: {
                                        suggestedMin: suggestedMin,
                                        suggestedMax: suggestedMax,
                                    }
                                }
                            ],
                        }
                    }
                });
            });
        }
    });
    
    var MPSFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Renderer: MPSFormRenderer
        }),
    });
    
    viewRegistry.add('mps_view_details_form_view', MPSFormView);
    
    return {
        MPSFormView: MPSFormView,
        MPSFormRenderer: MPSFormRenderer
    };
});
    