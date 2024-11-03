odoo.define('equip3_pos_masterdata.PaymentScreenPaymentLines', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const PaymentScreenPaymentLines = require('point_of_sale.PaymentScreenPaymentLines');
    const {useState} = owl.hooks;
    const {useListener} = require('web.custom_hooks');
    const models = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');

    const RetailPaymentScreenPaymentLines = (PaymentScreenPaymentLines) =>
        class extends PaymentScreenPaymentLines { 
            formatLineAmount(paymentline) {
                let selectedOrder = this.env.pos.get_order();
                var currency = false
                if(selectedOrder){
                    currency = selectedOrder.currency
                }
                return this.env.pos.format_currency(paymentline.get_amount(),false,currency);
            }

            formatLineAmountWithRounding(paymentline) {
                let selectedOrder = this.env.pos.get_order();
                var currency = false
                if(selectedOrder){
                    currency = selectedOrder.currency
                }
                return this.env.pos.format_currency(paymentline.get_amount_with_rounding(),false,currency);
            }

            get disableRemoveLine() {
                if (this.line && this.line.payment_method && this.line.payment_method.pos_method_type == 'rounding') {
                    return true
                }
                return false
            }
            get cardNumberType() {
                if(this.cardPayment()){
                    if(this.cardPayment().have_char){
                        return 'text';
                    }
                }
                return 'number';
            }
            async validateCardNumber(line){
                let $line = $('.card-number[data-cid='+line.cid+']');
                let val = $line.val();
                line.card_payment_number = val;
                if(this.cardPayment()){
                    if(this.cardPayment().BIN != val){
                        line.card_payment_number = '';
                        $line.addClass('has-error');
                        return this.showPopup('ErrorPopup', {
                            title: this.env._t('Warning'),
                            body: this.env._t('Card Number is invalid!'),
                            confirmText: 'OK',
                            cancelText: ''
                        });
                    }
                    $line.removeClass('has-error');
                }
            }
            cardPayment(){
                let selectedOrder = this.env.pos.get_order();
                if(selectedOrder){
                    if(selectedOrder.selected_card_payment_id){
                        return this.env.pos.db.get_card_payment_by_id(selectedOrder.selected_card_payment_id);
                    }
                }
                return false;
            }
            get hasCardPayment() {
                if(this.cardPayment()){
                    return true;
                }
                return false;
            }
            get hasMDRPayment() {
                return this.props.paymentLines.find((pline) => pline.mdr_paid_by === 'Customer');
            }
            formatLineAmountMDR(paymentline) {
                let selectedOrder = this.env.pos.get_order();
                var currency = false
                if(selectedOrder){
                    currency = selectedOrder.currency
                }
                return this.env.pos.format_currency(paymentline.get_mdr_customer_amount(),currency);
            }

            is_client_use_voucher(){
                let use_voucher = false;
                let order = this.env.pos.get_order();
                if(order && order.client_use_voucher == true){
                    let orderlines = order.orderlines.models;
                    for (let i = orderlines.length - 1; i >= 0; i--) {
                        if(orderlines[i].is_product_voucher){
                            use_voucher = true;
                            break;
                        }
                    }
                }
                return use_voucher;
            }
            get_client_use_voucher_amount() {
                let amount = 0;
                let order = this.env.pos.get_order();
                if(order && order.client_use_voucher_amount){
                    amount += order.client_use_voucher_amount;
                }
                return amount;
            }

        }

    Registries.Component.extend(PaymentScreenPaymentLines, RetailPaymentScreenPaymentLines);
    PaymentScreenPaymentLines.template = 'RetailPaymentScreenPaymentLines'

    return RetailPaymentScreenPaymentLines;
});
