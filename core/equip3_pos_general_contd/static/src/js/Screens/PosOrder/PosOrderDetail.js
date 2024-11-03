odoo.define('equip3_pos_general_contd.PosOrderDetail', function (require) {
    'use strict';

    var PosOrderDetail = require('equip3_pos_masterdata.PosOrderDetail');
    var Orderline = require('point_of_sale.Orderline');
    var Registries = require('point_of_sale.Registries');
    var {useListener} = require('web.custom_hooks');
    var models = require('point_of_sale.models');

    var {Gui} = require('point_of_sale.Gui');
    var { Component } = owl;
    var core = require('web.core');
    var _t = core._t;
    const current = Component.current;
 

    async function askPin(product_exchange_pin) {
        if (product_exchange_pin.includes(',')) {
            var product_exchange_pins = product_exchange_pin.split(',');
        } else {
            var product_exchange_pins = [product_exchange_pin];
        }
        const { confirmed, payload: inputPin } = await Gui.showPopup('NumberPopup', {
            isPassword: true,
            title: _t('Password ?'),
            startingValue: null,
        });

        if (!confirmed) return false;
        if (product_exchange_pins.includes(inputPin)) {
            return true;
        } else {
            await Gui.showPopup('ErrorPopup', {
                title: _t('Incorrect Password'),
            });
            return false;
        }
    } 


    const ExchangePosOrderDetail = (PosOrderDetail) =>
     class extends PosOrderDetail {
        constructor() {
            super(...arguments)
            useListener('exchange_products', () => this.ExchangeProducts());
        } 
        async ExchangeProducts() {
            let self = this;
            var order = this.props.order;
            var order_id = order.id;

            // Validate void line PIN
            if (this.env.pos.config.product_exchange_line_pins) {
                let auth = await askPin.call(current, this.env.pos.config.product_exchange_line_pins);
                if (!auth) return;
            }

            var all_pos_orders = self.env.pos.get('orders').models || []; 
            var order = self.env.pos.db.order_by_id[order_id]; 
            var return_order_exist = _.find(all_pos_orders, function(pos_order){ 
                if(pos_order.return_order_id && pos_order.return_order_id == order_id){
                    return pos_order;
                }
            }); 

            if(return_order_exist){
                self.showPopup('MyCustomMessagePopup',{
                    'title': self.env._t('Exchange/Return Already In Progress'),
                    'body': self.env._t("Exchange/Return order is already in progress. Please proceed with Order Reference " + return_order_exist.sequence_number),
                });
            }else if(order){
                var message = '';
                var non_returnable_products = false;
                var original_orderlines = [];
                var allow_return = true;
                
                if(order.return_status == 'Fully-Returned'){
                    message = 'No items are left to return for this order!!'
                    allow_return = false;
                }

                if (allow_return) { 
                    order.lines.forEach(function(line_id){
                        var line = line_id;
                        if (typeof line != 'object' && typeof line !== null){
                            line = self.env.pos.db.line_by_id[line_id];
                        }
                        var product = self.env.pos.db.get_product_by_id(line.product_id[0]);
                        if(product == null){
                            non_returnable_products = true;
                            message = 'Some product(s) of this order are unavailable in Point Of Sale, do you wish to exchange other products?'
                        }
                        else if (product.not_returnable) {
                            non_returnable_products = true;
                            message = 'This order contains some Non-Returnable products, do you wish to exchange other products?'
                        }
                        else if(line.qty - line.line_qty_returned > 0){
                            original_orderlines.push(line);
                        }
                    });
                    if(original_orderlines.length == 0){ 
                        self.showPopup('MyCustomMessagePopup',{
                            'title': self.env._t('Cannot exchange This Order!!!'),
                            'body': self.env._t("There are no exchangable products left for this order. Maybe the products are Non-Returnable or unavailable in Point Of Sale!!"),
                        });
                    }else if(non_returnable_products){ 
                        self.confirm_exchange_popup(message, original_orderlines, order, true);
                    }else{ 
                        self.showPopup('ProductExchangePopup',{
                            'orderlines': original_orderlines,
                            'order': order,
                            'is_partial_return':false,
                        }); 
                    }
                }else{ 
                    self.showPopup('MyCustomMessagePopup',{
                        'title': self.env._t('Warning!!!'),
                        'body': self.env._t(message),
                    });
                }
            }
        }

        async confirm_exchange_popup(message, original_orderlines, order, is_partial_return){
            var self = this;
            const { confirmed } = await self.showPopup('ConfirmPopup', {
                title: self.env._t('Warning !!!'),
                body: self.env._t(message),
            });
            if (confirmed) {
                self.showPopup('ProductExchangePopup',{
                    'orderlines': original_orderlines,
                    'order': order,
                    'is_partial_return': true,
                });
            }
        }
         
    }
    Registries.Component.extend(PosOrderDetail, ExchangePosOrderDetail);

    return ExchangePosOrderDetail;
});
