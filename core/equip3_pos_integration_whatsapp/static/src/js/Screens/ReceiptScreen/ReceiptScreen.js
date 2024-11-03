odoo.define('equip3_pos_integration_whatsapp.WhatsappReceiptScreen', function(require) {
	'use strict';

	const ReceiptScreen = require('point_of_sale.ReceiptScreen');
	const Registries = require('point_of_sale.Registries');
    const { Printer } = require('point_of_sale.Printer');
    const { useRef, useContext } = owl.hooks;

    const WhatsappReceiptScreen = (ReceiptScreen) =>
    class extends ReceiptScreen {
		constructor() {
			super(...arguments);

            const order = this.currentOrder;
            const client = order.get_client();
            this.orderUiState.inputWhatsappNumber = this.orderUiState.inputWhatsappNumber || (client && client.mobile) || '';
            this.orderUiState.sendReceiptMode = 'email';
		}

        mounted() {
            super.mounted()

            // Here, we send a task to the event loop that handles
            // the printing of the receipt when the component is mounted.
            // We are doing this because we want the receipt screen to be
            // displayed regardless of what happen to the handleAutoSendWhatsappMessage
            // call.
            setTimeout(async () => await this.handleAutoSendWhatsappMessage(), 0);
        }

        /**
         * This function is called outside the rendering call stack. This way,
         * we don't block the displaying of ReceiptScreen when it is mounted; additionally,
         * any error that can happen during the printing does not affect the rendering.
         */
        async handleAutoSendWhatsappMessage() {
            if (this._shouldAutoSendWhatsappMessage()) {
                await this.autoSendWhatsappMessage();
            }
        }

        _shouldAutoSendWhatsappMessage(){
            let value = false
            let client = this.currentOrder.get_client();
            if(client && client.is_pos_member){
                if(this.env.pos.company && this.env.pos.company.pos_whatsapp_auto_sent_receipt_to_member){
                    value = true;
                }
                if(this.currentOrder._whatsapp_message_sent == true){
                    value = false;
                }
            }
            return value;
        }

        async autoSendWhatsappMessage(){
            let self = this;
            const client = this.currentOrder.get_client();
            this.orderUiState.inputWhatsappNumber = ''
            if(client.mobile){
                this.orderUiState.inputWhatsappNumber = client.mobile.trim();
            }

            if (!this.isValidWhatsappNumber(this.orderUiState.inputWhatsappNumber)) {
                self.env.pos.alert_message({
                    title: self.env._t('Warning'),
                    body: self.env._t('Can\'t Sent E-receipt Invalid whatsapp number. [' + this.orderUiState.inputWhatsappNumber + ']')
                });
                return;
            }

            try {
                self.env.pos.alert_message({
                    title: self.env._t('Info!!'),
                    body: self.env._t('Sent E-receipt to whatsapp number...')
                });

                this.currentOrder._whatsapp_message_sent = true;
                let result = await self._sendWhatsappMessageToCustomer();
                if(result.status == 'success'){
                    self.env.pos.alert_message({ title: self.env._t('Success'), body: self.env._t(result.message) });
                }else{
                    self.env.pos.alert_message({ title: self.env._t('Warning'), body: self.env._t(result.message) });
                }
            } catch (error) {
                console.log('ERROR autoSendWhatsappMessage:', error);
                self.env.pos.alert_message({
                    title: self.env._t('Warning'),
                    body: self.env._t('(ERROR) Failed when auto sent E-receipt. Please do it manually')
                });
            }
        }

        async onSumbitSendWhatsappMessage() {
            let self = this;
            this.orderUiState.whatsappSuccessful = null;
            this.orderUiState.inputWhatsappNumber = this.orderUiState.inputWhatsappNumber.trim();

            if (!this.isValidWhatsappNumber(this.orderUiState.inputWhatsappNumber)) {
                this.orderUiState.whatsappSuccessful = false;
                this.orderUiState.whatsappNotice = 'Invalid whatsapp number.';
                return;
            }

            try {
                this.orderUiState.whatsappSuccessful = 'process_sending_message';
                this.orderUiState.whatsappNotice = 'Sending to whatsapp number...';

                let result = await self._sendWhatsappMessageToCustomer();
                if(result.status == 'success'){
                    this.orderUiState.whatsappSuccessful = true;
                    this.orderUiState.whatsappNotice = result.message;
                }else{
                    this.orderUiState.whatsappSuccessful = false;
                    this.orderUiState.whatsappNotice = result.message;
                }
            } catch (error) {
                console.log('ERROR _sendWhatsappMessageToCustomer:', error);
                this.orderUiState.whatsappSuccessful = false;
                this.orderUiState.whatsappNotice = '(ERROR) Failed when sending E-receipt. Please try again.';
            }
        }

		isValidWhatsappNumber(number){
			if(number == ''){
				return false;
			}
			if(number && number.length < 10){
				return false;
			}
			return true;
		}

		async changeSendReceiptMode(mode){
			this.orderUiState.sendReceiptMode = mode;
		}

        async __wait(milliseconds){
            await new Promise(resolve => {
                return setTimeout(resolve, milliseconds)
            });
        }

        getWhatsappTicketImage(receipt) {
            var self = this;
            const process_canvas = (canvas) => canvas.toDataURL('image/jpeg').replace('data:image/jpeg;base64,','');

            $('.pos-receipt-print').html(receipt);
            var promise = new Promise(function (resolve, reject) {
                let $receipt = $('.pos-receipt-print>.pos-receipt');
                $receipt.css({
                    'text-align': 'left',
                    'width': '335px',
                    'background-color': 'white',
                    'margin': '20px',
                    'padding': '15px',
                    'font-size': '13px',
                    'border-radius': '3px',
                    'line-height': '34px',
                });
                html2canvas($receipt[0], {
                    onparsed: function(queue) {
                        queue.stack.ctx.height = Math.ceil($receipt.outerHeight() + $receipt.offset().top);
                    },
                    onrendered: function (canvas) {
                        $('.pos-receipt-print').empty();
                        resolve(process_canvas(canvas));
                    }
                })
            });
            return promise;
        }

        async _sendWhatsappMessageToCustomer() {
        	console.log('_sendWhatsappMessageToCustomer: Process...')
            const receiptString = this.orderReceipt.comp.el.outerHTML;
            const ticketImage = await this.getWhatsappTicketImage(receiptString);

            const order = this.currentOrder;
            const client = order.get_client();
            const orderName = order.get_name();
            const orderClient = { number: this.orderUiState.inputWhatsappNumber, name: client ? client.name : this.orderUiState.inputWhatsappNumber };

            let receipt = await this.rpc({
                model: 'pos.order',
                method: 'action_whatsapp_save_receipt',
                args: [[false], orderName, ticketImage],
            });
            console.log('_sendWhatsappMessageToCustomer: Save receipt:', receipt)
            if(receipt.status != 'success'){
                return new Promise(function (resolve, reject) {
                    return resolve({
                        'status': 'error',
                        'message': 'Cannot save E-receipt',
                    });
                });
            }

            this.__wait(1000);

            console.log('_sendWhatsappMessageToCustomer: Sending message...')
            var client_name = ''
            if(client){
                client_name = client.name
            }
            var days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
            var values_order = {
                'customer': client_name,
                'pos_reference':orderName,
                'date_order':order.creation_date.toLocaleDateString('en-US'),
                'day':days[order.creation_date.getDay()],
                'amount_paid':order.get_total_with_tax(),
            }
            let result = await this.rpc({
                model: 'pos.order',
                method: 'action_whatsapp_message_to_customer',
                args: [[false], orderClient.number, receipt.media,values_order],
            });
            console.log('_sendWhatsappMessageToCustomer: Done...', result)
            if(result.status == 'success'){
                return new Promise(function (resolve, reject) {
                    return resolve({
                        'status': 'success',
                        'message': 'E-receipt sent.',
                    });
                });
            }

            console.log('_sendWhatsappMessageToCustomer: failed...')
            return new Promise(function (resolve, reject) {
                return resolve({
                    'status': 'error',
                    'message': 'Failed when sending E-receipt. Please try again.',
                });
            });

        }
		
	} 

    Registries.Component.extend(ReceiptScreen, WhatsappReceiptScreen);
    return WhatsappReceiptScreen;

});