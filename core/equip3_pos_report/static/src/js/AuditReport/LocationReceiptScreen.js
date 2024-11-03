odoo.define('equip3_pos_report.LocationReceiptScreen', function(require) {
	'use strict';

	const ReceiptScreen = require('point_of_sale.ReceiptScreen');
	const Registries = require('point_of_sale.Registries');

	const LocationReceiptScreen = (ReceiptScreen) => {
		class LocationReceiptScreen extends ReceiptScreen {
			constructor() {
				super(...arguments);
			}

			back(){
				this.trigger('close-temp-screen');
				this.showScreen('ProductScreen');
			}

			async handleAutoPrint() {
				if (this._shouldAutoPrint()) {
					const isPrinted = await this._printReceipt();
					if (isPrinted) {
						const { name, props } = this.nextScreen;
						this.showScreen(name, props);
					}
				}
			}

			orderDone() {
				const { name, props } = this.nextScreen;
				this.showScreen(name, props);
			}

			async printReceipt() {
				const isPrinted = await this._printReceipt();
				if (isPrinted) {
					const { name, props } = this.nextScreen;
					this.showScreen(name, props);
				}
			}

			get_loc_summery(){
				return this['props']['output_summery_location'];
			}

			get location_receipt_data() {
				return {
					widget: this,
					pos: this.pos,
					ssn: this['props']['ssn'],
					loc_summery: this.get_loc_summery(),
					date: (new Date()).toLocaleString()

				};
			}
		}
		LocationReceiptScreen.template = 'LocationReceiptScreen';
		return LocationReceiptScreen;
	};

	Registries.Component.addByExtending(LocationReceiptScreen, ReceiptScreen);
	return LocationReceiptScreen;

});