odoo.define('equip3_mining_reports.StrippingRatioGraph', function(require){
    "use strict";

    const graphRenderer = require('web.GraphRenderer');
    const graphController = require('web.GraphController');
    const graphView = require('web.GraphView');
    const viewRegistry = require('web.view_registry');

    const strippingGraphController = graphController.extend({
        async _attachDropdownComponents() {
            await this._super.apply(this, arguments);
            this.measureMenu.el.classList.add('d-none');
        },
    });

    const strippingGraphRenderer = graphRenderer.extend({
        _prepareOptions: function (datasetsCount) {
            var options = this._super.apply(this, arguments);
            if (this.state.mode === 'pie'){
                let extraction = 0.0;
                let wasteRemoval = 0.0;
                _.each(this.state.dataPoints, function(dPoint){
                    if (dPoint.labels[0] === 'Extraction'){
                        extraction += dPoint.value;
                    } else if (dPoint.labels[0] === 'Waste Removal'){
                        wasteRemoval += dPoint.value;
                    }
                });
                let strippingRatio = extraction === 0.0 ? 0.0 : wasteRemoval / extraction;
                
                options.title = {
                    display: true,
                    text: 'Stripping Ratio: ' + strippingRatio.toFixed(5)
                };
                options.plugins = {
                    datalabels: {
                        formatter: (value, ctx) => {
                            return value;
                        },
                        color: '#fff',
                    }
                };
            }
            return options;
        },
    });

    const strippingGraphView = graphView.extend({
        jsLibs: [
            '/web/static/lib/Chart/Chart.js',
            '/equip3_mining_reports/static/lib/Chart/chartjs-plugin-datalabels.min.js'
        ],

        config: _.extend({}, graphView.prototype.config, {
            Controller: strippingGraphController,
            Renderer: strippingGraphRenderer
        }),
    });

    viewRegistry.add('stripping_ratio_graph', strippingGraphView);

    return {
        strippingGraphController: strippingGraphController,
        strippingGraphRenderer: strippingGraphRenderer,
        strippingGraphView: strippingGraphView
    }
});