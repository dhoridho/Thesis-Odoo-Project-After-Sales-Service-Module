odoo.define('equip3_pos_emenu.TakeAwayButton', function (require) {
    'use strict';

    const TakeAwayButton = require('equip3_pos_masterdata.TakeAwayButton');
    const Registries = require('point_of_sale.Registries');

    const EmenuTakeAwayButton = (TakeAwayButton) => class extends TakeAwayButton {
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
    Registries.Component.extend(TakeAwayButton, EmenuTakeAwayButton);
    return EmenuTakeAwayButton;
});