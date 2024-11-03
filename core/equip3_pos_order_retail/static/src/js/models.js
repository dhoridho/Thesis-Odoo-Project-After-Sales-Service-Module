odoo.define('equip3_pos_order_retail.models', function (require) {
    'use strict';
    var rpc = require('pos.rpc');
    var models = require('point_of_sale.models');
    var pos_re_models = require('pos_retail.load_models');
    var pos_retails_order = require('pos_retail.order');
    var core = require('web.core');
    var _super_orderline = models.Orderline.prototype;
    var _super_pos_model = models.PosModel.prototype;

    models.load_models({
        model: 'combo.option.item',
        fields: ['combo_option_id','product_id', 'extra_price', 'product_variant_id'],
        loaded: function(self,pos_combo_items){
            self.db.add_pos_combo_items(pos_combo_items);
        },
    });

    models.load_models({
        model: 'combo.option',
        fields: ['combo_name','item_ids'],
        loaded: function(self,pos_combo_ids){
            self.db.add_pos_combo(pos_combo_ids);
        },
    })
    models.load_fields('product.template', ['is_combo_product', 'combo_option_id', 'combo_option_items']);
    models.load_fields('product.product', ['is_combo_product', 'combo_option_id', 'combo_option_items']);
    models.load_fields('restaurant.table', ['customer_name', 'date_reserve']);
    models.load_fields("pos.promotion", ['is_stack', 'card_payment_id']);
    models.load_fields("pos.config", ['is_complementary', 'required_ask_seat']);
    models.PosModel = models.PosModel.extend({
        initialize: function(attributes) {
            _super_pos_model.initialize.apply(this,arguments);
            this.r_customer_name = '';
            this.table_reserve_date = '';
            this.clear_interval = '';
        },
        async unlock_table() {
            var self = this;
            let resultUnLock = await rpc.query({
                model: 'restaurant.table',
                method: 'lock_table',
                args: [[this.table_click.id], {
                    'locked': false,
                    'customer_name': '',
                    'date_reserve': false
                }],
            }, {
                timeout: 30000,
                shadow: true,
            })
            if (resultUnLock) {
                this.table_click['locked'] = false;
                const table = this.tables.find(t => t.id == this.table_click.id)
                table.locked = false;
                this.set_table(this.table_click);
                var orders = this.get('orders').models;
                const order_of_table = orders.find(o => o.table && o.table.id == table.id)
                if (self.pos_bus && order_of_table) {
                    self.pos_bus.send_notification({
                        data: {
                            order: order_of_table.export_as_JSON(),
                            table_id: order_of_table.table.id,
                            order_uid: order_of_table.uid,
                            lock: false,
                            customer_name: '',
                            date_reserve: false
                        },
                        action: 'lock_table',
                        order_uid: order_of_table.uid,
                    })
                }
            }
        },
    });
    models.Orderline = models.Orderline.extend({
        initialize: function(attr,options) {
            _super_orderline.initialize.apply(this,arguments);
            if(options && options.json && options.json.item_state == 'cancelled'){
                this.item_state = 'cancelled';    
            }else{
                this.item_state = 'ordered';
            }
            this.is_complementary = this.is_complementary || false; 
            this.required_ask_seat = this.required_ask_seat || '';
        },
        set_is_complementary:function(is_complementary){
            this.is_complementary = is_complementary;
        }, 
        get_is_complementary: function(){
            return this.is_complementary;
        },
        set_required_ask_seat:function(required_ask_seat){
            this.required_ask_seat = required_ask_seat;
            this.trigger('change');
        }, 
        get_required_ask_seat: function(){
            return this.required_ask_seat;
        },
        get_item_state: function(){
            return this.item_state;
        },
        set_item_state: function(item_state){
            this.item_state = item_state;
            this.trigger('change');
        },
        init_from_JSON: function(json) {
            _super_orderline.init_from_JSON.apply(this, arguments);
            this.set_item_state(json.item_state);
            this.set_required_ask_seat(json.required_ask_seat);
        },
        export_as_JSON: function() {
            var res = _super_orderline.export_as_JSON.apply(this, arguments);
            res['item_state'] = this.get_item_state();
            if(this.get_item_state() == 'cancelled' && this.get_quantity() != 0){
                this.set_quantity(0);
            }
            res['required_ask_seat'] = this.get_required_ask_seat();
            return res;
        },
        export_for_printing: function(){
            var res = _super_orderline.export_for_printing.apply(this, arguments);
            res['item_state'] = this.get_item_state();
            res['required_ask_seat'] = this.get_required_ask_seat();
            return res;
        }
    });

    var _super_order = models.Order.prototype;
    models.Order = models.Order.extend({
        getOrderReceiptEnv: function() {
            var res = _super_order.getOrderReceiptEnv.apply(this, arguments);
            res['orderlines'] = res.orderlines.filter((line)=>{return line.item_state == 'ordered'});
            return res;
        },
        export_for_printing: function(){
            var receipt = _super_order.export_for_printing.apply(this, arguments);
            if(receipt && receipt.orderlines && receipt.orderlines.length){
                receipt['orderlines'] = receipt.orderlines.filter((line)=>{return line.item_state == 'ordered'});
            }
            return receipt;
        },
        get_promotions_active: function () {
            var res = _super_order.get_promotions_active.apply(this, arguments);
            if(res && res['promotions_active'] && res['promotions_active'].length){
                var prmos = res['promotions_active'];
                var prmos = res['promotions_active'].filter(prm => {
                    return !prm.card_payment_id || prm.card_payment_id[0] == this.get_selected_card_payment_id();
                });
                var flag = false;
                var stb = prmos.filter(prm => {
                    if(!prm.is_stack && prmos.indexOf(prm) == 0 && !flag){                        
                        flag = true;
                        return prm;
                    }else if(!prm.is_stack && !flag){
                        flag = true;
                        return false;
                    }else{
                        if(!flag){
                            return prm;
                        }
                        return false;
                    }
                });
                res['promotions_active'] = stb;
                return res;
            }else{
                return res;
            }
        },
        compute_price_filter_quantity: function (promotion) {
            let promotion_prices = this.pos.promotion_price_by_promotion_id[promotion.id];
            if (promotion_prices) {
                let prices_item_by_product_id = {};
                for (let i = 0; i < promotion_prices.length; i++) {
                    let item = promotion_prices[i];
                    if (!prices_item_by_product_id[item.product_id[0]]) {
                        prices_item_by_product_id[item.product_id[0]] = [item]
                    } else {
                        prices_item_by_product_id[item.product_id[0]].push(item)
                    }
                }
                let quantity_by_product_id = this.product_quantity_by_product_id();
                for (var i in quantity_by_product_id) {
                    if (prices_item_by_product_id[i]) {
                        let quantity_tmp = 0;
                        let price_item_tmp = null;
                        for (let j = 0; j < prices_item_by_product_id[i].length; j++) {
                            let price_item = prices_item_by_product_id[i][j];
                            if (quantity_by_product_id[i] >= price_item.minimum_quantity && quantity_by_product_id[i] >= quantity_tmp) {
                                quantity_tmp = price_item.minimum_quantity;
                                price_item_tmp = price_item;
                            }
                        }
                        if (price_item_tmp) {
                            let lines = _.filter(this.orderlines.models, function (line) {
                                return !line['is_return'] && !line['promotion'] && line.product.id == price_item_tmp.product_id[0];
                            });
                            let promotion_reason = promotion.name;
                            let promotion_amount = price_item_tmp.price_down;
                            this._apply_promotion_to_orderlines(lines, promotion.id, promotion_reason, promotion_amount, 0);
                        }
                    }
                }
            }
        },
        lock_order: async function () {
            const order = this;
            if (order && order.table) {
                let result = await rpc.query({
                    model: 'restaurant.table',
                    method: 'lock_table',
                    args: [[order.table.id], {
                        'locked': true,
                        'customer_name': this.pos.r_customer_name || '',
                        'date_reserve': this.pos.table_reserve_date || false,
                        'clear_interval': this.pos.clear_interval || false
                    }],
                })
                if (result) {
                    const table = this.pos.tables.find(t => t.id == order.table.id)
                    table.locked = true;
                    this.pos.set_table(null)
                }
                if (this.pos.pos_bus) {
                    this.pos.pos_bus.send_notification({
                        data: {
                            order: order.export_as_JSON(),
                            table_id: order.table.id,
                            order_uid: order.uid,
                            lock: true,
                            customer_name: this.pos.r_customer_name || '',
                            date_reserve: this.pos.table_reserve_date || false
                        },
                        action: 'lock_table',
                        order_uid: order.uid,
                    })
                }
            }
        },
        get_table_order_seat_no: function(ev) {
            var self = this;
            var seatno = this.get_orderlines().filter((x)=>{return x.required_ask_seat !== ""});
            return seatno.map((x) => x.required_ask_seat).join()
        }
    });
    
});