odoo.define('equip3_pos_report_ph.PaymentScreen', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Pos_masterdata_PaymentScreen = require('equip3_pos_masterdata.PaymentScreen');
    const {useListener} = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const core = require('web.core');
    const _t = core._t;
    const Session = require('web.Session');
    const {posbus} = require('point_of_sale.utils');


    const RetailPaymentScreenPH = (PaymentScreen) =>
        class extends PaymentScreen {
            async validateOrder(isForceValidate) {
                let currentOrder = this.env.pos.get_order();
                if(this.env.pos.config.is_ph_training_mode){
                    currentOrder.name = (currentOrder.name).replace('Order','Training')
                    currentOrder.is_ph_training_mode = true
                }
                var res = super.validateOrder(isForceValidate)
                return res
            }



        }
    Registries.Component.extend(PaymentScreen, RetailPaymentScreenPH);

    return RetailPaymentScreenPH;
});
