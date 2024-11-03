odoo.define('equip3_pos_report.PivotController', function (require) {
"use strict";

var core = require('web.core');
var PivotController = require('web.PivotController');
var viewRegistry = require('web.view_registry');
var PivotView = require('web.PivotView');

var _t = core._t;


var PivotControllerPOSReport = PivotController.extend({
	_onOpenView: function (ev) {
		const context = Object.assign({}, this.model.data.context);
		if ('pos_detail_report' in context){
			ev.stopPropagation();
	        const $target = ev.target;
	        const cell = ev.data;
	        if (cell.value === undefined || this.disableLinking) {
	            return;
	        }
	        Object.keys(context).forEach(x => {
	            if (x === 'group_by' || x.startsWith('search_default_')) {
	                delete context[x];
	            }
	        });

	        const group = {
	            rowValues: cell.groupId[0],
	            colValues: cell.groupId[1],
	            originIndex: cell.originIndexes[0]
	        };

	        const domain = this.model._getGroupDomain(group);
	        var title = this.title

	    	var rows = cell.__originalComponent.props.table.rows
	    	var row_selected = rows.filter(r => r.groupId[0] == cell.groupId[0]);
	    	if(row_selected.length>0){
	    		title = row_selected[0].title
	    	}
	        
	        this.do_action({
	            type: 'ir.actions.act_window',
	            name: title,
	            res_model: this.modelName,
	            views: this.views,
	            view_mode: 'list',
	            target: 'current',
	            context: context,
	            domain: domain,
	        });
		}
		else {
			this._super.apply(this, arguments);
		}
    },
});

var POSReportPivotView = PivotView.extend({
    config: _.extend({}, PivotView.prototype.config, {
        Controller: PivotControllerPOSReport,
    }),
});

viewRegistry.add('pivot_view_eq_pos_report', POSReportPivotView);

return {
    PivotControllerPOSReport: PivotControllerPOSReport,
    POSReportPivotView: POSReportPivotView,
};

});
