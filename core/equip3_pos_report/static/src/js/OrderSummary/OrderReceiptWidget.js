odoo.define('equip3_pos_report.OrderReceiptWidget', function(require) {
	'use strict';

	const ReceiptScreen = require('point_of_sale.ReceiptScreen');
	const Registries = require('point_of_sale.Registries');

	const OrderReceiptWidget = (ReceiptScreen) => {
		class OrderReceiptWidget extends ReceiptScreen {
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

			get order_receipt_data() {
				var is_current = this.env.pos.get_order().get_screen_data('order_current_session')
				return {
					widget: this,
					pos: this.env.pos,
					order_current_session :this['props']['order_current_session'],
					summery: this.get_summery(),
					st_date:this.get_order_st_date(),
					ed_date:this.get_order_ed_date(),
					date_o: (new Date()).toLocaleString(),
				};
			}


			get_order_st_date(){
				return this['props']['ord_start_dt'];
			}

			get_order_ed_date(){
				return this['props']['ord_end_dt'];
			}

			get_summery(){
				return this['props']['output_summery'];
			}
		}

		OrderReceiptWidget.template = 'OrderReceiptWidget';
		return OrderReceiptWidget
	};
	Registries.Component.addByExtending(OrderReceiptWidget,ReceiptScreen);
	return OrderReceiptWidget;

});