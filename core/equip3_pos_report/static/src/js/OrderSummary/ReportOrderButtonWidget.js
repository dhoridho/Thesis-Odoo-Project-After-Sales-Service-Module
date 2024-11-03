odoo.define('equip3_pos_report.ReportOrderButtonWidget', function(require) {
	'use strict';

	const PosComponent = require('point_of_sale.PosComponent');
	const ProductScreen = require('point_of_sale.ProductScreen');
	const { useListener } = require('web.custom_hooks');
	let core = require('web.core');
	let _t = core._t;
	const Registries = require('point_of_sale.Registries');

	class ReportOrderButtonWidget extends PosComponent {
		constructor() {
			super(...arguments);
			useListener('click', this.onClick);
		}
			
		async onClick(){
			var self = this;
			self.showPopup('PopupOrderWidget',{
				'title': 'Order Summary',
			});
		}
	}
	
	ReportOrderButtonWidget.template = 'ReportOrderButtonWidget';
	ProductScreen.addControlButton({
		component: ReportOrderButtonWidget,
		condition: function() {
			return this.env.pos.config.order_summery;
		},
	});
	Registries.Component.add(ReportOrderButtonWidget);
	return ReportOrderButtonWidget;
});