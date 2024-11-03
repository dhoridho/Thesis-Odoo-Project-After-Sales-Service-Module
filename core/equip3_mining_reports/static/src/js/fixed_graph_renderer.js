odoo.define('equip3_mining_reports.FixedGraphRenderer', function(require){
    "use strict";

    const graphRenderer = require('web.GraphRenderer');
    const graphView = require('web.GraphView');
    const viewRegistry = require('web.view_registry');

    function hexToRGBA(hex, opacity) {
        var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        var rgb = result.slice(1, 4).map(function (n) {
            return parseInt(n, 16);
        }).join(',');
        return 'rgba(' + rgb + ',' + opacity + ')';
    }

    var COLORS = ["#1f77b4", "#ff7f0e", "#aec7e8", "#ffbb78", "#2ca02c", "#98df8a", "#d62728",
    "#ff9896", "#9467bd", "#c5b0d5", "#8c564b", "#c49c94", "#e377c2", "#f7b6d2",
    "#7f7f7f", "#c7c7c7", "#bcbd22", "#dbdb8d", "#17becf", "#9edae5"];

    const fixedGraphRenderer = graphRenderer.extend({
        _renderLineChart: function (dataPoints) {
            var self = this;
            var data = this._prepareData(dataPoints);
            var labels = [];
            _.each(data.labels, function(label){
                labels.push(label[0]); 
            });

            this._rpc({
                method: 'search_read',
                model: 'mining.production.record',
                domain: [['name', 'in', labels]],
                fields: ['gross_total', 'nett_total']
            }).then(function(result){

                var grossData = JSON.parse(JSON.stringify(data.datasets[0]));
                grossData.label = 'Gross';
                
                _.each(result, function(r, index){
                    grossData.data[index] = r.gross_total;
                })
                data.datasets.push(grossData);

                data.datasets.forEach(function (dataset, index) {
                    if (self.state.processedGroupBy.length <= 1 && self.state.origins.length > 1) {
                        if (dataset.originIndex === 0) {
                            dataset.fill = 'origin';
                            dataset.backgroundColor = hexToRGBA(COLORS[0], 0.4);
                            dataset.borderColor = hexToRGBA(COLORS[0], 1);
                        } else if (dataset.originIndex === 1) {
                            dataset.borderColor = hexToRGBA(COLORS[1], 1);
                        } else {
                            dataset.borderColor = self._getColor(index);
                        }
                    } else {
                        dataset.borderColor = self._getColor(index);
                    }
                    if (data.labels.length === 1) {
                        // shift of the real value to right. This is done to center the points in the chart
                        // See data.labels below in Chart parameters
                        dataset.data.unshift(undefined);
                    }
                    dataset.pointBackgroundColor = dataset.borderColor;
                    dataset.pointBorderColor = 'rgba(0,0,0,0.2)';
                });

                if (data.datasets.length === 1) {
                    const dataset = data.datasets[0];
                    dataset.fill = 'origin';
                    dataset.backgroundColor = hexToRGBA(COLORS[0], 0.4);
                }

                // center the points in the chart (without that code they are put on the left and the graph seems empty)
                data.labels = data.labels.length > 1 ?
                    data.labels :
                    Array.prototype.concat.apply([], [[['']], data.labels, [['']]]);

                // prepare options
                var options = self._prepareOptions(data.datasets.length);
                options.scales.yAxes[0].scaleLabel.labelString = 'Nett & Gross';

                // create chart
                var ctx = document.getElementById(self.chartId);
                self.chart = new Chart(ctx, {
                    type: 'line',
                    data: data,
                    options: options,
                });

            });
        },

        _customTooltip: function (tooltipModel) {
            this._super.apply(this, arguments);
            this.$tooltip.find('.o_measure').html('Nett & Gross');
        }
    });

    const fixedGraphView = graphView.extend({
        config: _.extend({}, graphView.prototype.config, {
            Renderer: fixedGraphRenderer
        }),
    });

    viewRegistry.add('fixed_graph_renderer', fixedGraphView);

    return {
        fixedGraphRenderer: fixedGraphRenderer,
        fixedGraphView: fixedGraphView
    }
});