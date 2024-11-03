odoo.define('equip3_pos_membership.PaymentScreenPaymentLines', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const PaymentScreenPaymentLines = require('point_of_sale.PaymentScreenPaymentLines');
    const {useState} = owl.hooks;
    const {useListener} = require('web.custom_hooks');
    const models = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');

    const RetailPaymentScreenPaymentLines = (PaymentScreenPaymentLines) =>
        class extends PaymentScreenPaymentLines { 
            get payment_with_member_points() {
                let selectedOrder = this.env.pos.get_order();
                var res = []
                if(selectedOrder){
                    selectedOrder.orderlines.models.forEach(l => {
                        if(l.redeem_point && l.redeem_point > 0) {
                            res.push(l)
                        }
                    });
                }
                return res
            }
            format_member_point_amount(amount) {
                let selectedOrder = this.env.pos.get_order();
                var currency = false
                if(selectedOrder){
                    currency = selectedOrder.currency
                }
                return this.env.pos.format_currency(amount,currency);
            }
            delete_member_point_line(line){
                let selectedOrder = this.env.pos.get_order();
                if(selectedOrder){
                    selectedOrder.orderlines.models.forEach(l => {
                        if(l.redeem_point && l.redeem_point > 0) {
                            if(l.id == line.id) {
                                selectedOrder.remove_orderline(l);
                            }
                        }
                    });
                }
                this.render();
            }
            selected_member_point_line(line){
                let selectedOrder = this.env.pos.get_order();
                if(selectedOrder){
                    selectedOrder.orderlines.models.forEach(l => {
                        if(l.redeem_point && l.redeem_point > 0) {
                            if(l.id == line.id) {
                                l.selected_redeem_payment = true
                            }
                            else{
                                l.selected_redeem_payment = false
                            }
                        }
                    });
                    this.props.paymentLines.forEach(l => {
                        l.set_selected(false);
                    });
                }
                this.render();
            }
        }

    Registries.Component.extend(PaymentScreenPaymentLines, RetailPaymentScreenPaymentLines);
    PaymentScreenPaymentLines.template = 'RetailPaymentScreenPaymentLines'

    return RetailPaymentScreenPaymentLines;
});
