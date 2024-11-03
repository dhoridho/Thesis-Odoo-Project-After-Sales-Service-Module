odoo.define('equip3_pos_general_contd.pos_order', function (require) {
    'use strict';
    
    const Registries = require('point_of_sale.Registries');
    const PosOrder = require('equip3_pos_general.pos_order');
    const ProductScreen = PosOrder.ProductScreen;
    var models = require('point_of_sale.models');

    const {useState, useRef, useContext} = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const {useExternalListener} = owl.hooks;


    const ProductScreenExt = (ProductScreen) =>
        class extends ProductScreen {
            constructor() {
                super(...arguments);
            } 

            async _onClickPayBtn() {
                let selectedOrder = this.env.pos.get_order();
                let has_product_exchange = false;
                let orderlines = selectedOrder.get_orderlines();

                if(selectedOrder.is_exchange_order){
                    let product_exchange_count = orderlines.reduce((acc, line) => {
                        if(!line.line_qty_returned || line.quantity >= 0){
                            return acc + line.quantity;
                        }
                        return acc;
                    }, 0);

                    if(product_exchange_count <= 0){
                        this.showPopup('MyCustomMessagePopup',{
                            'title': this.env._t('Action Stopped'),
                            'body': this.env._t('Please add the new product for the exchange.'),
                        });
                    } else {
                        super._onClickPayBtn();
                        this.adjustmentPaymentProductExchange();
                    }
                } else {
                    super._onClickPayBtn();
                    this.adjustmentPaymentProductExchange();
                }

                // super._onClickPayBtn();
                // this.adjustmentPaymentProductExchange();
            }

            async adjustmentPaymentProductExchange(){
                let selectedOrder = this.env.pos.get_order();
                if(!selectedOrder.is_exchange_order){
                    return;
                }
                let has_product_exchange = false;
                let orderlines = selectedOrder.get_orderlines();

                for (var i = orderlines.length - 1; i >= 0; i--) {
                    if(orderlines[i].quantity < 0 || orderlines[i].is_product_exchange){
                        has_product_exchange = true
                    }
                }

                if(!has_product_exchange){
                    selectedOrder.paymentlines.models.forEach(function (p) {
                        if(p.payment_method.pos_method_type == 'return'){
                            p.allow_remove = true;
                            selectedOrder.remove_paymentline(p)
                        }
                    });
                    selectedOrder.is_return_order = false;
                    selectedOrder.is_exchange_order = false;
                    selectedOrder.exchange_amount = 0;
                    selectedOrder.return_status = '';
                    selectedOrder.return_order_id = false;
                    return;
                }
                
                // remove_paymentline
                selectedOrder.paymentlines.models.forEach(function (p) {
                    if(p.payment_method.pos_method_type == 'return'){
                        p.allow_remove = true;
                        selectedOrder.remove_paymentline(p)
                    }
                });

                let method = _.find(this.env.pos.payment_methods, function (method) {
                    return method.pos_method_type == 'return';
                });
                if (method) {
                    let totalWithoutProductExchange = 0;
                    let totalProductExchange = 0;
                    for (var i = orderlines.length - 1; i >= 0; i--) {
                        if(orderlines[i].quantity < 0){
                            totalProductExchange += orderlines[i].product_exchange_price;
                        }else{
                            totalWithoutProductExchange += orderlines[i].get_display_price();
                        }
                    }
                    if(totalWithoutProductExchange > Math.abs(totalProductExchange)){

                        selectedOrder.add_paymentline(method);
                        let paymentline = selectedOrder.selected_paymentline; 
                        var amount = totalWithoutProductExchange - Math.abs(totalProductExchange);
                        amount = totalWithoutProductExchange - amount;
                        paymentline.set_amount(amount);
                    }else{
                        if(totalWithoutProductExchange > 0){
                            selectedOrder.add_paymentline(method);
                            let paymentline = selectedOrder.selected_paymentline; 
                            var amount = totalWithoutProductExchange;
                            paymentline.set_amount(amount);
                        }
                    }
                }
            }
    }

    Registries.Component.extend(ProductScreen, ProductScreenExt);
    return ProductScreen;
});


