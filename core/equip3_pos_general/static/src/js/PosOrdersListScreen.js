/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */
odoo.define('equip3_pos_general.pos_orders_list_screen',function(require){
    "use strict"
    var core = require('web.core');
    var QWeb = core.qweb;
    const Registries = require('point_of_sale.Registries');
    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const ClientLine = require('point_of_sale.ClientLine');
	const { useListener } = require('web.custom_hooks');

    class POSOrdersScreenWidget extends PosComponent {
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
            for (var i = 0, len = Math.min(order.length, 1000); i < len; i++) {
                var wk_order = order[i];
                var orderline_html = QWeb.render('POSOrderLineScreen', {
                    widget: this,
                    order: order[i],
                    customer_id:order[i].partner_id[0],
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
    POSOrdersScreenWidget.template = 'POSOrdersScreenWidget';
	Registries.Component.add(POSOrdersScreenWidget);

    // AllOrdersButton Popup
	class POSAllOrdersButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        async onClick() {
            var self = this;
			self.showScreen('POSOrdersScreenWidget',{});
        }
    }
    POSAllOrdersButton.template = 'POSAllOrdersButton';
    ProductScreen.addControlButton({ component: POSAllOrdersButton, condition: function() { return true; },});
	Registries.Component.add(POSAllOrdersButton);
    
    // Inherit ClientLine-------------
    const POSOrdersClientLine = (ClientLine) =>
        class extends ClientLine{
            click_all_orders(event){
                this.showTempScreen('POSOrdersScreenWidget',{
                    'customer_id':this.props.partner.id
                });
            }
        }
    Registries.Component.extend(ClientLine, POSOrdersClientLine);

    return POSOrdersScreenWidget;
});
