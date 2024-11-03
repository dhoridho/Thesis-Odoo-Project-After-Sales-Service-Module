
odoo.define('bi_loyalty_generic.BiProductScreen', function(require) {
	"use strict";

	const models = require('point_of_sale.models');
	const PosComponent = require('point_of_sale.PosComponent');
	const Registries = require('point_of_sale.Registries');
	const Session = require('web.Session');
	const chrome = require('point_of_sale.Chrome');
	const ControlButtonsMixin = require('point_of_sale.ControlButtonsMixin');
	const NumberBuffer = require('point_of_sale.NumberBuffer');
	const { useListener } = require('web.custom_hooks');
	const { onChangeOrder, useBarcodeReader } = require('point_of_sale.custom_hooks');
	const { useState } = owl.hooks;

	const ProductScreen = require('point_of_sale.ProductScreen'); 

	const BiProductScreen = (ProductScreen) =>
		class extends ProductScreen {
			constructor() {
				super(...arguments);
			}

			async _onClickCustomer() {
				let order = this.env.pos.get_order();
				let self = this;
				if(order.redeem_done){
					this.showPopup('ErrorPopup',{
						'title': this.env._t('Cannot Change Customer'),
						'body': this.env._t('Sorry, you redeemed product, please remove it before changing customer.'),
					}); 
				}else{
					const currentClient = this.currentOrder.get_client();
					const { confirmed, payload: newClient } = await this.showTempScreen(
						'ClientListScreen',
						{ client: currentClient }
					);
					if (confirmed) {
						this.currentOrder.set_client(newClient);
						this.currentOrder.updatePricelist(newClient);
					}
				}
				
			}
			
		};

	Registries.Component.extend(ProductScreen, BiProductScreen);

	return ProductScreen;

});
