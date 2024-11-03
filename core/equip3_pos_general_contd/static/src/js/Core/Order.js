odoo.define('equip3_pos_general_contd.order', function (require) {
    'use strict';

    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const NumberBuffer = require('point_of_sale.NumberBuffer');
    const Registries = require('point_of_sale.Registries');
    const models = require('point_of_sale.models'); 
    const core = require('web.core');
    const _t = core._t;

    let _super_Order = models.Order.prototype;
    models.Order = models.Order.extend({

        
        add_product: async function (product, options) {
            let check = this.get_orderlines().filter((l) => l.product.id==product.id && l.line_qty_returned)
            if(check.length>0){
                return this.pos.chrome.showPopup('ErrorPopup', {
                                title: _t('Warning !'),
                                body: _t("Can't add product with same product exchange.")
                            })
            }
            let res = _super_Order.add_product.call(this, product, options);
            return res
        },

        get_screen_data: function(){
            const screen = this.screen_data['value'];
            if (screen){
                if (screen['name'] == 'PosOrderScreen' && $('.table_ticketing').length > 0){
                    screen['name'] = 'ProductScreen'
                }
            }
            
            // If no screen data is saved
            //   no payment line -> product screen
            //   with payment line -> payment screen
            if (!screen) {
                if (this.get_paymentlines().length > 0) return { name: 'PaymentScreen' };
                return { name: 'ProductScreen' };
            }
            if (!this.finalized && this.get_paymentlines().length > 0) {
                return { name: 'PaymentScreen' };
            }
            return screen;

        },
 
        remove_paymentline: function (line) {
            if(line.order.is_exchange_order){
                if(line.payment_method.pos_method_type == 'return' && line.allow_remove != true){
                    return;
                }
            }
            if(this.pos.selected_order_method == 'employee-meal'){
                if(line.payment_method.name.toLowerCase().trim() == 'employee budget' && line.allow_remove != true){
                    return;
                }
            }
            let res = _super_Order.remove_paymentline.apply(this, arguments);
        },

    });

});