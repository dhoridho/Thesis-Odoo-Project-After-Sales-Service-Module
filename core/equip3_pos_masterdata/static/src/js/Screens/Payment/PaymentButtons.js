odoo.define('equip3_pos_masterdata.PaymentButtons', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');

    class PaymentButtons extends PosComponent {
        constructor() {
            super(...arguments);
        }
    }

    PaymentButtons.template = 'PaymentButtons';
    Registries.Component.add(PaymentButtons);
    return PaymentButtons;
});
