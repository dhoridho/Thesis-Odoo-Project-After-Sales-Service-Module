odoo.define("ks_custom_report.GraphModel", function(require){

    var GraphModel = require("web.GraphModel");

    GraphModel.include({

        _processData: function (originIndex, rawData) {
            var self = this;
            var isCount = this.chart.measure === '__count__';
            var labels;

            function getLabels (dataPt) {
                return self.chart.groupBy.map(function (field) {
                    return self._sanitizeValue(dataPt[field], field.split(":")[0]);
                });
            }
            rawData.forEach(function (dataPt){
                labels = getLabels(dataPt);
                var count = dataPt.__count || dataPt[self.chart.groupBy[0]+'_count'] || 0;
                var value = isCount ? count : dataPt[self.chart.measure];
                if (value instanceof Array) {
                    // when a many2one field is used as a measure AND as a grouped
                    // field, bad things happen.  The server will only return the
                    // grouped value and will not aggregate it.  Since there is a
                    // name clash, we are then in the situation where this value is
                    // an array.  Fortunately, if we group by a field, then we can
                    // say for certain that the group contains exactly one distinct
                    // value for that field.
                    value = 1;
                }
                self.chart.dataPoints.push({
                    count: count,
                    value: value,
                    labels: labels,
                    domain: dataPt.__domain,
                    originIndex: originIndex,
                });
            });
        },

        getKsmodelDomain: function(domain){
            var self = this;
            var context = this.getSession().user_context;
            self._rpc({
                route: '/ks_custom_report/get_model_name',
                params: {
                    model: self.modelName,
                    local_context: context,
                    domain: domain,
                },
            }).then(function(result){
                if(result){
                    self.do_action(result);
                }
            })
        },

    });

    return GraphModel;
});