odoo.define('equip3_pos_general_contd.Database', function (require) {
    'use strict';

    const PosDB = require('point_of_sale.DB');
    const Session = require('web.Session');
    const _super_init_ = PosDB.prototype.init;
    const _super_db = PosDB.prototype;
    
    PosDB.prototype.init = function(options) {
        _super_init_.call(this, options);

        // TODO: stored order history local storage
        this.order_history_local_is_loaded = false;
        this.order_history_local_ids = [];
        this.order_history_localby_id = {}; // generated ID for unique
        this.order_history_local_by_name = {};
        this.order_history_local_string = '';
        this.order_history_local_search_stringby_id = {};

        // TODO: Store ID to avoid multiple push data
        this.order_history_local_pos_cache_ids = [];
    };
    
    PosDB.include({

        _order_history_local_search_string: function (order) {
            let str = order.name;
            if (order.sync_sequence_number) {
                str += '|' + order.sync_sequence_number;
            }
            if (order.origin) {
                str += '|' + order.origin;
            }
            if (order.creation_date) {
                str += '|' + order.creation_date;
            }
            if (order.ean13) {
                str += '|' + order.ean13;
            }
            if (order.note) {
                str += '|' + order.note;
            }
            if (order.user_id) {
                str += '|' + order.user_id[1];
            }
            if (order.partner_id) {
                if(this.partner_by_id){
                    let partner = this.partner_by_id[order.partner_id];
                    if (partner) {
                        if (partner.name) {
                            str += '|' + partner.name;
                        }
                    }
                }
            }

            str = '' + order.id + ':' + str.replace(':', '') + '\n';
            return str;
        },

        get_order_history_local_unique_id: function (order) {
            //TODO: combine uid and creation date to avoid duplication
            let uid = order.uid.replaceAll('-','');
            return uid + moment(order.creation_date).format('YYYYMMDDhhmmss');
        },

        save_order_history_local: function (orders) {
            for (let i = 0; i < orders.length; i++) {
                let order = orders[i];
                let label = this._order_history_local_search_string(order);

                this.order_history_local_ids.push(order.id);
                this.order_history_localby_id[order.id] = order;
                this.order_history_local_by_name[order.name] = order;
                this.order_history_local_search_stringby_id[order.id] = label;
            }
            for (let _id in this.order_history_local_search_stringby_id) {
                this.order_history_local_string += this.order_history_local_search_stringby_id[_id];
            }
        },

        get_order_history_local: function(max_count){
            let orders = [];
            let max = 0;
            for (let res_id in this.order_history_localby_id) {
                let order = this.order_history_localby_id[res_id];
                orders.push(order);
                max += 1;
                if (max_count > 0 && max >= max_count) {
                    break;
                }
            }
            return orders;
        },
        get_order_history_local_by_name: function(name){
            let order_log = this.order_history_local_by_name[name];
            if (order_log) {
                return order_log;
            }
            return false;
        },

        search_order_history_local: function(query){
            query = query.replace(/[\[\]\(\)\+\*\?\.\-\!\&\^\$\|\~\_\{\}\:\,\\\/]/g, '.');
            query = query.replace(' ', '.+');
            const re = RegExp("([0-9]+):.*?" + query, "gi");
            let orders = [];
            let order_ids = [];
            for (let i = 0; i < this.limit; i++) {
                let r = re.exec(this.order_history_local_string);
                if (r && r[1]) {
                    let id = r[1];
                    if (this.order_history_localby_id[id] !== undefined && !order_ids.includes(id)) {
                        orders.push(this.order_history_localby_id[id]);
                        order_ids.push(id);
                    }
                } else {
                    break;
                }
            }
            return orders;
        }

    });
});