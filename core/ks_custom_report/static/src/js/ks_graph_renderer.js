odoo.define("ks_custom_report.GraphRenderer", function(require){

    var GraphRenderer = require("web.GraphRenderer");

    GraphRenderer.include({

        ksDoAction: function(domain){
            this.getParent().model.getKsmodelDomain(domain);
        },

        _renderBarChart: function(){
            var self = this;
            this._super.apply(this, arguments);
            $("#"+this.chartId).click(function(e) {
                activePoint = self.chart.getElementAtEvent(e)[0];
                if (activePoint){
                    var domain = activePoint._chart.data.domains[activePoint._index];
                    self.ksDoAction(domain);
                }
            });

            return undefined;
        },

        _renderPieChart: function(){
            var self = this;
            this._super.apply(this, arguments);
            $("#"+this.chartId).click(function(e) {
                activePoint = self.chart.getElementAtEvent(e)[0];
                if(activePoint && activePoint._chart.data.domains){
                    var domain = activePoint._chart.data.domains[activePoint._index]
                    self.ksDoAction(domain);
                }
            });

        },

        _renderLineChart: function(){
            var self = this;
            this._super.apply(this, arguments);
            $("#"+this.chartId).click(function(e) {
                activePoint = self.chart.getElementAtEvent(e)[0]
                if(activePoint){
                domain = activePoint._chart.data.domains[activePoint._index]
                self.ksDoAction(domain);
                }
            });
        },

        _prepareData: function(dataPoints){
            var self = this;
            var data = this._super.apply(this, arguments);

            var domains = _.values(dataPoints.reduce(
                function (acc, dataPt) {
                    var datasetLabel = self._getDatasetLabel(dataPt);
                    if (!('data' in acc)) {
                       acc['data'] = new Array(self._getDatasetDataLength(dataPt.originIndex, data.labels.length)).fill(0)
                    }
                    var label = self._getLabel(dataPt);
                    var labelIndex = self._indexOf(data.labels, label);
                    acc.data[labelIndex] = dataPt.domain;
                    return acc;
                },
                {}
            ));

            data['domains'] = domains[0]
            return data
        },
    });
});