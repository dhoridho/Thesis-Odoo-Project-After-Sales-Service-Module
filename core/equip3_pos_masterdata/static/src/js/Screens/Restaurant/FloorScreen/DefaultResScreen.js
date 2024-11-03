odoo.define('equip3_pos_masterdata.DefaultResScreen', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const rpc = require('web.rpc');
    const {useState} = owl;

    class DefaultResScreen extends PosComponent {
        constructor() {
            super(...arguments);
        }

        back() {
            this.trigger('close-temp-screen');
        }

        async clearCart() {
            let selectedOrder = this.env.pos.get_order();
            if(selectedOrder){
                delete selectedOrder['employeemeal_employee_id'];
                delete selectedOrder['employeemeal_employee_name'];
                delete selectedOrder['employeemeal_budget'];

                if (selectedOrder.orderlines.models.length > 0) {
                    let orderline = selectedOrder.get_orderlines();
                    orderline.forEach((orderline) => {
                        var vals = []
                        var product_id = orderline.product.id
                        var qty = orderline.quantity
                        var date = new Date();
                        return rpc.query({
                            model: 'product.cancel',
                            method: 'SavelogProcuctCancel',
                            args: [[], vals, product_id, qty, date],
                        });
                    }); 

                    while (selectedOrder.orderlines.models.length > 0) {
                        selectedOrder.orderlines.models.forEach(l => selectedOrder.remove_orderline(l))
                    }
                    selectedOrder.is_return = false;
                }  
            }
        }
        
    }

    DefaultResScreen.template = 'DefaultResScreen';

    Registries.Component.add(DefaultResScreen);

    return DefaultResScreen;
});
