odoo.define('equip3_construction_operation.KsGraphView', function (require) {
    "use strict";
    var AbstractField = require('web.AbstractField');
    var ks_field_registry = require('web.field_registry');
    var ajax = require('web.ajax');

    var KsGraphView = AbstractField.extend({
        jsLibs: [
           '/web/static/lib/Chart/Chart.js',
        ],
        resetOnAnyFieldChange: true,
        template: 'mini_graph_template',
        xmlDependencies: [
            '/equip3_construction_operation/static/src/xml/ks_graph_template.xml',
        ],
        init: function (parent, value) {
            var self = this;
            this._super.apply(this,arguments);
        },

        renderElement: function () {
            this._super();
            this.render_Linechart();
        },

        render_Linechart:function(){
            this.$el.find('.ks_chart_container').empty()
            var canvas = '<canvas id="canvas"></canvas>'
            this.$el.find('.ks_chart_container').append($(canvas))

            var ctx = this.$el.find('#canvas').get(0).getContext('2d');
            var chart_data = JSON.parse(this.recordData.ks_chart_data)
            
            var myChart = new Chart(ctx, {
                type: 'line',
                data: chart_data,
                options: {
                    maintainAspectRatio: false,
                    responsive: true,
                    legend: {
                        display: true,
                        position: 'bottom',
                        labels: {
                            fontSize: 8
                        }
                    },
                    scales: {
                        xAxes: [{
                            display: true,
                            gridLines: {
                                display: true
                                }
                        }],
                        yAxes: [{
                            display: true,
                            gridLines: {
                                display: true
                                }
                        }]
                    },
                    elements: {
                        point: {
                            radius: 2
                        }
                    },
                    plugins: {
                        tooltip: {
                            enabled: false
                        }
                    }
                }
            });
            this.ks_chart_color(myChart, 'line')
        },

        ks_chart_color: function(ksMyChart, ksChartType){
            var chartColors = [];
            var datasets = ksMyChart.config.data.datasets;
            var setsCount = datasets.length;
            var color_set = ['#F04F65', '#f69032', '#fdc233', '#53cfce', '#36a2ec', '#8a79fd', '#b1b5be', '#1c425c', '#8c2620', '#71ecef', '#0b4295', '#f2e6ce', '#1379e7']
            for (var i = 0, counter = 0; i < setsCount; i++, counter++) {
                if (counter >= color_set.length) counter = 0; // reset back to the beginning
                chartColors.push(color_set[counter]);
            }
            for (var i = 0; i < datasets.length; i++) {
                switch (ksChartType) {
                    case "line":
                        datasets[i].borderColor = chartColors[i];
                        datasets[i].backgroundColor = "rgba(255,255,255,0)";
                        break;
                    case "bar":
                        datasets[i].backgroundColor = chartColors[i];
                        datasets[i].borderColor = "rgba(255,255,255,0)";
                        break;
                }
            }
            ksMyChart.update();
        },
    });

    ks_field_registry.add('ks_mini_graph', KsGraphView);

    return KsGraphView;

});