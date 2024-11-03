odoo.define('equip3_pos_payment_edc.PaymentScreen', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');
    const PaymentScreenPaymentLines = require('point_of_sale.PaymentScreenPaymentLines');
                
    const {Gui} = require('point_of_sale.Gui');
    const core = require('web.core');
    const _t = core._t;

    const EDCPaymentScreen = (PaymentScreen) =>
    class extends PaymentScreen {
        constructor() {
            super(...arguments);
        }

        mounted() {
            super.mounted();
        } 


        async validateOrder(isForceValidate) {
            const order = this.currentOrder;
            const paymentlines = order.get_paymentlines();
            let payment_edc_state = false;
            let payment_line_edc = false;
            let payment_method = false;

            for (var i = paymentlines.length - 1; i >= 0; i--) {
                payment_method = paymentlines[i].payment_method;
                if(payment_method && payment_method.is_payment_edc){
                    payment_line_edc = paymentlines[i];
                    break
                }
            }
            if(payment_line_edc){
                payment_edc_state = payment_line_edc.payment_edc_state;
                if(payment_edc_state != 'paid'){ 
                    let message = 'Please send request payment before completing order!';
                    if(payment_method.is_edc_manual_input){
                        message = 'Please Manually Input "Approval Code" before completing order!';
                    }
                    Gui.showPopup('ErrorPopup', {
                        title: 'Invalid',
                        body: _t(message)
                    });
                    this.isProcessing = false; // reset blocking multiple click complete order
                    return;
                }
            }

            return super.validateOrder(isForceValidate);
        }

        async addNewPaymentLine({detail: paymentMethod}) {
            //TODO: Select installment tenor
            if(paymentMethod.is_edc_bca && paymentMethod.trans_type == 'credit_card'){
                const order = this.env.pos.get_order();
                let {confirmed: confirmed, payload: payload} = await Gui.showPopup('SelectInstallmentTenorPopUps', 
                    {'installment_tenor_ids': paymentMethod.installment_tenor_ids});
                if(confirmed){
                    if(payload.value){
                        order.installment_tenor = payload.value;
                    }
                }
                if(!confirmed){
                    return;   
                }
            }
            super.addNewPaymentLine({detail: paymentMethod});
        }

    }

    Registries.Component.extend(PaymentScreen, EDCPaymentScreen);
    return EDCPaymentScreen;
});

