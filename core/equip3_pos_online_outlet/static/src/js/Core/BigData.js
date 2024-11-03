odoo.define('equip3_pos_online_outlet.BigData', function (require) {
    'use strict';

    const models = require('point_of_sale.models');
    const field_utils = require('web.field_utils');
    const core = require('web.core');
    const _t = core._t;
    var SuperOrder = models.Order;

    models.load_fields('pos.order', ['is_online_outlet', 'oloutlet_order_id', 'oloutlet_order_from', 'oloutlet_order_type', 'oloutlet_order_info']);

    models.Order = models.Order.extend({
        initialize: function(attributes, options) {
            var self = this; 
            self.is_online_outlet = false;
            self.oloutlet_order_id = false;
            self.oloutlet_order_from = false;
            self.oloutlet_order_info = false;
            self.oloutlet_order_type = false;
            self.has_pos_order = false
            SuperOrder.prototype.initialize.call(this, attributes, options);
        },

        init_from_JSON: function (json) { 
            let res = SuperOrder.prototype.init_from_JSON.apply(this, arguments);
            if (json.is_online_outlet) {
                this.is_online_outlet = json.is_online_outlet;
            }
            if (json.return_status) {
                this.return_status = json.return_status;
            }
            if (json.oloutlet_order_id) {
                this.oloutlet_order_id = json.oloutlet_order_id;
            }
            if (json.has_pos_order) {
                this.has_pos_order = json.has_pos_order;
            }
            return res;
        },
        export_as_JSON: function() {
            var self = this;
            var loaded = SuperOrder.prototype.export_as_JSON.call(this);
            var current_order = self.pos.get_order();
            if (self.pos.get_order() != null) {
                loaded.is_online_outlet = current_order.is_online_outlet;
                loaded.return_status = current_order.return_status;
                loaded.oloutlet_order_id = current_order.oloutlet_order_id;
                loaded.has_pos_order = current_order.has_pos_order;
            }
            return loaded;
        },
        save_to_db: function() {
            var res = SuperOrder.prototype.save_to_db.call(this);
            return res;
        }
    });

    models.load_models([
        {
            model: 'pos.online.outlet',
            fields: ['id', 'name','state'],
            domain: function(self) {
                let domain = [['id','=',-1]]; 
                let online_outlet_id = self.config.online_outlet_id;
                if(typeof online_outlet_id != undefined && online_outlet_id != false){
                    domain = [['id','=',self.config.online_outlet_id[0]]]
                }
                return domain;
            },
            context: function (self) {
                return { }
            },
            loaded: function (self, outlet) {
                let online_outlet = {}
                if(outlet){
                    online_outlet = outlet[0];
                }
                self.saveOnlineOutlet(online_outlet);
            },
        }, 
        {
            model: 'pos.online.outlet.order',
            fields: [
                'id', 'online_outlet_id','order_number','order_from','order_type','state','status','online_state','order_date','amount_total','is_mark_order_ready',
                'order_ready_est_allow_change','order_ready_est_time','order_ready_est_max_time','order_ready_new_est_time','order_ready_est_time_display',
                'currency_id','manual_action','line_ids','has_pos_order','payment_type', 'info'],
            domain: function(self) {
                let domain = [['id','=',-1]]; 
                let online_outlet_id = self.config.online_outlet_id;
                if(typeof online_outlet_id != undefined && online_outlet_id != false){
                    domain = [['online_outlet_id','=',self.config.online_outlet_id[0]]]
                }
                return domain;
            },
            context: function (self) {
                return { }
            },
            loaded: function (self, orders) {
                self.saveOnlineOrders(orders)
            },
        }, 
        {
            model: 'pos.online.outlet.order.line',
            fields: ['order_id', 'id', 'product_id', 'product_tmpl_id', 'qty', 'price', 'subtotal', 'note', 
                'is_delivery', 'is_main_product', 'is_option_product', 'sequence'],
            domain: function(self) {
                let domain = [['id','=',-1]];
                let online_outlet_id = self.config.online_outlet_id;
                if(typeof online_outlet_id != undefined && online_outlet_id != false){
                    domain = [['order_id.online_outlet_id','=',self.config.online_outlet_id[0]]]
                }
            },
            context: function (self) {
                return { }
            },
            loaded: function (self, order_lines) {
                self.saveOnlineOrdersLines(order_lines)
            },
        }, 
    ], {'after': 'product.product'});

    const _super_PosModel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        initialize: async function (session, attributes) {
            if (attributes && attributes.chrome) {
                this.chrome = attributes.chrome
            }
            let self = this;
            _super_PosModel.initialize.call(this, session, attributes);
        },

        saveOnlineOutlet(outlet) { 
            this.db.save_online_outlet(outlet);
        },

        saveOnlineOrders(orders) { 
            for (let i = 0; i < orders.length; i++) {
                let order = orders[i];
                // order.order_date = field_utils.format.datetime(field_utils.parse.datetime(order.order_date));
            } 
            this.db.save_online_orders(orders);
        },

        async getOnlineOrders() {
            let self = this;
            let domain = [['id','=',-1]]; 
            let online_outlet_id = self.config.online_outlet_id;
            if(typeof online_outlet_id != undefined && online_outlet_id != false){
                domain = [['online_outlet_id','=',self.config.online_outlet_id[0]]]
            }
            let model = self.get_model('pos.online.outlet.order');
            let params = {
                model: 'pos.online.outlet.order',
                fields: model.fields,
                domain: domain,
                context: {
                    ctx_limit: 20,
                    ctx_order_by: 'write_date desc'
                }
            }

            let orders = await this.getDatasByModel(params['model'], params['domain'], params['fields'], params['context']);
            await this.getOnlineOrdersLines(orders);
            this.saveOnlineOrders(orders);

            this.alert_message({
                title: _t('Syncing'),
                body: _t('Online Orders')
            })
        },
        async getOnlineOrdersLines(orders=[]) {
            let self = this;
            let orders_ids = [];
            let domain = [['id','=',-1]];
            let online_outlet_id = self.config.online_outlet_id;
            if(typeof online_outlet_id != undefined && online_outlet_id != false){
                domain = [['order_id.online_outlet_id','=',self.config.online_outlet_id[0]]]
            }
            if(orders.length){
                domain.push(['order_id','in', orders.map((o)=>o.id)]);
            }
            let model = self.get_model('pos.online.outlet.order.line');
            let params = {  
                model: 'pos.online.outlet.order.line',
                fields: model.fields,
                domain: domain,
                context: {}
            }
            let orders_lines = await this.getDatasByModel(params['model'], params['domain'], params['fields'], params['context']);
            this.saveOnlineOrdersLines(orders_lines);
        },

        saveOnlineOrdersLines(orders_lines) {
            this.db.save_online_orders_lines(orders_lines);
        },

        async getOnlineOutlet() {
            let self = this; 
            let model = self.get_model('pos.online.outlet');
            let domain = [['id','=',-1]]; 
            let online_outlet_id = self.config.online_outlet_id;
            if(typeof online_outlet_id != undefined && online_outlet_id != false){
                domain = [['id','=',self.config.online_outlet_id[0]]]
            }
            let params = {
                model: 'pos.online.outlet',
                fields: model.fields,
                domain: domain,
                context: { }
            }
            let online_outlets = await this.getDatasByModel(params['model'], params['domain'], params['fields'], params['context']);
            if(online_outlets){
                self.saveOnlineOutlet(online_outlets[0]);
            }
        },
    });
    
});
