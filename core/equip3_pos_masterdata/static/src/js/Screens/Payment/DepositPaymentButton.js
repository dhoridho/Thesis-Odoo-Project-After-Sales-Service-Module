odoo.define('equip3_pos_masterdata.DepositPaymentButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');
    
    class DepositPaymentButton extends PosComponent {
        constructor() {
            super(...arguments);
        }

        is_hidden(){
            return true;
        }

        async useMemberDeposit(){
            
        }
    }

    DepositPaymentButton.template = 'DepositPaymentButton';
    Registries.Component.add(DepositPaymentButton);
    return DepositPaymentButton;
});