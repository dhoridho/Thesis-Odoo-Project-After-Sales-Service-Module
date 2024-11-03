odoo.define('equip3_mining_reports.FixedGraphView', function(require){
    "use strict";

    const graphRenderer = require('web.GraphRenderer');
    const graphModel = require('web.GraphModel');
    const graphController = require('web.GraphController');
    const graphView = require('web.GraphView');
    const viewRegistry = require('web.view_registry');

    const fixedGraphModel = graphModel.extend({
        _loadGraph: function () {
            var self = this;
            this.chart.dataPoints = [];
            var groupBy = this.chart.processedGroupBy;
            var fields = _.map(groupBy, function (groupBy) {
                return groupBy.split(':')[0];
            });

            fields = fields.concat(['gross_total', 'nett_total', 'tare_total']);
    
            if (this.chart.measure !== '__count__') {
                if (this.fields[this.chart.measure].type === 'many2one') {
                    fields = fields.concat(this.chart.measure + ":count_distinct");
                }
                else {
                    fields = fields.concat(this.chart.measure);
                }
            }
    
            var context = _.extend({fill_temporal: true}, this.chart.context);
    
            var proms = [];
            this.chart.domains.forEach(function (domain, originIndex) {
                proms.push(self._rpc({
                    model: self.modelName,
                    method: 'read_group',
                    context: context,
                    domain: domain,
                    fields: fields,
                    groupBy: groupBy,
                    lazy: false,
                }).then(self._processData.bind(self, originIndex)));
            });
            return Promise.all(proms);
        },

        _processData: function (originIndex, rawData) {
            this._super.apply(this, arguments);
            var self = this;
            rawData.forEach(function (dataPt, index){
                self.chart.dataPoints[index].gross = dataPt.gross_total;
                self.chart.dataPoints[index].nett = dataPt.nett_total;
                self.chart.dataPoints[index].tare = dataPt.tare_total;
            });
        },
    });

    const fixedGraphController = graphController.extend({
        async _attachDropdownComponents() {
            await this._super.apply(this, arguments);
            this.measureMenu.el.classList.add('d-none');
        },
    });

    const fixedGraphRenderer = graphRenderer.extend({

        _prepareData: function (dataPoints) {
            if (this.state.mode === 'pie'){

                let nett = 0.0;
                let tare = 0.0
                _.each(dataPoints, function(dPoint){
                    nett += dPoint.nett;
                    tare += dPoint.tare;
                });

                dataPoints = [
                    {
                        count: 1,
                        domain: [],
                        labelIndex: 0,
                        labels: ['Tare'],
                        originIndex: 0,
                        value: tare
                    },
                    {
                        count: 1,
                        domain: [],
                        labelIndex: 1,
                        labels: ['Nett'],
                        originIndex: 0,
                        value: nett
                    }
                ];
                var {datasets, labels} = this._super(dataPoints);
            } else {
                var {datasets, labels} = this._super.apply(this, arguments);
                if (this.state.mode === 'line'){
                    var {datasets, labels} = this._super.apply(this, arguments);
                    var nettData = datasets[0];
                    var tareDate = JSON.parse(JSON.stringify(nettData));
    
                    nettData.label = 'Nett';
                    tareDate.label = 'Tare';
    
                    _.each(dataPoints, function(dPoint, index){
                        nettData.data[index] = dPoint.nett;
                        tareDate.data[index] = dPoint.tare;
                    });
                    datasets.push(tareDate);
                } 
            }
            return {
                datasets: datasets,
                labels: labels
            }
        },

        _getScaleOptions: function () {
            var scaleOptions = this._super.apply(this, arguments);
            if (this.state.mode === 'line'){
                scaleOptions.yAxes[0].scaleLabel.labelString = 'Nett & Gross';
            }
        },

        _prepareOptions: function (datasetsCount) {
            var options = this._super.apply(this, arguments);
            if (this.state.mode === 'pie'){
                options.plugins = {
                    datalabels: {
                        formatter: (value, ctx) => {
                            let datasets = ctx.chart.data.datasets;
                            if (datasets.indexOf(ctx.dataset) === datasets.length - 1) {
                                let sum = datasets[0].data.reduce((a, b) => a + b, 0);
                                let percentage = Math.round((value / sum) * 100) + '%';
                                return percentage;
                            } else {
                                return percentage;
                            }
                        },
                        color: '#fff',
                    }
                }
            }
            return options;
        },

        _customTooltip: function (tooltipModel) {
            this._super.apply(this, arguments);
            if (this.state.mode === 'line'){
                this.$tooltip.find('.o_measure').html('Nett & Gross');
            }
        }
    });

    const fixedGraphView = graphView.extend({
        jsLibs: [
            '/web/static/lib/Chart/Chart.js',
            '/equip3_mining_reports/static/lib/Chart/chartjs-plugin-datalabels.min.js'
        ],

        config: _.extend({}, graphView.prototype.config, {
            Model: fixedGraphModel,
            Controller: fixedGraphController,
            Renderer: fixedGraphRenderer
        }),
    });

    viewRegistry.add('fixed_graph_view', fixedGraphView);

    return {
        fixedGraphModel: fixedGraphModel,
        fixedGraphController: fixedGraphController,
        fixedGraphRenderer: fixedGraphRenderer,
        fixedGraphView: fixedGraphView
    }
});