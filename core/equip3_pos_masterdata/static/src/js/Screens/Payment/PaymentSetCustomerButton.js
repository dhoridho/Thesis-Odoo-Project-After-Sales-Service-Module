odoo.define('equip3_pos_masterdata.PaymentSetCustomerButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');

    class PaymentSetCustomerButton extends PosComponent {
        constructor() {
            super(...arguments);
        }

        async selectClient() {
            const order = this.env.pos.get_order();
            const currentClient = order.get_client();
            const { confirmed, payload: newClient } = await this.showTempScreen(
                'ClientListScreen',
                { client: currentClient }
            );
            if (confirmed) {
                order.set_client(newClient);
                order.updatePricelist(newClient);
            }
            posbus.trigger('set-screen', 'Payment')
        }

    }

    PaymentSetCustomerButton.template = 'PaymentSetCustomerButton';
    Registries.Component.add(PaymentSetCustomerButton);
    return PaymentSetCustomerButton;
});
