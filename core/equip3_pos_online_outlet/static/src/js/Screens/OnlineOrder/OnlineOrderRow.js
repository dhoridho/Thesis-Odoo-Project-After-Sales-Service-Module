odoo.define('equip3_pos_online_outlet.OnlineOrderRow', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const field_utils = require('web.field_utils');
    const {useState} = owl.hooks;

    class OnlineOrderRow extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({
                refresh: 'done',
            });
        }

        async updateOrder(order, values){
            let orders = this.env.pos.db.get_online_orders();
            for (var i = orders.length - 1; i >= 0; i--) {
                if(orders[i].id == order.id){
                    for(let key in values){
                        orders[i][key] = values[key];
                    }
                    break;
                }
            }
            this.env.pos.db.save_online_orders(orders);
        }
        
        resetBackStatus(order){
            this.updateOrder(order, {
                'manual_action': '',
                'status': 'NEW',
                'state': 'new',
            });
        }
        resetMarkOrderReady(order){
            this.updateOrder(order, {
                'is_mark_order_ready': false
            });
        }
        
        async actionAcceptOrder(order) {
            //accept online order
        }

        async actionRejectOrder(order){
            //reject online order
        }

        async actionCreateOrder(order){
            //create order session
        }
        
        async createOrder(order){
            //create order session data
        }

        async actionChangeReadyTime(order){
            //change estimation ready time
        }

        async actionMarkOrderReady(order){
            //mark order ready
        }

        is_show_pay_button(order){
            let is_show = false;
            if(['to pay'].includes(order.state) == true && order.has_pos_order == false){
                is_show = true;

                if(order.order_from == 'grabfood'){
                    if(!['Driver Arrived', 'Order Collected', 'On Delivery'].includes(order.online_state)){
                        is_show = false;
                    }
                }
            }
            return is_show;
        }

        is_show_mark_ready_button(order){
            let hidden_status = ['', 'Driver Arrived', 'Order Collected', 'On Delivery', 'Failed', 'Cancelled'];
            let is_show = true;
            if(order){
                if(hidden_status.includes(order.online_state)){
                    is_show = false;
                }
                if(order.is_mark_order_ready){
                    is_show = false;
                }
                return is_show;
            }
            return false;
        }

        is_show_change_ready_time_button(order){
            let hidden_status = ['', 'Driver Arrived', 'Order Collected', 'On Delivery', 'Failed', 'Cancelled'];
            let is_show = true;
            if(order){
                if(hidden_status.includes(order.online_state)){
                    is_show = false;
                }
                if(order.is_mark_order_ready){
                    is_show = false;
                }
                return is_show;
            }
            return false;
        }

        async _autoSyncBackend() {
            if(this.props.order){
                this.state.refresh = 'connecting';
                let _object = this.env.pos.get_model('pos.online.outlet.order');
                let fields = _object.fields; 
                let orders = await this.rpc({
                    model: 'pos.online.outlet.order',
                    method: 'search_read',
                    fields: fields,
                    args: [[['id', '=', this.props.order.id]]]
                })
                this.state.refresh = 'done';
                this.props.order = orders[0];
                this.render();
            }
        }
        getOnlineOrderLines(onlineOrder){
            let lines = [];
            for(let id of onlineOrder.line_ids){
                lines.push(this.env.pos.db.online_order_line_by_id[id]);
            }
            return lines.sort((a, b) => a.sequence - b.sequence);
        }
        get getHighlight() {
            return this.props.order !== this.props.selectedOrder ? '' : 'highlight';
        }

        getDate(date){
            return field_utils.format.datetime(field_utils.parse.datetime(date));
        }
        
        getOrderFrom(val){
            if(val == 'grabfood'){
                return 'GrabFood';
            }
            if(val == 'gofood'){
                return 'GoFood';
            }
            return val;
        }

        getOrderType(val){
            if(val == 'self-pickup'){
                return 'Self-pickup'; //Pickup/TakeAway/Self-Collection
            }
            if(val == 'grab-delivery'){
                return 'Grab delivery';
            }
            if(val == 'outlet-delivery'){
                return 'Outlet delivery';
            }
            if(val == 'dine-in'){
                return 'Dine-in';
            }
            return val;
        }

        async clearOrderCart() {
            if(this.env.pos.selected_order_method != 'online-order'){
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
    }

    OnlineOrderRow.template = 'OnlineOrderRow';
    Registries.Component.add(OnlineOrderRow);
    return OnlineOrderRow;
});
