odoo.define('equip3_pos_report.LocationReceipt', function(require) {
	'use strict';

	const PosComponent = require('point_of_sale.PosComponent');
	const Registries = require('point_of_sale.Registries');

	class LocationReceipt extends PosComponent {
		constructor() {
			super(...arguments);
		}	
	}
	LocationReceipt.template = 'LocationReceipt';
	Registries.Component.add(LocationReceipt);
	return LocationReceipt;
});

	