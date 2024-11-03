odoo.define('equip3_pos_emenu.SubmitOrderButton', function (require) {
    'use strict';

    const SubmitOrderButton = require('pos_restaurant.SubmitOrderButton');
    const Registries = require('point_of_sale.Registries');

    const EmenuSubmitOrderButton = (SubmitOrderButton) => class extends SubmitOrderButton {
        constructor() {
            super(...arguments);
        }

        async beforeShowReceipt() {
            let order = this.env.pos.get_order();
            if(order.emenu_order_id){ 
                if(this.state.sync == 'connecting'){
                    return;
                }
                this.state.sync = 'connecting';
                await this.env.pos.emenu_save_cashier_changes(order);
                this.state.sync = 'done';
            }
            super.beforeShowReceipt();
        }

    }
    Registries.Component.extend(SubmitOrderButton, EmenuSubmitOrderButton);
    return EmenuSubmitOrderButton;
});