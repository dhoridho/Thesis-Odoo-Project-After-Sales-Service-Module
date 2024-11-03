odoo.define('equip3_pos_general_contd.PaymentScreen', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const NumberBuffer = require('point_of_sale.NumberBuffer');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');

    const PaymentScreenExt = (PaymentScreen) =>
     class extends PaymentScreen {
        constructor() {
            super(...arguments)
        }
        _updateSelectedPaymentline() {
            if (this.paymentLines.every((line) => line.paid)) {
                this.currentOrder.add_paymentline(this.payment_methods_from_config[0]);
            }
            if (!this.selectedPaymentLine) return; // do nothing if no selected payment line
            // disable changing amount on paymentlines with running or done payments on a payment terminal

            if(this.selectedPaymentLine.order.is_exchange_order){
                let cashExist = this.paymentLines.some( l => l.payment_method.pos_method_type == 'default' );
                if(!cashExist){
                    let totalPayment = this.currentOrder.get_total_with_tax();
                    let exchangeAmount = this.currentOrder.exchange_amount;
                    let has_product_exchange = false;
                    let _orderLines = this.currentOrder.get_orderlines();
                    for (var i = _orderLines.length - 1; i >= 0; i--) {
                        if(_orderLines[i].quantity < 0 || _orderLines[i].is_product_exchange){
                            has_product_exchange = true;
                        }
                    }
                    if(has_product_exchange && totalPayment > 0){
                        if((totalPayment - exchangeAmount) > 0 ){
                            let cash_method = _.find(this.env.pos.payment_methods, function (method) {
                                return method.pos_method_type == 'default';
                            });
                            this.currentOrder.add_paymentline(cash_method);
                        }
                    }
                }
                if(this.selectedPaymentLine.payment_method.pos_method_type == 'return'){
                    return;
                }
            }

            super._updateSelectedPaymentline()
        }
    }

    Registries.Component.extend(PaymentScreen, PaymentScreenExt);

    return PaymentScreenExt;

});