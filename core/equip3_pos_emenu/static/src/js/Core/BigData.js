odoo.define('equip3_pos_emenu.BigData', function (require) {
    'use strict';

    const models = require('point_of_sale.models');
    const core = require('web.core');
    const {Gui} = require('point_of_sale.Gui');
    const _t = core._t;
    var SuperOrder = models.Order;
    var SuperOrderline = models.Orderline;

    models.load_fields('pos.order', ['is_emenu_order', 'emenu_order_id']);

    models.Order = models.Order.extend({
        initialize: function(attributes, options) {
            this.is_emenu_order = false;
            this.emenu_order_id = false;
            this.emenu_status = false;
            SuperOrder.prototype.initialize.call(this, attributes, options);
        },

        init_from_JSON: function (json) { 
            SuperOrder.prototype.init_from_JSON.apply(this, arguments);
            if (json.is_emenu_order) {
                this.is_emenu_order = json.is_emenu_order;
            }
            if (json.emenu_order_id) {
                this.emenu_order_id = json.emenu_order_id;
            }
            if (json.emenu_status) {
                this.emenu_status = json.emenu_status;
            }
        },

        export_as_JSON: function () {
            var json = SuperOrder.prototype.export_as_JSON.call(this);
            if (this.is_emenu_order) {
                json.is_emenu_order = this.is_emenu_order;
            }
            if (this.emenu_order_id) {
                json.emenu_order_id = this.emenu_order_id;
            }
            if (this.emenu_status) {
                json.emenu_status = this.emenu_status;
            }
            return json;
        },
        
        save_to_db: function() {
            var res = SuperOrder.prototype.save_to_db.call(this);
            return res;
        },
    });


    models.Orderline = models.Orderline.extend({
        initialize: function (attributes, options) {
            let res = SuperOrderline.prototype.initialize.apply(this, arguments);
            if (!options.json) {
                this.emenu_status = '';
                this.emenu_order_number = '';
                this.emenu_order_line_id = '';
            }
            return res;
        }, 

        init_from_JSON: function (json) {
            SuperOrderline.prototype.init_from_JSON.apply(this, arguments);
            if (json.emenu_status) {
                this.emenu_status = json.emenu_status;
            }
            if (json.emenu_order_number) {
                this.emenu_order_number = json.emenu_order_number;
            }
            if (json.emenu_order_line_id) {
                this.emenu_order_line_id = json.emenu_order_line_id;
            }
        },

        export_as_JSON: function () {
            let json = SuperOrderline.prototype.export_as_JSON.apply(this, arguments);
            if (this.emenu_status) {
                json.emenu_status = this.emenu_status;
            }
            if (this.emenu_order_number) {
                json.emenu_order_number = this.emenu_order_number;
            }
            if (this.emenu_order_line_id) {
                json.emenu_order_line_id = this.emenu_order_line_id;
            }
            return json;
        },

    });

    const _super_PosModel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        initialize: async function (session, attributes) {
            if (attributes && attributes.chrome) {
                this.chrome = attributes.chrome
            }
            let self = this;
            _super_PosModel.initialize.call(this, session, attributes);
        },

        sync_emenu_orders: async function(){
            let self = this;
            let order_uids = [];
            this.env.pos.get('orders').models.forEach(function (order) {
                order_uids.push(order.uid);
            });

            let results = await this.rpc({
                model: 'pos.emenu.order', 
                method: 'sync_emenu_orders', 
                args: [[], { order_uids: order_uids }]
            }, {
                shadow: true,
                timeout: 75000
            }).then(function (response) {
                return response;
            }, function (error) {
                if (error && error.message && error.message.code == -32098) {
                    console.error('[sync_emenu_order] ~ Server Offline')
                } else {
                    console.error('[sync_emenu_order] ~ Error 403')
                }
                self.env.pos.alert_message({
                    title: self.env._t('Warning'),
                    body: self.env._t('Failed,Sync E-Menu Order please try again.'),
                })
                return Promise.reject(error);
            });

            _.each(results, function(result){
                let order = self.get_order_by_uid(result.order_session_uid);
                if(order){
                    order.emenu_status = result.state;
                    if (result.lines){
                        let emenu_order_line_ids = [];
                        order.get_orderlines().forEach(function (orderline) {
                            emenu_order_line_ids.push(orderline.emenu_order_line_id);
                        });

                        let notfound_products = [];
                        _.each(result.lines, function(line){
                            if (!emenu_order_line_ids.includes(line.id)){
                                let product = self.db.get_product_by_id(line.product_id[0]);
                                if(product){
                                    order.add_product(product, {
                                        quantity: line.qty,
                                        merge: false,
                                        extras: {
                                            emenu_status: line.state,
                                            emenu_order_number: line.order_number,
                                            emenu_order_line_id: line.id,
                                        }
                                    });
                                }else{
                                    notfound_products.push(line.product_id[1]);
                                }
                            }
                        });

                        if(notfound_products.length){
                            console.error('[sync_emenu_orders] Product not found:', notfound_products);
                            Gui.showPopup('ErrorPopup', {
                                title: self.env._t('Warning'),
                                body: self.env._t('Product is not found, please sync masterdata products. ') + '['+ notfound_products.slice(0,4).join() +']',
                            });
                        }

                    }
                }
            });

        },

        sync_emenu_order: async function(selectedOrder){
            let self = this;
            let result = await this.rpc({
                model: 'pos.emenu.order', 
                method: 'sync_emenu_order', 
                args: [[selectedOrder.emenu_order_id]]
            }, {
                shadow: true,
                timeout: 75000
            }).then(function (response) {
                return response;
            }, function (error) {
                if (error && error.message && error.message.code == -32098) {
                    console.error('[sync_emenu_order] ~ Server Offline')
                } else {
                    console.error('[sync_emenu_order] ~ Error 403')
                }
                self.env.pos.alert_message({
                    title: self.env._t('Warning'),
                    body: self.env._t('Failed,Sync E-Menu Order please try again.'),
                })
                return Promise.reject(error);
            });

            selectedOrder.emenu_status = result.order.state;
            if(selectedOrder.emenu_status){
                $('.o_action_manager .pos').attr('data-emenu-status', selectedOrder.emenu_status);
            }

            if (result.lines){
                let emenu_order_line_ids = [];
                selectedOrder.get_orderlines().forEach(function (orderline) {
                    emenu_order_line_ids.push(orderline.emenu_order_line_id);
                });

                let notfound_products = [];
                _.each(result.lines, function(line){
                    if (!emenu_order_line_ids.includes(line.id)){
                        let product = self.db.get_product_by_id(line.product_id[0]);
                        if(product){
                            selectedOrder.add_product(product, {
                                quantity: line.qty,
                                merge: false,
                                extras: {
                                    emenu_status: line.state,
                                    emenu_order_number: line.order_number,
                                    emenu_order_line_id: line.id,
                                }
                            });
                        }else{
                            notfound_products.push(line.product_id[1]);
                        }
                    }
                });

                if(notfound_products.length){
                    console.error('[sync_emenu_order] Product not found:', notfound_products);
                    return Gui.showPopup('ErrorPopup', {
                        title: self.env._t('Warning'),
                        body: self.env._t('Product is not found, please sync masterdata products. ') + '['+ notfound_products.slice(0,4).join() +']',
                    });
                }

            }
        },

        emenu_save_cashier_changes: async function(order){
            let self = this;
            let changes = order.computeChanges();
            if(!changes.new.length){
                return Promise.resolve(false);
            }
            let values = { lines: [] };
            
            for (let data of changes.new){
                values.lines.push({
                    'product_id': data.product_id,
                    'qty': data.qty,
                    'note': data.note,
                    'order_type': 'dine-in',
                });
            }

            let result = await this.rpc({
                model: 'pos.emenu.order', 
                method: 'action_save_cashier_changes', 
                args: [[order.emenu_order_id], values]
            }, {
                shadow: true,
                timeout: 75000
            }).then(function (response) {
                return response;
            }, function (error) {
                if (error && error.message && error.message.code == -32098) {
                    console.error('[action_save_cashier_changes] ~ Server Offline')
                } else {
                    console.error('[action_save_cashier_changes] ~ Error 403')
                }
                self.env.pos.alert_message({
                    title: self.env._t('Warning'),
                    body: self.env._t('Failed, Sync Cashier changes please try again.'),
                })
                return Promise.reject(error);
            });
            return Promise.resolve(result);
        }

    });
    
    
});