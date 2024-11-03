odoo.define('setu_cash_flow_forecasting.setu_kanban_chart', function (require) {
    "use strict";

    require('web.dom_ready');

    var registry = require('web.field_registry');
    var AbstractField = require('web.AbstractField');
    var core = require('web.core');
    var basic_fields = require('web.basic_fields');

    var QWeb = core.qweb;

    basic_fields.JournalDashboardGraph.include({
            _renderInDOM: function () {

                 if(this.graph_type === 'gauge'){
                        var config, cssClass;
                         config = this._getGaugeChartConfig();
                         cssClass = 'o_graph_barchart';
                         this.$canvas = $('<canvas/>');
                        this.$el.addClass(cssClass);
                        this.$el.empty();
                        this.$el.append(this.$canvas);
                        var context = this.$canvas[0].getContext('2d');
                        this.chart = new Chart(context, config);
                  }
                  else{
                    this._super.apply(this, arguments);
                  }
            },
            _getGaugeChartConfig: function () {
            var data = [];
            var labels = [];
            var backgroundColor = [];
            if(this.data[0].title === "dummy"){
                this.data[0].values.forEach(function (pt) {
                    data.push(pt.value);
                    labels.push(pt.label);
                    var color = pt.type === 'past' ? '#ccbdc8' : (pt.type === 'future' ? '#a5d8d7' : '#ebebeb');
                    backgroundColor.push(color);
                });
                return {
                    type: 'doughnut',
                    data: {
                        labels: ["No Forecast Calculated"],
                        datasets: [{
                            data: data,
                            backgroundColor: backgroundColor,
                        }],
                    },
                    options: {
                         title: {
                                display: true,
                                text: 'No Forecast Calculated'
                            },
                            legend: {
                                display: false
                            },
                        circumference: Math.PI,
                        rotation: -Math.PI,
                        tooltips: {
                            enabled: false
                        },
                    },
                }
            }
            else if(this.data[0].title === "zero-dummy"){
                this.data[0].values.forEach(function (pt) {
                    data.push(pt.value);
                    labels.push(pt.label);
                    var color = pt.type === 'past' ? '#ccbdc8' : (pt.type === 'future' ? '#a5d8d7' : '#ebebeb');
                    backgroundColor.push(color);
                });
                return {
                    type: 'doughnut',
                    data: {
                        labels: ["All Forested Values Are Zero"],
                        datasets: [{
                            data: data,
                            backgroundColor: backgroundColor,
                        }],
                    },
                    options: {
                         title: {
                                display: true,
                                text: 'All Forested Values Are Zero'
                            },
                            legend: {
                                display: false
                            },
                        circumference: Math.PI,
                        rotation: -Math.PI,
                        tooltips: {
                            enabled: false
                        },
                    },
                }
            }
            else{
                this.data[0].values.forEach(function (pt) {
                    data.push(pt.value);
                    labels.push(pt.label);
                    var color = pt.type === 'past' ? '#ccbdc8' : (pt.type === 'future' ? '#a5d8d7' : '#ebebeb');
                    backgroundColor.push(color);
                });
                return {
                    type: 'doughnut',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: data,
                            backgroundColor: backgroundColor,
                        }],
                    },
                    options: {
                        circumference: Math.PI,
                        rotation: -Math.PI,
                        legend: {
                            display: false
                        },
                    },
                }
            }
        },
        });

//    AbstractField.include({
//
//         init: function (parent, state, params) {
//            debugger
//            this._super.apply(this, arguments);
//        },
//    });
//    registry.add('SetuDashboardGraph', SetuDashboardGraph);

//    return {
//        SetuDashboardGraph: SetuDashboardGraph
//    };

});
