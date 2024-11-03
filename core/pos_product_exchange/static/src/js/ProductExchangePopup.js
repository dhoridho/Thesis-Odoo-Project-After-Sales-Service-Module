odoo.define('pos_product_exchange.ProductExchangePopup', function (require) {
    'use strict';

    const {useState, useRef, useContext} = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const contexts = require('point_of_sale.PosContext');
    const {useExternalListener} = owl.hooks;

    class ProductExchangePopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.changes = {
                error: this.env._t('Name is required'),
                valid: null,
                mobile: this.props.mobile || ''
            }
            this.state = useState(this.changes);
        } 

        click_exchange_order(event){
            var self = this;
            var all = $('.exchange_qty');
            var return_dict = {};
            var return_entries_ok = true;
            $.each(all, function(index, value){
                var input_element = $(value).find('input');
                var line_quantity_remaining = parseFloat(input_element.attr('line-qty-remaining'));
                var line_product_id = parseInt(input_element.attr('line-product-id'));
                var line_price_unit = parseInt(input_element.attr('line-price_unit'));
                var line_discount = parseInt(input_element.attr('line-discount'));
                var line_price_subtotal = parseFloat(input_element.attr('line-price_subtotal'));
                var line_price_subtotal_incl = parseFloat(input_element.attr('line-price_subtotal_incl'));
                var line_qty = parseFloat(input_element.attr('line-qty'));

                var line_id = parseFloat(input_element.attr('line-id'));
                var qty_input = parseFloat(input_element.val());
                if(!$.isNumeric(qty_input) || qty_input > line_quantity_remaining || qty_input < 0){
                    return_entries_ok = false;
                    input_element.css("background-color","#ff8888;");
                    setTimeout(function(){
                        input_element.css("background-color","");
                    },100);
                    setTimeout(function(){
                        input_element.css("background-color","#ff8888;");
                    },200);
                    setTimeout(function(){
                        input_element.css("background-color","");
                    },300);
                    setTimeout(function(){
                        input_element.css("background-color","#ff8888;");
                    },400);
                    setTimeout(function(){
                        input_element.css("background-color","");
                    },500);
                }

                if(qty_input == 0 && line_quantity_remaining != 0 && !self.props.is_partial_return)
                    self.props.is_partial_return = true;
                else if(qty_input > 0){
                    return_dict[line_id] = {
                        qty_input: qty_input,
                        product_id: line_product_id,
                        price_unit: line_price_unit,
                        discount: line_discount,
                        price_subtotal: line_price_subtotal,
                        price_subtotal_incl: line_price_subtotal_incl,
                        qty: line_qty,
                    }
                    if(line_quantity_remaining != qty_input  && !self.props.is_partial_return)
                        self.props.is_partial_return = true;
                    else if(!self.props.is_partial_return)
                        self.props.is_partial_return = false;
                }
            });
            if(return_entries_ok){
                self.create_return_order(return_dict);
            }
        }

        create_return_order(return_dict){
            var self = this;
            var order = self.props.order;
            var orderlines = self.props.orderlines;
            var current_order = self.env.pos.get_order(); 

            if(Object.keys(return_dict).length > 0){
                if(typeof self.env.pos.tables != 'undefined'){
                    var table = self.env.pos.tables[0];
                    if(table){
                        self.env.pos.set_table(table);
                    }
                }

                var new_order = self.env.pos.add_new_order()
                this.cancel();
                var refund_order = self.env.pos.get_order();
                if(refund_order === null){
                    self.showPopup('MyCustomMessagePopup',{
                        'title': self.env._t('Error'),
                        'body': self.env._t('Cannot Get refund_order'),
                    });
                }
                refund_order.is_return_order = true;
                refund_order.is_exchange_order = true;
                var exchange_amount = 0;

                if (typeof order.partner_id[0] != 'undefined'){
                    refund_order.set_client(self.env.pos.db.get_partner_by_id(order.partner_id[0]));
                }
                Object.keys(return_dict).forEach(function(line_id){
                    var line_id = line_id;
                    if (typeof line_id == 'object' && typeof line_id !== null){
                        line_id = line_id.id;
                    }
                    var line = return_dict[line_id];
                    var product = self.env.pos.db.get_product_by_id(line.product_id);
                    var qty_input = line.qty_input;
                    var product_exchange_base_price = (line.price_subtotal_incl / line.qty);
                    var product_exchange_price = (line.price_subtotal_incl / line.qty) * qty_input;
                    var options = {
                        quantity: -1 * qty_input,
                        price: 0,
                        discount: 0,
                        is_product_exchange: true,
                        product_exchange_price: product_exchange_price,
                        merge: false,
                    }
                    exchange_amount += product_exchange_price;
                    refund_order.add_product(product, options);

                    refund_order.selected_orderline.original_line_id = line_id;
                    refund_order.selected_orderline.line_qty_returned = qty_input;
                    refund_order.selected_orderline.is_product_exchange = true;
                    refund_order.selected_orderline.product_exchange_base_price = product_exchange_base_price;
                    refund_order.selected_orderline.product_exchange_price = product_exchange_price;
                });
                refund_order.exchange_amount = exchange_amount;
                if(self.props.is_partial_return){
                    refund_order.return_status = 'Partially-Returned';
                    refund_order.return_order_id = order.id;
                }else{
                    refund_order.return_status = 'Fully-Returned';
                    refund_order.return_order_id = order.id;
                }

                self.trigger('close-temp-screen');
                self.showScreen('PaymentScreen');
                self.showScreen('ProductScreen'); 
            }
            else{
                $(".popupinput").css("background-color","#ff8888;");
                setTimeout(function(){
                    $(".popupinput").css("background-color","");
                },100);
                setTimeout(function(){
                    $(".popupinput").css("background-color","#ff8888;");
                },200);
                setTimeout(function(){
                    $(".popupinput").css("background-color","");
                },300);
                setTimeout(function(){
                    $(".popupinput").css("background-color","#ff8888;");
                },400);
                setTimeout(function(){
                    $(".popup input").css("background-color","");
                },500);
            }
        }

        click_complete_exchange(event){
            var self = this;
            var all = $('.exchange_qty');
            $.each(all, function(index, value){
                var line_quantity_remaining = parseFloat($(value).find('input').attr('line-qty-remaining'));
                $(value).find('input').val(line_quantity_remaining);
            });
        }
        async getPayload() {
            const results = {
                items: 'Ok',
                success: true,
            };
            return results
        }
    }

    ProductExchangePopup.template = 'ProductExchangePopup';
    ProductExchangePopup.defaultProps = { title: 'Exchange Products', value:'' };
    Registries.Component.add(ProductExchangePopup);

    return ProductExchangePopup;
});