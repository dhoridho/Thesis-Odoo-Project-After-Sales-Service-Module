odoo.define('equip3_pos_online_outlet.Chrome', function (require) {
    'use strict';

    const Chrome = require('point_of_sale.Chrome');
    const Registries = require('point_of_sale.Registries');

    const OnlineOrderChrome = (Chrome) =>
        class extends Chrome {
            get getOrderType() {
                let order_type = '';
                if(this.env.pos){
                    let selectedOrder = this.env.pos.get_order();
                    if(selectedOrder){
                        if(selectedOrder.oloutlet_order_id){
                            order_type = 'online-order';
                        }
                    }
                }
                return order_type
            }
        }
    Registries.Component.extend(Chrome, OnlineOrderChrome);
    return OnlineOrderChrome;
});