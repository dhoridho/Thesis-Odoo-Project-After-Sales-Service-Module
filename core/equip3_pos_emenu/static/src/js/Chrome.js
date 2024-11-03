odoo.define('equip3_pos_emenu.Chrome', function (require) {
    'use strict';

    const Chrome = require('point_of_sale.Chrome');
    const Registries = require('point_of_sale.Registries');

    const EmenuChrome = (Chrome) =>
      class extends Chrome {
        get getEmenuStatus() {
            if(this.env.pos){
                let order = this.env.pos.get_order();
                if(order && order.emenu_status){
                    return order.emenu_status;
                }
            }
            return false;
        }

        get allowAdditional() {
            if(this.env.pos && this.env.pos.config && this.env.pos.config.emenu_additional_orders_on_the_cashier_screen){
                return 'true';
            }
            return 'false';
        }
    }

    Registries.Component.extend(Chrome, EmenuChrome);
    return EmenuChrome;
});