odoo.define('equip3_pos_online_outlet.Database', function (require) {
    'use strict';

    var PosDB = require('point_of_sale.DB'); 
    var _super_init_ = PosDB.prototype.init;
    const _super_db = PosDB.prototype;
    
    PosDB.prototype.init = function(options) {
        _super_init_.call(this, options);
        this.online_outlet = {};
        // TODO: stored online outlet order
        this.online_order_by_id = {};
        this.online_order_string = '';
        this.online_order_string_by_id = {};
        this.online_order_search_string_by_id = {};
        this.online_order_line_by_id = {};
    };
    
    PosDB.include({
        save_online_outlet: function (outlet) {
            this.online_outlet = outlet;
        },
        get_online_outlet: function () {
            return this.online_outlet;
        },

        _online_orders_search_string: function (order) {
            let str = order.order_number;
            if(order.customer_name){
                str += '|' + order.grabfood;
            }
            str = '' + order['id'] + ':' + str.replace(':', '') + '\n';
            return str;
        },

        save_online_orders: function (orders) {
            for (let i = 0; i < orders.length; i++) {
                let order = orders[i];
                let label = this._online_orders_search_string(order);
                this.online_order_by_id[order.id] = order;
                this.online_order_string_by_id[order.id] = label;
                this.online_order_search_string_by_id[order.id] = label;
            }
            for (let order_id in this.online_order_search_string_by_id) {
                this.online_order_string += this.online_order_search_string_by_id[order_id];
            }
        },

        save_online_orders_lines: function (orders_lines) {
            for (let i = 0; i < orders_lines.length; i++) {
                this.online_order_line_by_id[orders_lines[i].id] = orders_lines[i];
            } 
        },
        
        get_online_orders: function (max_count) {
            let orders = [];
            let max = 0;
            for (let order_id in this.online_order_by_id) {
                let order = this.online_order_by_id[order_id];
                orders.push(order);
                max += 1;
                if (max_count > 0 && max >= max_count) {
                    break;
                }
            }
            return orders;
        },
        search_online_orders: function (query) {
            query = query.replace(/[\[\]\(\)\+\*\?\.\-\!\&\^\$\|\~\_\{\}\:\,\\\/]/g, '.');
            query = query.replace(' ', '.+');
            const re = RegExp("([0-9]+):.*?" + query, "gi");
            let orders = [];
            let order_ids = [];
            for (let i = 0; i < this.limit; i++) {
                let r = re.exec(this.online_order_string);
                if (r && r[1]) {
                    let id = r[1];
                    if (this.online_order_by_id[id] !== undefined && !order_ids.includes(id)) {
                        orders.push(this.online_order_by_id[id]);
                        order_ids.push(id);
                    }
                } else {
                    break;
                }
            }
            return orders;
        },
    });
});