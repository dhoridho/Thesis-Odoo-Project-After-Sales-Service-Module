odoo.define('equip3_pos_weight_scale.PosOrderWeightScale', function(require) {
	'use strict';

    const rpc = require('web.rpc');
	const PosComponent = require('point_of_sale.PosComponent');
	const ProductScreen = require('point_of_sale.ProductScreen');
	const { useListener } = require('web.custom_hooks');
	const Registries = require('point_of_sale.Registries');
    const { Gui } = require('point_of_sale.Gui');

	class PosOrderWeightScale extends PosComponent {
		constructor() {
			super(...arguments);
			useListener('click', this.onClick);
		}
		async onClick() {
			console.log('Get Weight: start')
			let pos_drive_link = self.posmodel.config.pos_drive_link;
			if(!pos_drive_link){
                Gui.showPopup('ErrorPopup', {
                    title: _t('Error'),
                    body: _t('Please configure "Localhost link Weight Machine"'),
                });
			}

			var time = moment.utc(moment().format('YYYY-MM-DD h:mm:ss'), 'YYYY-MM-DD h:mm:ss').format('YYYY-MM-DD h:mm:ss');
			$.ajax({
			   	type: 'POST',
			   	url: pos_drive_link,
			   	cache: false,
			   	data: { time: time },
			   	success: function(data) {
			   		// data is integer
					console.log('Get Weight: data:', data) 
			       	if(!data){
	                    self.alert('Not getting any port');
	                    self.posmodel.get_order().selected_orderline.set_quantity(0.0);
	                }else{
	                    self.posmodel.get_order().selected_orderline.set_quantity(data);
	                }
			   	},
			   	error: function(response) {
			       	console.error('Get Weight Error: ', response);
                    self.alert('Network error');
			   	}
			});
		}
	}

    PosOrderWeightScale.template = 'PosOrderWeightScale';
	ProductScreen.addControlButton({
		component: PosOrderWeightScale,
		condition: function() {
			return true;
		},
	});

	Registries.Component.add(PosOrderWeightScale);
	return PosOrderWeightScale;
});
