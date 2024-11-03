odoo.define('equip3_pos_report.XMLPosCategorySummaryReceipt', function(require) {
	'use strict';

	const PosComponent = require('point_of_sale.PosComponent');
	const Registries = require('point_of_sale.Registries');

	class XMLPosCategorySummaryReceipt extends PosComponent {
		constructor() {
			super(...arguments);
		}
	}
	
	XMLPosCategorySummaryReceipt.template = 'XMLPosCategorySummaryReceipt';
	Registries.Component.add(XMLPosCategorySummaryReceipt);
	return XMLPosCategorySummaryReceipt;
});
