odoo.define('setu_cash_flow_forecasting.PivotModel', function (require) {
    "use strict";

    var PivotModel = require('web.PivotModel');
    var core = require('web.core');
    var _t = core._t;

PivotModel.prototype._getTable = function(){
    const headers = this._getTableHeaders();
    const rows = this._getTableRows(this.rowGroupTree, headers[headers.length - 1]);
    var count_1 =  this.data.measures.length
    var i =0
    if(this.loadParams.modelName == 'setu.cash.forecast' || this.loadParams.modelName == 'setu.cash.forecast.report'){
        headers[0].splice(1);
        while(i<count_1){
            headers[2].pop()
            i++
        }
    }
    return {
        headers: headers,
        rows: rows,
    };
},
PivotModel.prototype._getTableRows =  function (tree, columns) {

        var self = this;
        var rows = [];
        var group = tree.root;
        var rowGroupId = [group.values, []];
        var title = group.labels[group.labels.length - 1] || _t('Total');
        var indent = group.labels.length;
        var isLeaf = !tree.directSubTrees.size;
        var rowGroupBys = this._getGroupBys().rowGroupBys;
        var count = this.data.measures.length

        var subGroupMeasurements = columns.map(function (column) {
            var colGroupId = column.groupId;
            var groupIntersectionId = [rowGroupId[0], colGroupId[1]];
            var measure = column.measure;
            var originIndexes = column.originIndexes || [0];

            var value = self._getCellValue(groupIntersectionId, measure, originIndexes);

            var measurement = {
                groupId: groupIntersectionId,
                originIndexes: originIndexes,
                measure: measure,
                value: value,
                isBold: !groupIntersectionId[0].length || !groupIntersectionId[1].length,
            };
            return measurement;
        });
        if(this.loadParams.modelName == 'setu.cash.forecast' || this.loadParams.modelName == 'setu.cash.forecast.report'){
            if(subGroupMeasurements.length > 1)
            {
                var subGroupMeasurements_custom = subGroupMeasurements.slice(0, -count)
            }
            else
            {
                 var subGroupMeasurements_custom = subGroupMeasurements
            }
        }
        else
        {
            var subGroupMeasurements_custom = subGroupMeasurements
        }
        if(title != "Total"){
            rows.push({
            title: title,
            label: indent === 0 ? undefined : this.fields[rowGroupBys[indent - 1].split(':')[0]].string,
            groupId: rowGroupId,
            indent: indent,
            isLeaf: isLeaf,
            subGroupMeasurements: subGroupMeasurements_custom,
        });
        }

        var subTreeKeys = tree.sortedKeys || [...tree.directSubTrees.keys()];
        subTreeKeys.forEach(function (subTreeKey) {
            var subTree = tree.directSubTrees.get(subTreeKey);
            rows = rows.concat(self._getTableRows(subTree, columns));
        });

        return rows;
}

});

