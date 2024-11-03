/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */
odoo.define('pos_orders.pos_orders',function(require){
    "use strict"
    var models = require('point_of_sale.models');
    var core = require('web.core');
    var QWeb = core.qweb;
    var SuperPosModel = models.PosModel.prototype;
    const Registries = require('point_of_sale.Registries');
    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const ClientLine = require('point_of_sale.ClientLine');
	const { useListener } = require('web.custom_hooks');

    models.load_models([{
            model: 'pos.order',
            fields: ['id', 'name', 'date_order', 'partner_id', 'lines', 'pos_reference','account_move'],
            context: function (self) {
                    return {'pos_config_id': self.config.id}
                },
            domain: function(self) {
                var domain_list = []; 
                return domain_list;
            },
            loaded: function(self, wk_order) {
                self.db.pos_all_orders = wk_order;
                self.db.order_by_id = {};
                self.db.order_by_ean13 = {};
                self.db.pos_orders = [];
                wk_order.forEach(function(order){
                    var order_date = new Date(order['date_order']);
                    var utc = order_date.getTime() - (order_date.getTimezoneOffset() * 60000);
                    order['date_order'] = new Date(utc).toLocaleString();
                    self.db.order_by_id[order.id] = order;
                    self.db.order_by_ean13[order.ean13] = order
                    self.db.pos_orders.push(order)
                });
            },
        }, {
            model: 'pos.order.line',
            fields: ['product_id', 'order_id', 'qty','discount','price_unit','price_subtotal_incl','price_subtotal'],
            domain: function(self) {
                var order_lines = []
                var orders = self.db.pos_all_orders;
                for (var i = 0; i < orders.length; i++) {
                    order_lines = order_lines.concat(orders[i]['lines']);
                }
                return [
                    ['id', 'in', order_lines]
                ];
            },
            loaded: function(self, wk_order_lines) {
                self.db.pos_all_order_lines = wk_order_lines;
                self.db.line_by_id = {};
                wk_order_lines.forEach(function(line){
                    self.db.line_by_id[line.id] = line;
                });
            },
        }, ], {
        'after': 'product.product'
    });

    models.PosModel = models.PosModel.extend({
        _save_to_server: function (orders, options) {
            var self = this;
            return SuperPosModel._save_to_server.call(this,orders,options).then(function(return_dict){
                if(return_dict){
                    _.forEach(return_dict, function(data){
                        if(data.orders != null){
                            data.orders.forEach(function(order){
                                if(order.existing)
                                {
                                    self.db.pos_all_orders.forEach(function(order_from_list){
                                        if(order_from_list.id == order.original_order_id)
                                            order_from_list.return_status = order.return_status
                                    });
                                }
                                else{
                                    var order_date = new Date(order['date_order'])
                                    var utc = order_date.getTime() - (order_date.getTimezoneOffset() * 60000);
                                    order['date_order'] = new Date(utc).toLocaleString()
                                    self.db.pos_all_orders.unshift(order);
                                    self.db.order_by_id[order.id] = order;
                                    self.db.pos_orders.push(order)
                                    self.db.order_by_ean13[order.ean13] = order
                                }
                            });

                            data.orderlines.forEach(function(orderline){
                                if(orderline.existing){
                                    var target_line = self.db.line_by_id[orderline.id];
                                    target_line.line_qty_returned = orderline.line_qty_returned;
                                }
                                else{
                                    self.db.pos_all_order_lines.unshift(orderline);
                                    self.db.line_by_id[orderline.id] = orderline;
                                }
                            });
                        
                            if(self.db.all_payments)
                                data.payments.forEach(function(payment) {
                                    self.db.all_payments.unshift(payment);
                                    self.db.payment_by_id[payment.id] = payment;
                            });

                            delete data.orders;
                            delete data.orderlines;
                            delete data.payments;
                        }
                    })
                }
                return return_dict
            });
        }
    });

    class OrdersScreenWidget extends PosComponent {
		get_customer(customer_id){
            var self = this;
            if(this.props && this.props.customer_id){
                return this.props.customer_id
            }
            else{
                return undefined;
            }
        }
		render_list(order, input_txt){
            var self = this;
            var customer_id = this.get_customer();
            var new_order_data = [];
            if(customer_id != undefined){
                for(var i=0; i<order.length; i++){
                    if(order[i].partner_id[0] == customer_id)
                        new_order_data = new_order_data.concat(order[i]);
                }
                order = new_order_data;
            }
            if (input_txt != undefined && input_txt != '') {
                var new_order_data = [];
                var search_text = input_txt.toLowerCase()
                for (var i = 0; i < order.length; i++) {
                    if (order[i].partner_id == '') {
                        order[i].partner_id = [0, '-'];
                    }
                    if (((order[i].name.toLowerCase()).indexOf(search_text) != -1) || ((order[i].partner_id[1].toLowerCase()).indexOf(search_text) != -1)) {
                        new_order_data = new_order_data.concat(order[i]);
                    }
                }
                order = new_order_data;
            }
            var contents = $('div.clientlist-screen.screen')[0].querySelector('.wk-order-list-contents');
            contents.innerHTML = "";
            var wk_orders = order;
            for (var i = 0, len = Math.min(wk_orders.length, 1000); i < len; i++) {
                var wk_order = wk_orders[i];
                var orderline_html = QWeb.render('WkOrderLine', {
                    widget: this,
                    order: wk_orders[i],
                    customer_id:wk_orders[i].partner_id[0],
                });
                var orderline = document.createElement('tbody');
                orderline.innerHTML = orderline_html;
                orderline = orderline.childNodes[1];
                contents.appendChild(orderline);
            }
		}
        constructor() {
            super(...arguments);
			var self = this;
			setTimeout(function(){
                var orders = self.env.pos.db.pos_all_orders;
                self.render_list(orders, undefined);
            }, 150);
        }
        keyup_order_search(event){
            var orders = this.env.pos.db.pos_all_orders;
            this.render_list(orders, event.target.value);
        }
        clickBack(event){
            if(this.props.isShown){
                this.showScreen('ProductScreen');
            }
            else{
                this.showTempScreen('ClientListScreen', { });
            }
        }
    }
    OrdersScreenWidget.template = 'OrdersScreenWidget';
	Registries.Component.add(OrdersScreenWidget);

    // AllOrdersButton Popup
	class AllOrdersButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        async onClick() {
            var self = this;
			self.showScreen('OrdersScreenWidget',{});
        }
    }
    AllOrdersButton.template = 'AllOrdersButton';
    ProductScreen.addControlButton({ component: AllOrdersButton, condition: function() { return true; },});
	Registries.Component.add(AllOrdersButton);
    
    // Inherit ClientLine-------------
    const PosResClientLine = (ClientLine) =>
        class extends ClientLine{
            click_all_orders(event){
                this.showTempScreen('OrdersScreenWidget',{
                    'customer_id':this.props.partner.id
                });
            }
        }
    Registries.Component.extend(ClientLine, PosResClientLine);

    return OrdersScreenWidget;
});
