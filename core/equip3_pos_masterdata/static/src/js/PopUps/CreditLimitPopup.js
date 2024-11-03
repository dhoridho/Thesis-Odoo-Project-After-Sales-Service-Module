odoo.define('equip3_pos_masterdata.CreditLimitPopup', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class CreditLimitPopup extends AbstractAwaitablePopup {
        amount_available_credit_limit(){
            let order = this.env.pos.get_order();
            let client = order.get_client();
            if(client){
                client = this.env.pos.db.partner_by_id[client.id];
                return this.env.pos.format_currency(client.customer_credit_limit)
            }
            return '';
        }

        confirm(){
            super.confirm();
        }
    }
    
    CreditLimitPopup.template = 'CreditLimitPopup';
    CreditLimitPopup.defaultProps = {
        title: 'PAYMENT FAILED',
    };
    Registries.Component.add(CreditLimitPopup);
    return CreditLimitPopup;
});