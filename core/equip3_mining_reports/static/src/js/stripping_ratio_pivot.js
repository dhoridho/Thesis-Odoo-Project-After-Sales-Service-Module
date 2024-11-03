odoo.define('equip3_mining_reports.StrippingRatioPivot', function(require){
    "use strict";

    const PivotRenderer = require('web.PivotRenderer');
    const PivotModel = require('web.PivotModel');
    const PivotView = require('web.PivotView');
    const viewRegistry = require('web.view_registry');
    const patchMixin = require('web.patchMixin');

    var core = require('web.core');
    var _t = core._t;

    class StrippingPivotRenderer extends PivotRenderer {
        _onHeaderClick(cell, type) {
            if (cell && cell.indent === 0){
                return;
            }
            super._onHeaderClick(cell, type);
        }
    }

    const StrippingPivotModel = PivotModel.extend({
        _getTableRows: function (tree, columns) {
            var rows = this._super.apply(this, arguments);
            if (rows[0].title === _t('Total') || rows[0].title === _t('Stripping Ratio')){
                rows[0].title = _t('Stripping Ratio');

                if (rows[0].subGroupMeasurements.length){

                    let extractionRow, wasteRow;
                    _.each(rows, function(row){
                        if (row.indent === 1){
                            if (row.title === 'Extraction'){
                                extractionRow = row;
                            } else if (row.title === 'Waste Removal'){
                                wasteRow = row;
                            }
                        }
                    });

                    if (extractionRow && wasteRow){
                        _.each(rows[0].subGroupMeasurements, function(col, index){
                            let extractionTotal = extractionRow.subGroupMeasurements[index].value;
                            let wasteTotal = wasteRow.subGroupMeasurements[index].value;
                            col.value = extractionTotal === 0.0 ? 0.0 : wasteTotal / extractionTotal;
                        });
                    }
                }
            }
            return rows;
        }
    });

    const StrippingPivotRendererPatched = patchMixin(StrippingPivotRenderer);

    const StrippingPivotView = PivotView.extend({
        config: _.extend({}, PivotView.prototype.config, {
            Model: StrippingPivotModel,
            Renderer: StrippingPivotRendererPatched
        }),
    });

    viewRegistry.add('stripping_ratio_pivot', StrippingPivotView);
    
    return {
        StrippingPivotRenderer: StrippingPivotRendererPatched,
        StrippingPivotModel: StrippingPivotModel,
        StrippingPivotView: StrippingPivotView
    }
});