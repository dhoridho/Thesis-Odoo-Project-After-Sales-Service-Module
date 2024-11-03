odoo.define('equip3_assembly_reports.assembly_production_record_report', function(require) {
	'use strict';

	var stock_report = require('stock.stock_report_generic');
	var core = require('web.core');

	var Equip3AssemblyReport = stock_report.extend({
		init: function(parent, action) {
			this._super.apply(this, arguments);
		},
		get_html: function() {
			var self = this;
			var args = [
				this.given_context.active_id,
			];
			return this._rpc({
					model: 'report.equip3_assembly_reports.report_assembly_production',
					method: 'get_html',
					args: args,
					context: this.given_context,
				})
				.then(function(result) {
					self.data = result;
				});
		},
		set_html: function() {
			var self = this;
			return this._super().then(function() {
				self.$('.o_content').html(self.data.lines);
			});
		},
	});

	core.action_registry.add('assembly_production_record_report', Equip3AssemblyReport);
	return Equip3AssemblyReport;
});