odoo.define('equip3_pos_general_contd.BigData', function (require) {
    'use strict';

    var PosOrderDetail = require('equip3_pos_masterdata.PosOrderDetail');
    var Orderline = require('point_of_sale.Orderline');
    var models = require('point_of_sale.models');
    const big_data = require('equip3_pos_masterdata.big_data');
    var SuperOrder = models.Order.prototype;
    var SuperOrderline = models.Orderline.prototype;
    const indexedDBContd = require('equip3_pos_general_contd.indexedDBContd');


    const _super_PosModel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        initialize: async function (session, attributes) {
            _super_PosModel.initialize.call(this, session, attributes);
        }
    });

    models.Order = models.Order.extend({
        initialize: function(attributes, options) {
            this.is_exchange_order = false;
            this.exchange_amount = 0;
            this.is_return_order = false;
            this.return_status = '';
            this.return_order_id = false;

            SuperOrder.initialize.call(this, attributes, options);
        },
        init_from_JSON: function (json) {
            SuperOrder.init_from_JSON.apply(this, arguments);
            
            if (json.is_exchange_order) {
                this.is_exchange_order = json.is_exchange_order;
            }
            if (json.exchange_amount) {
                this.exchange_amount = json.exchange_amount;
            }
            if (json.is_return_order) {
                this.is_return_order = json.is_return_order;
            }
            if (json.return_status) {
                this.return_status = json.return_status;
            }
            if (json.return_order_id) {
                this.return_order_id = json.return_order_id;
            }
        },
        export_as_JSON: function() {
            var json = SuperOrder.export_as_JSON.call(this);
            var current_order = this.pos.get_order();
            if (current_order != null) {
                json.is_exchange_order = current_order.is_exchange_order;
                json.exchange_amount = current_order.exchange_amount;
                json.is_return_order = current_order.is_return_order;
                json.return_status = current_order.return_status;
                json.return_order_id = current_order.return_order_id;
            }
            return json;
        },
    });

    models.Orderline = models.Orderline.extend({ 
        initialize: function(attr, options) {
            this.line_qty_returned = 0;
            this.original_line_id = null;
            this.is_product_exchange = false;
            
            SuperOrderline.initialize.call(this, attr, options);
        },
        export_as_JSON: function() {
            var self = this;
            var loaded = SuperOrderline.export_as_JSON.call(this);
            loaded.line_qty_returned = self.line_qty_returned;
            loaded.original_line_id = self.original_line_id;
            loaded.is_product_exchange = self.is_product_exchange;
            return loaded;
        },
        can_be_merged_with: function(orderline) {
            var self = this;
            if (self.pos.get_order() && self.pos.get_order().is_return_order && self.quantity < 0)
                return false;
            else
                return SuperOrderline.can_be_merged_with.call(this, orderline);
        }
    });

    models.load_fields('pos.order', ['exchange_amount', 'is_exchange_order']);

    models.load_fields('pos.order.line', ['is_product_exchange', 'product_exchange_price','is_fee_of_product_exchange']);

    models.load_models([
        {
            label: 'Load Local Order Log from Local Storage',
            installed: true,
            condition: function(self){
                return self.config.is_save_order_history_local;
            },
            loaded: async function (self) {
                await self.indexedDBContd.get_datas('order.history', 1);
                let orders = self.indexedDBContd.data_by_model['order.history'];
                if(!orders){
                    orders = [];
                }

                let limit_saving_date = moment().subtract(self.config.save_order_history_local_days, 'days');

                let delete_orders = orders.filter((o)=> moment(o.creation_date).isAfter(limit_saving_date) == false);
                for (let i = 0; i < delete_orders.length; i++) {
                    self.indexedDBContd.unlink('order.history', delete_orders[i]);
                }

                let load_orders = orders.filter((o)=> moment(o.creation_date).isAfter(limit_saving_date) == true);
                if(load_orders.length){
                    await self.db.save_order_history_local(load_orders);
                }
                
                console.warn("Load Local Order Log from indexedDB:", load_orders.length);
                console.warn("Delete Local Order Log from indexedDB:", delete_orders.length);
            }
        },
    ], {
        after: 'pos.payment.method'
    });

});