odoo.define('equip3_pos_masterdata.big_data', function (require) {

    const models = require('point_of_sale.models');
    const core = require('web.core');
    const _t = core._t;
    const db = require('point_of_sale.DB');
    const indexed_db = require('equip3_pos_masterdata.indexedDB');
    const field_utils = require('web.field_utils');
    const time = require('web.time');
    const retail_db = require('equip3_pos_masterdata.database');
    const bus = require('equip3_pos_masterdata.core_bus');
    const rpc = require('web.rpc');
    const exports = {};
    const {posbus} = require('point_of_sale.utils');
    const Session = require('web.Session');

    const indexedDB = window.indexedDB || window.mozIndexedDB || window.webkitIndexedDB || window.msIndexedDB || window.shimIndexedDB;

    if (!indexedDB) {
        window.alert("Your browser doesn't support a stable version of IndexedDB.")
    }
    
    // TODO: for QRcodeOrderScreen
    const listenEventConfirmPlaceOrderOfUsers = Backbone.Model.extend({
        initialize: function (pos) {
            var self = this;
            this.pos = pos;
        },
        start: function () {
            this.bus = bus.bus;
            this.bus.on("notification", this, this.on_notification);
            this.bus.start_polling();
        },
        on_notification: function (notifications) {
            if (notifications && notifications[0] && notifications[0][1]) {
                for (var i = 0; i < notifications.length; i++) {
                    var channel = notifications[i][0][1];
                    if (channel == 'pos.confirm.place.order') {
                        let uid = notifications[i][1].uid
                        posbus.trigger('user-confirm-place-order', uid)
                    }
                }
            }
        }
    });

    const _super_PosModel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        initialize: async function (session, attributes) {
            if (attributes && attributes.chrome) {
                this.chrome = attributes.chrome
            }
            let self = this;
            this.deleted = {};
            this.partner_model = null;
            this.product_model = null;
            this.stock_quant_model = null;
            this.product_brand_model = null;
            this.pos_voucher_model = null;
            this.pos_order_model = null;
            this.pos_order_line_model = null;

            this.account_move_model = null;
            this.account_move_line_model = null;
            this.total_account_move = 0;
            this.total_account_move_line = 0;
            this.account_move_ids = [];
            this.account_move_line_ids = [];

            this.product_template_model = null;
            this.product_template_barcode_model = null;
            this.pricelist_model = null;
            this.lot_model = null;
            this.total_products = 0;
            this.total_product_templates = 0;
            this.total_product_template_barcode = 0;
            this.total_pricelists = 0;
            this.total_lots = 0;
            this.total_stock_quant = 0;
            this.total_product_brand = 0;

            this.total_pos_promotion = 0;
            this.total_pos_promotion_discount_order = 0;
            this.total_pos_promotion_discount_category = 0;
            this.total_pos_promotion_discount_quantity = 0;
            this.total_pos_promotion_gift_condition = 0;
            this.total_pos_promotion_gift_free = 0;
            this.total_pos_promotion_discount_condition = 0;
            this.total_pos_promotion_discount_apply = 0;
            this.total_pos_promotion_special_category = 0;
            this.total_pos_promotion_selected_brand = 0;
            this.total_pos_promotion_tebus_murah_selected_brand = 0;
            this.total_pos_promotion_specific_product = 0;
            this.total_pos_promotion_multi_buy = 0;
            this.total_pos_promotion_price = 0;
            this.total_pos_promotion_tebus_murah = 0;
            this.total_pos_promotion_multilevel_condition = 0;
            this.total_pos_promotion_multilevel_gift = 0;

            this.total_pos_promotion_ids = [];
            this.total_pos_promotion_discount_order_ids = [];
            this.total_pos_promotion_discount_category_ids = [];
            this.total_pos_promotion_discount_quantity_ids = [];
            this.total_pos_promotion_gift_condition_ids = [];
            this.total_pos_promotion_gift_free_ids = [];
            this.total_pos_promotion_discount_condition_ids = [];
            this.total_pos_promotion_discount_apply_ids = [];
            this.total_pos_promotion_special_category_ids = [];
            this.total_pos_promotion_selected_brand_ids = [];
            this.total_pos_promotion_tebus_murah_selected_brand_ids = [];
            this.total_pos_promotion_specific_product_ids = [];
            this.total_pos_promotion_multi_buy_ids = [];
            this.total_pos_promotion_price_ids = [];
            this.total_pos_promotion_tebus_murah_ids = [];
            this.total_pos_promotion_multilevel_condition_ids = [];
            this.total_pos_promotion_multilevel_gift_ids = [];

            this.total_pos_voucher = 0;
            this.total_pos_order = 0;
            this.total_pos_order_line = 0;
            this.total_clients = 0;
            this.load_datas_cache = false;
            this.max_load = 9999;
            this.next_load = 10000;
            this.first_load = 10000;
            this.session = session.env.session;
            this.sequence = 0;
            this.image_by_product_id = {}
            this.product_ids = []
            this.product_template_ids = []
            this.pricelist_ids = []
            this.lot_ids = []
            this.stock_quant_ids = []
            this.product_brand_ids = []
            this.product_template_barcode_ids = []
            this.pos_voucher_ids = []
            this.posorder_ids = []
            this.posorderline_ids = []
            this.partner_ids = []
            this.model_lock = [];
            this.model_unlock = [];
            this.order_ids = []
            this.orderline_ids = []
            this.model_ids = this.session['model_ids'];
            this.start_time = this.session['start_time'];
            this.pos_retail = this.session['pos_retail'];
            this.equip3_pos_masterdata = this.session['equip3_pos_masterdata'];
            
            this.company_currency_id = this.session['company_currency_id'];
            _super_PosModel.initialize.call(this, session, attributes);


            let fonts = _.find(this.models, function (model) { // TODO: odoo default need 5 seconds load fonts, we dont use font 'Lato','Inconsolata', it reason no need to wait
                return model.label == 'fonts'
            });
            fonts.loaded = function (self) {
                return true;
            };
            for (let i = 0; i < this.models.length; i++) {
                let this_model = this.models[i];
                if (this_model.model && this.model_ids[this_model.model]) {
                    this_model['max_id'] = this.model_ids[this_model.model]['max_id'];
                    this_model['min_id'] = this.model_ids[this_model.model]['min_id'];
                    if (this_model.model == 'product.product' && this_model.fields && this_model.fields.length) {
                        this.product_model = this_model;
                        this.model_lock.push(this_model);
                    }
                    if (this_model.model == 'product.template' && this_model.fields && this_model.fields.length) {
                        this.product_template_model = this_model;
                        this.model_lock.push(this_model);
                    }
                    if (this_model.model == 'product.template.barcode' && this_model.fields && this_model.fields.length) {
                        this.product_template_barcode_model = this_model;
                        this.model_lock.push(this_model);
                    }
                    if (this_model.model == 'stock.production.lot' && this_model.fields) {
                        this.model_lock.push(this_model);
                        this.lot_model = this_model;
                    }
                    if (this_model.model == 'stock.quant' && this_model.fields && this_model.fields.length) {
                        this.stock_quant_model = this_model;
                        this.model_lock.push(this_model);
                    }
                    if (this_model.model == 'product.brand' && this_model.fields && this_model.fields.length) {
                        this.product_brand_model = this_model;
                        this.model_lock.push(this_model);
                    }
                    if (this_model.model == 'pos.voucher' && this_model.fields && this_model.fields.length) {
                        this.pos_voucher_model = this_model;
                        this.model_lock.push(this_model);
                    }
                    if (this_model.model == 'product.pricelist.item') {
                        this.model_lock.push(this_model);
                        this.pricelist_model = this_model;
                    }
                    if (this_model.model == 'res.partner' && this_model.fields) {
                        this.model_lock.push(this_model);
                        this.partner_model = this_model;
                    }

                    // Start Promotions
                    let _pos_promotion_models = [
                        'pos.promotion', 'pos.promotion.discount.order', 'pos.promotion.discount.category',
                        'pos.promotion.discount.quantity', 'pos.promotion.gift.condition', 'pos.promotion.gift.free', 
                        'pos.promotion.discount.condition', 'pos.promotion.discount.apply', 'pos.promotion.special.category',  'pos.promotion.selected.brand', 'pos.promotion.tebus.murah.selected.brand', 
                        'pos.promotion.multi.buy', 'pos.promotion.price','pos.promotion.specific.product', 'pos.promotion.tebus.murah',
                        'pos.promotion.multilevel.condition', 'pos.promotion.multilevel.gift',
                    ];
                    if(_pos_promotion_models.includes(this_model.model) && this_model.fields && this_model.fields.length) {
                        this.pos_voucher_model = this_model;
                        this.model_lock.push(this_model);
                    }
                    // End Promotions

                    if (this_model.model == 'pos.order' && this_model.fields && this_model.fields.length) {
                        this.pos_order_model = this_model;
                        this.model_lock.push(this_model);
                    }
                    if (this_model.model == 'pos.order.line' && this_model.fields && this_model.fields.length) {
                        this.pos_order_line_model = this_model;
                        this.model_lock.push(this_model);
                    }

                    // Start Invoices
                    if (this_model.model == 'account.move' && this_model.fields && this_model.fields.length) {
                        this.account_move_model = this_model;
                        this.model_lock.push(this_model);
                    }
                    if (this_model.model == 'account.move.line' && this_model.fields && this_model.fields.length) {
                        this.account_move_line_model = this_model;
                        this.model_lock.push(this_model);
                    }
                    // End Invoices

                } else {
                    this.model_unlock.push(this_model);
                }
            }
            // locked loyalty of odoo
            this.model_unlock.filter(model => model.model && model.model != 'loyalty.program');

            if (this.product_model && this.product_template_model && this.pricelist_model && this.partner_model 
                && this.lot_model && this.stock_quant_model && this.pos_order_model && this.pos_order_line_model 
                && this.account_move_model && this.account_move_line_model && this.pos_voucher_model) {
                let models = {
                    'product.product': {
                        fields: this.product_model.fields,
                        domain: this.product_model.domain,
                        context: this.product_model.context,
                    },
                    'product.template': {
                        fields: this.product_template_model.fields,
                        domain: this.product_template_model.domain,
                        context: this.product_template_model.context,
                    },
                    'product.template.barcode': {
                        fields: this.product_template_barcode_model.fields,
                        domain: this.product_template_barcode_model.domain,
                    },
                    'stock.production.lot': {
                        fields: this.lot_model.fields,
                        domain: this.lot_model.domain,
                        context: this.lot_model.context,
                    },
                    'stock.quant': {
                        fields: this.stock_quant_model.fields,
                        domain: this.stock_quant_model.domain,
                    },
                    'product.brand': {
                        fields: this.product_brand_model.fields,
                        domain: this.product_brand_model.domain,
                    },
                    'pos.voucher': {
                        fields: this.pos_voucher_model.fields,
                        domain: this.pos_voucher_model.domain,
                    },
                    'product.pricelist.item': {
                        fields: this.pricelist_model.fields,
                        domain: this.pricelist_model.domain,
                        context: this.pricelist_model.context,
                    },
                    'pos.order': {
                        fields: this.pos_order_model.fields,
                        domain: this.pos_order_model.domain,
                    },
                    'pos.order.line': {
                        fields: this.pos_order_line_model.fields,
                        domain: this.pos_order_line_model.domain,
                    },
                    'res.partner': {
                        fields: this.partner_model.fields,
                        domain: this.partner_model.domain,
                        context: this.partner_model.context,
                    },

                    'account.move': {
                        fields: this.account_move_model.fields,
                        domain: this.account_move_model.domain,
                    },
                    'account.move.line': {
                        fields: this.account_move_line_model.fields,
                        domain: this.account_move_line_model.domain,
                    },
                };
                for (let i = 0; i < this.model_unlock.length; i++) {
                    let model = this.model_unlock[i];
                    if (!model.model) {
                        continue
                    }
                    if (['sale.order', 'sale.order.line', 'account.move', 'account.move.line'].indexOf(model.model) != -1) {
                        models[model.model] = {
                            fields: model.fields,
                            domain: [],
                            context: {},
                        }
                    }
                }

                this.rpc({
                    model: 'pos.cache.database',
                    method: 'save_parameter_models_load',
                    args: [[], models]
                }, {
                    shadow: true,
                    timeout: 60000
                }).then(function (reinstall) {
                    console.log('[save_parameter_models_load]  ' + reinstall);
                }, function (err) {
                    console.error(err);
                });
            }

            if(self.db.pos_load_data_from_pos_cache_sdk){
                this.models = this.models;
            }else{
                this.models = this.model_unlock; // TODO: don't load on pos screen use IndexedDB instead
            }

            let pos_session_object = this.get_model('pos.session');
            if (pos_session_object) {
                pos_session_object.fields.push('required_reinstall_cache')
            }
            this.indexed_db = new indexed_db(self.session);
            this.apply_promotion_succeed = false;
        },

        async getDatasByModel(model, domain, fields, context) {
            const self = this
            const object = this.get_model(model);
            if (!fields) {
                fields = object.fields
            }
            if (!domain) {
                domain = object.domain
            }
            if (!context) {
                context = object.context
            }
            domain = typeof domain === 'function' ? domain(this, {}) : domain;
            fields = typeof fields === 'function' ? fields(this, {}) : fields;
            context = typeof context === 'function' ? context(this, {}) : context;
            this.set('synch', {
                status: 'connecting',
            });
            let results = await rpc.query({
                model: model,
                method: 'search_read',
                domain: domain,
                fields: fields,
                context: context
            }, function (datas) {
                self.set('synch', {
                    status: 'connected',
                });
                return datas
            }, function (error) {
                self.set('synch', {
                    status: 'disconnected',
                    pending: 'connection Offline'
                });
            })
            this.set('synch', {
                status: 'connected',
            });
            return results
        },

        async getDatasByModelInShadow(model, domain, fields, context) {
            const self = this
            const object = this.get_model(model);
            if (!fields) {
                fields = object.fields
            }
            if (!domain) {
                domain = object.domain
            }
            if (!context) {
                context = object.context
            }
            domain = typeof domain === 'function' ? domain(this, {}) : domain;
            fields = typeof fields === 'function' ? fields(this, {}) : fields;
            context = typeof context === 'function' ? context(this, {}) : context;
            this.set('synch', {
                status: 'connecting',
            });
            let results = await rpc.query({
                model: model,
                method: 'search_read',
                domain: domain,
                fields: fields,
                context: context
            },{
                shadow: true
            }).then(function(datas) {
                return datas;
            });
            this.set('synch', {
                status: 'connected',
            });
            return results
        },

        async getAccountMoves() {
            this.alert_message({
                title: _t('Syncing'),
                body: _t('Account Invoices')
            })
            const model = this.get_model('account.move');
            const params = {
                model: 'account.move',
                fields: model.fields,
                domain: [['company_id', '=', this.company.id]],
                context: {
                    'pos_config_id': this.config.id
                }
            }
            this.saveMoves(await this.getDatasByModel(params['model'], params['domain'], params['fields'], params['context']))
            this.db.save_invoice_lines(await this.getAccountMoveLines())
        },

        async getAccountMoveLines() {
            const self = this
            const model = self.get_model('account.move.line');
            const params = {
                model: 'account.move.line',
                fields: model.fields,
                domain: [['move_id', 'in', this.invoice_ids]],
                context: {
                    'pos_config_id': this.config.id
                }
            }
            return await this.getDatasByModel(params['model'], params['domain'], params['fields'], params['context'])
        },

        saveMoves(invoices) {
            this.invoice_ids = []
            for (let i = 0; i < invoices.length; i++) {
                this.invoice_ids.push(invoices[i]['id']);
            }
            this.db.save_invoices(invoices);
        },

        async getSaleOrders() {
            this.alert_message({
                title: _t('Syncing'),
                body: _t('Sale Orders')
            })
            const self = this;
            const model = self.get_model('sale.order');
            const params = {
                model: 'sale.order',
                fields: model.fields,
                domain: [['pos_order_id','=',false]],
                context: {
                    'pos_config_id': this.config.id
                }
            }
            this.saveSaleOrders(await this.getDatasByModel(params['model'], params['domain'], params['fields'], params['context']))
            await this.getSaleOrderLines()
        },

        async getSaleOrderLines() {
            const self = this
            const model = self.get_model('sale.order.line');
            const params = {
                model: 'sale.order.line',
                fields: model.fields,
                domain: [['order_id', 'in', this.booking_ids]],
                context: {
                    'pos_config_id': this.config.id
                }
            }
            this.saveSaleOrderLines(await this.getDatasByModel(params['model'], params['domain'], params['fields'], params['context']))
        },


        saveSaleOrders(orders) {
            if (!this.booking_ids) {
                this.booking_ids = [];
            }
            if (!this.booking_in_state_sale_ids) {
                this.booking_in_state_sale_ids = [];
            }
            for (let i = 0; i < orders.length; i++) {
                let order = orders[i]
                if (!this.booking_ids.includes(order.id)) {
                    this.booking_ids.push(order.id)
                }
                if(!order.pos_order_id && ['sale','done'].includes(order.state) && order.is_self_pickup && order.delivered_state != 'fully'){
                    if (!this.booking_in_state_sale_ids.includes(order.id)) {
                        this.booking_in_state_sale_ids.push(order.id);
                    }
                }

                let create_date = field_utils.parse.datetime(order.create_date);
                order.create_date = field_utils.format.datetime(create_date);
                let date_order = field_utils.parse.datetime(order.date_order);
                order.date_order = field_utils.format.datetime(date_order);
                if (order.reserve_from) {
                    let reserve_from = field_utils.parse.datetime(order.reserve_from);
                    order.reserve_from = field_utils.format.datetime(reserve_from);
                }
                if (order.reserve_to) {
                    let reserve_to = field_utils.parse.datetime(order.reserve_to);
                    order.reserve_to = field_utils.format.datetime(reserve_to);
                }
            }
            this.db.save_sale_orders(orders);
        },

        saveSaleOrderLines(order_lines) {
            if (!this.order_lines) {
                this.order_lines = order_lines;
            } else {
                this.order_lines = this.order_lines.concat(order_lines);
                order_lines.forEach(l => {
                    this.order_lines = this.order_lines.filter(sol => sol.id != l.id)
                    this.order_lines.push(l)
                })
            }
            this.db.save_sale_order_lines(order_lines);
        },
        
        async getPosOrders() {
            await this.getPosOrderLines()
            await this.getPosPayments()
        },

        async getPosOrderLines() {
            const self = this;
            const model = self.get_model('pos.order.line');
            const params = {
                model: 'pos.order.line',
                fields: model.fields,
                domain: [['order_id', 'in', this.order_ids]],
                context: {
                    'pos_config_id': this.config.id
                }
            }
            this.savePosOrderLines(await this.getDatasByModel(params['model'], params['domain'], params['fields'], params['context']))
        },

        async getPosPayments() {
            const self = this;
            const model = self.get_model('pos.payment');
            const params = {
                model: model.model,
                fields: model.fields,
                domain: [['pos_order_id', 'in', this.order_ids]],
                context: {
                    'pos_config_id': this.config.id
                }
            }
            let payments = await this.getDatasByModel(params['model'], params['domain'], params['fields'], params['context'])
            for (let i = 0; i < payments.length; i++) {
                let payment = payments[i]
                let payment_date = field_utils.parse.datetime(payment.payment_date);
                payment.payment_date = field_utils.format.datetime(payment_date);
                if(payment.pos_order_id){
                    let order_id = payment.pos_order_id[0]
                    let order = this.db.order_by_id[order_id]
                    order['payments'].push(payment)
                }
                if(!payment.pos_order_id){
                    console.error("Error ~ payment.pos_order_id: ", payment)
                }
            }
            return payments
        },

        savePosOrders(orders) {
            for (let i = 0; i < orders.length; i++) {
                let order = orders[i];
            
                if(!this.order_ids.includes(order.id)){
                    this.order_ids.unshift(order.id)
                }
            }
            this.db.save_pos_orders(orders);
        },

        savePosOrderLines(order_lines) {
            this.db.save_pos_order_line(order_lines);
            for (let i = 0; i < order_lines.length; i++) {

                if(!this.orderline_ids.includes(order_lines[i]['id'])){
                    this.orderline_ids.push(order_lines[i]['id'])
                }
  
                    
            }
        },

        removeProductHasDeletedOutOfCart: function (product_id) {
            let orders = this.get('orders').models;
            for (let n = 0; n < orders.length; n++) {
                let order = orders[n];
                for (let i = 0; i < order.orderlines.models.length; i++) {
                    let line = order.orderlines.models[i];
                    if (line.product.id == product_id) {
                        order.remove_orderline(line);
                    }
                }
            }
        },
        update_customer_in_cart: function (partner_datas) {
            this.the_first_load = true;
            let orders = this.get('orders').models;
            for (let i = 0; i < orders.length; i++) {
                let order = orders[i];
                let client_order = order.get_client();
                if (!client_order || order.finalized) {
                    continue
                }
                for (let n = 0; n < partner_datas.length; n++) {
                    let partner_data = partner_datas[n];
                    if (partner_data['id'] == client_order.id) {
                        let client = this.db.get_partner_by_id(client_order.id);
                        order.set_client(client);
                    }
                }
            }
            this.the_first_load = false;
        },
        remove_partner_deleted_outof_orders: function (partner_id) {
            let orders = this.get('orders').models;
            let order = orders.find(function (order) {
                let client = order.get_client();
                if (client && client['id'] == partner_id) {
                    return true;
                }
            });
            if (order) {
                order.set_client(null)
            }
            return order;
        },
        get_model: function (_name) {
            let _index = this.models.map(function (e) {
                return e.model;
            }).indexOf(_name);
            if (_index > -1) {
                return this.models[_index];
            }
            return false;
        },
        sort_by: function (field, reverse, primer) {
            let key = primer ?
                function (x) {
                    return primer(x[field])
                } :
                function (x) {
                    return x[field]
                };
            reverse = !reverse ? 1 : -1;
            return function (a, b) {
                return a = key(a), b = key(b), reverse * ((a > b) - (b > a));
            }
        },
        _get_active_pricelist: function () {
            let current_order = this.get_order();
            let default_pricelist = this.default_pricelist;
            if (current_order && current_order.pricelist) {
                let pricelist = _.find(this.pricelists, function (pricelist_check) {
                    return pricelist_check['id'] == current_order.pricelist['id']
                });
                return pricelist;
            } else {
                if (default_pricelist) {
                    let pricelist = _.find(this.pricelists, function (pricelist_check) {
                        return pricelist_check['id'] == default_pricelist['id']
                    });
                    return pricelist
                } else {
                    return null
                }
            }
        },
        get_process_time: function (min, max) {
            if (min > max) {
                return 1
            } else {
                return (min / max).toFixed(1)
            }
        },

        async getProductPricelistItems() {
            // TODO: loading product pricelist items on background
            const self = this;
            await this.getDatasByModel('product.pricelist.item', [['pricelist_id', 'in', _.pluck(this.pricelists, 'id')]], []).then(function (pricelistItems) {
                if (!pricelistItems) {
                    return false
                }
                console.log('[loaded] Product Pricelist Items: ' + pricelistItems.length)
                const pricelist_by_id = {};
                _.each(self.pricelists, function (pricelist) {
                    pricelist_by_id[pricelist.id] = pricelist;
                });
                _.each(pricelistItems, function (item) {
                    let pricelist = pricelist_by_id[item.pricelist_id[0]];
                    pricelist.items.push(item);
                    item.base_pricelist = pricelist_by_id[item.base_pricelist_id[0]];
                });
                let order = self.get_order();
                let pricelist = self._get_active_pricelist();
                if (order && pricelist) {
                    order.set_pricelist(pricelist);
                }
            })
        },

        reloadPosScreen() {
            const self = this;
            return new Promise(function (resolve, reject) {
                self.rpc({
                    model: 'pos.session',
                    method: 'update_required_reinstall_cache',
                    args: [[self.pos_session.id]]
                }, {
                    shadow: true,
                    timeout: 65000
                }).then(function (state) {
                    self.remove_indexed_db();
                    self.reload_pos();
                    resolve(state);
                }, function (err) {
                    self.remove_indexed_db();
                    self.reload_pos();
                    reject(err)
                })
            });
        },

        getStockDatasByLocationIds(product_ids = [], location_ids = []) {
            return rpc.query({
                model: 'stock.location',
                method: 'getStockDatasByLocationIds',
                args: [[], product_ids, location_ids],
                context: {}
            }, {
                timeout: 7500,
                shadow: true,
            });
        },

        async syncInvoices(sync_models){ 
            // TODO: sync account.move and account.move.line
            let self = this;
            if(sync_models){
                if(sync_models.sync_state.invoices == 'connecting'){
                    return;
                }
            }

            let vals = {
                'pos_config_id': self.config.id,
                'account.move': self.db.write_date_by_model['account.move'],
                'account.move.line': self.db.write_date_by_model['account.move.line'],
            }
            console.log('[syncInvoices] ~ Get Last Updated: account.move: ' + vals['account.move'] +  '  account.move: ' + vals['account.move.line'])

            let args = [[], vals];
            if(sync_models){
                sync_models.sync_state.invoices = 'connecting';
            }
            let result = await self.rpc({
                model: 'pos.cache.database',
                method: 'sync_pos_invoice', 
                args: args
            }, {
                shadow: true,
                timeout: 1200000 // 20 minutes
            }).then(function (response) {
                return response;
            }, function (error) {
                if (error && error.message && error.message.code == -32098) {
                    console.error('[syncInvoices] ~ Server Offline')
                } else {
                    console.error('[syncInvoices] ~ Error 403')
                }
                if(sync_models){
                    sync_models.sync_state.invoices = 'error';
                }
                return null;
            });
            if (result != null) {
                let account_move_rec = result['account_move'];
                let account_move_line_rec = result['account_move_line'];
                console.log('[syncInvoices] ~ Results: account_move: ' + account_move_rec.length +  '  account_move_line: ' + account_move_line_rec.length);

                for (var i = account_move_rec.length - 1; i >= 0; i--) {
                    account_move_rec[i].active = true;
                }
                for (var j = account_move_line_rec.length - 1; j >= 0; j--) {
                    account_move_line_rec[j].active = true;
                }
                
                if(account_move_rec.length){
                    console.log('[syncInvoices] ~ Updating variable account.move');
                    var active_records = account_move_rec.filter(r => r['active'] == true);
                    if(active_records.length){
                        self.saveMoves(active_records)
                        self.indexed_db.write('account.move', active_records);
                    }
                    self.save_results('account.move', account_move_rec);
                    console.log('[syncInvoices] ~ Finish variable account.move');
                }
                if(account_move_line_rec.length){
                    console.log('[syncInvoices] ~ Updating variable account.move.line');
                    var active_records = account_move_line_rec.filter(r => r['active'] == true);
                    if(active_records.length){
                        self.db.save_invoice_lines(active_records);
                        self.indexed_db.write('account.move.line', active_records);
                    }
                    self.save_results('account.move.line', account_move_line_rec);
                    console.log('[syncInvoices] ~ Finish variable account.move.line');
                }
            }else{
                console.log('[syncInvoices] ~ Results: 0');
            }

            if(sync_models){
                if(sync_models.sync_state.invoices == 'error'){
                    return false;
                }
            }
            
            if(sync_models){
                sync_models.sync_state.invoices = 'done';
            }
        },

        async syncPOSOrders(sync_models){
            // TODO: sync pos.order and pos.order.line
            let self = this;
            if(sync_models){
                if(sync_models.sync_state.pos_orders == 'connecting'){
                    return;
                }
            }

            let vals = {
                'pos_config_id': self.config.id,
                'pos.order': self.db.write_date_by_model['pos.order'],
                'pos.order.line': self.db.write_date_by_model['pos.order.line'],
                'pos.payment': self.db.write_date_by_model['pos.order.line'],
            }
            console.log('[syncProduct] ~ Get Last Updated: pos.order: ' + vals['pos.order'] +  '  pos.order: ' + vals['pos.order.line'])

            let args = [[], vals];
            if(sync_models){
                sync_models.sync_state.pos_orders = 'connecting';
            }
            let result = await self.rpc({
                model: 'pos.cache.database',
                method: 'sync_pos_orders', 
                args: args
            }, {
                shadow: true,
                timeout: 1200000 // 20 minutes
            }).then(function (response) {
                return response;
            }, function (error) {
                if (error && error.message && error.message.code == -32098) {
                    console.error('[syncPOSorder] ~ Server Offline')
                } else {
                    console.error('[syncPOSorder] ~ Error 403')
                }
                if(sync_models){
                    sync_models.sync_state.pos_orders = 'error';
                }
                return null;
            });

            if (result != null) {
                let pos_order_rec = result['pos_order'];
                let pos_order_line_rec = result['pos_order_line'];
                console.log('[syncPOSorder] ~ Results: pos_order: ' + pos_order_rec.length +  '  pos_order_line: ' + pos_order_line_rec.length);
                let pos_payment_rec = result['pos_payment'];
                if(pos_order_rec.length){
                    console.log('[syncPOSorder] ~ Updating variable pos.order');
                    var active_records = pos_order_rec.filter(r => r['active'] == true);
                    if(active_records.length){
                        self.pos_order_model.loaded(self, pos_order_rec);
                        self.indexed_db.write('pos.order', active_records);
                    }
                    self.save_results('pos.order', pos_order_rec);
                    console.log('[syncPOSorder] ~ Finish variable pos.order');
                }
                if(pos_order_line_rec.length){
                    console.log('[syncPOSorder] ~ Updating variable pos.order.line');
                    var active_records = pos_order_line_rec.filter(r => r['active'] == true);
                    if(active_records.length){
                        self.pos_order_line_model.loaded(self, pos_order_line_rec);
                        self.indexed_db.write('pos.order.line', active_records);
                    }
                    self.save_results('pos.order.line', pos_order_line_rec);
                    console.log('[syncPOSorder] ~ Finish variable pos.order.line');
                }

                if(pos_payment_rec.length){
                    if(!self.pos_payment_by_order_id){
                        self.pos_payment_by_order_id = {}
                    }
                    for (let payment of pos_payment_rec){
                        let order_id = payment.pos_order_id[0];
                        let order = self.db.order_by_id[order_id];
                        order['payments'].push(payment);

                        if (!self.pos_payment_by_order_id[order_id]) {
                            self.pos_payment_by_order_id[order_id] = [payment];
                        } else {
                            self.pos_payment_by_order_id[order_id].push(payment);
                        }
                    }
                    console.log('[syncPOSorder] ~ Finish variable pos.payment');
                }
               
            }else{
                console.log('[syncPOSorder] ~ Results: 0');
            }

            if(sync_models){
                if(sync_models.sync_state.pos_orders == 'error'){
                    return false;
                }
            }

            posbus.trigger('reload-orders');
            if(sync_models){
                sync_models.sync_state.pos_orders = 'done';
            }
        },

        async syncPartner(sync_models){
            // TODO: sync res.partner
            let self = this;
            if(sync_models){
                if(sync_models.sync_state.partner == 'connecting'){
                    return;
                }
            }
            let last_write_date = self.db.write_date_by_model['res.partner']
            console.log('[syncPartner] ~ Get Last Updated after or equal to: ', last_write_date)
             
            let args = [[], last_write_date];
            if(sync_models){
                sync_models.sync_state.partner = 'connecting';
            }
            let results = await self.rpc({
                model: 'pos.cache.database',
                method: 'sync_pos_partner', 
                args: args
            }, {
                shadow: true,
                timeout: 1200000 // 20 minutes
            }).then(function (response) {
                return response;
            }, function (error) {
                if (error && error.message && error.message.code == -32098) {
                    console.error('[syncPartner] ~ Server Offline')
                } else {
                    console.error('[syncPartner] ~ Error 403')
                }
                if(sync_models){
                    sync_models.sync_state.partner = 'error';
                }
                return null;
            })
            console.log('[syncPartner] ~ Results:', results == null? '0': results.length);
            if (results != null) {
                console.log('[syncPartner] ~ Updating variable res.partner'); 
                let active_records = results.filter(r => r['active'] == true);
                let archived_records = results.filter(r => r['active'] == false);
                for (let i = 0; i < archived_records.length; i++) {
                    self.indexed_db.unlink('res.partner', archived_records[i]);
                }
                if(active_records.length){
                    self.partner_model.loaded(self, results)
                    self.indexed_db.write('res.partner', active_records);
                }
                self.db.add_partners(results);
                self.save_results('res.partner', results); 
                self.update_customer_in_cart(results);
                console.log('[syncPartner] ~ Finish variable res.partner');
            }
            if(sync_models){
                if(sync_models.sync_state.partner == 'error'){
                    return false;
                }
                sync_models.sync_state.partner = 'done';
            }

        },

        async syncProductsPartners() {
            let self = this;
            let model_values = {};
            let allowed_models = [
                'product.product', 'product.template', 'res.partner'
            ]
            for (let key in this.db.write_date_by_model){
                if(allowed_models.includes(key)){
                    model_values[key] = this.db.write_date_by_model[key]
                }
            }
            console.warn('[syncProductsPartners] model_values: ', model_values)
            let args = [];
            args = [[], model_values, this.config.id];
            let results = await this.rpc({
                model: 'pos.cache.database',
                method: 'syncProductsPartners',
                args: args
            }, {
                shadow: true,
                timeout: 1200000 // 20 minutes
            })
            let count_update = 0
            for (let model in results) {
                let vals = results[model];
                for (let i = 0; i < vals.length; i++) {
                    vals[i].model = model;
                    if (vals[i].active == false) {
                        self.indexed_db.unlink(model, vals[i]);
                    }
                }
                
                vals = vals.filter(r => r['active'] == true);
                if (vals && vals.length) {
                    count_update += vals.length
                    self.indexed_db.write(model, vals);
                    self.save_results(model, vals)
                    if (model == 'res.partner') {
                        self.update_customer_in_cart(vals);
                    }
                }
            }
            console.log('Total update Products & Partners from BE: ' + count_update)
        },
        async onLoadPosSyncPricelistItems() {
            let self = this;
            let model_values = {};
            let allowed_models = ['product.pricelist.item'];
            for (let key in this.db.write_date_by_model){
                if(allowed_models.includes(key)){
                    model_values[key] = this.db.write_date_by_model[key]
                }
            }
            console.warn('[onLoadPosSyncPricelistItems] model_values: ', model_values)
            let args = [];
            args = [[], model_values, this.config.id];
            let results = await this.rpc({
                model: 'pos.cache.database',
                method: 'onLoadPosSyncPricelistItems',
                args: args
            }, {
                shadow: true,
                timeout: 1200000 // 20 minutes
            })
            let count_update = 0
            for (let model in results) {
                let vals = results[model];
                for (let i = 0; i < vals.length; i++) {
                    vals[i].model = model;
                    if (vals[i].active == false) {
                        self.indexed_db.unlink(model, vals[i]);
                    }
                }
                
                vals = vals.filter(r => r['active'] == true);
                if (vals && vals.length) {
                    count_update += vals.length
                    self.indexed_db.write(model, vals);
                    self.save_results(model, vals)
                }
            }
            console.log('Total update Pricelist Items from BE: ' + count_update)
        },
        async onLoadPosSyncProducts() {
            let self = this;
            let model_values = {};
            let allowed_models = [
                'product.product', 'product.template', 'product.pricelist.item',
                'stock.production.lot', 'stock.quant','product.brand'
            ]
            for (let key in this.db.write_date_by_model){
                if(allowed_models.includes(key)){
                    model_values[key] = this.db.write_date_by_model[key]
                }
            }
            console.warn('[onLoadPosSyncProducts] model_values: ', model_values)
            let args = [];
            args = [[], model_values, this.config.id];
            let results = await this.rpc({
                model: 'pos.cache.database',
                method: 'onLoadPosSyncProducts',
                args: args
            }, {
                shadow: true,
                timeout: 1200000 // 20 minutes
            })
            let count_update = 0
            for (let model in results) {
                let vals = results[model];
                for (let i = 0; i < vals.length; i++) {
                    vals[i].model = model;
                    if (vals[i].active == false) {
                        self.indexed_db.unlink(model, vals[i]);
                    }
                }
                
                vals = vals.filter(r => r['active'] == true);
                if (vals && vals.length) {
                    count_update += vals.length
                    self.indexed_db.write(model, vals);
                    self.save_results(model, vals)
                    if (model == 'res.partner') {
                        self.update_customer_in_cart(vals);
                    }
                }
            }
            console.log('Total update Products from BE: ' + count_update)
        },
        async onLoadPosSyncPartners() {
            let self = this;
            let model_values = {
                'res.partner': this.db.write_date_by_model['res.partner']
            };
            console.warn('[onLoadPosSyncPartners] model_values: ', model_values)
            let args = [];
            args = [[], model_values, this.config.id];
            let results = await this.rpc({
                model: 'pos.cache.database',
                method: 'onLoadPosSyncPartners',
                args: args
            }, {
                shadow: true,
                timeout: 1200000 // 20 minutes
            })
            let count_update = 0
            for (let model in results) {
                let vals = results[model];
                for (let i = 0; i < vals.length; i++) {
                    vals[i].model = model;
                    if (vals[i].active == false) {
                        self.indexed_db.unlink(model, vals[i]);
                    }
                }
                
                vals = vals.filter(r => r['active'] == true);
                if (vals && vals.length) {
                    count_update += vals.length
                    self.indexed_db.write(model, vals);
                    self.save_results(model, vals)
                    if (model == 'res.partner') {
                        self.update_customer_in_cart(vals);
                    }
                }
            }
            console.log('Total update Partners from BE: ' + count_update)
        },
        async onLoadPosSyncPromotions() {
            const self = this;
            let args = [];
            let model_values = {};
            let promotion_models = [
                'pos.promotion',
                'pos.promotion.discount.order',
                'pos.promotion.discount.category',
                'pos.promotion.discount.quantity',
                'pos.promotion.gift.condition',
                'pos.promotion.gift.free',
                'pos.promotion.discount.condition',
                'pos.promotion.discount.apply',
                'pos.promotion.special.category',
                'pos.promotion.selected.brand',
                'pos.promotion.tebus.murah.selected.brand',
                'pos.promotion.specific.product',
                'pos.promotion.multi.buy',
                'pos.promotion.price',
                'pos.promotion.tebus.murah',
                'pos.promotion.multilevel.condition', 
                'pos.promotion.multilevel.gift',
            ]
            for (let key in self.db.write_date_by_model){
                if(promotion_models.includes(key)){
                    model_values[key] = self.db.write_date_by_model[key]
                }
            }

            console.warn('[onLoadPosSyncPromotions] model_values: ', model_values)
            args = [[], model_values, this.config.id];
            let results = await this.rpc({
                model: 'pos.cache.database',
                method: 'onLoadPosSyncPromotions',
                args: args
            }, {
                shadow: true,
                timeout: 1200000 // 20 minutes
            })
            let count_update = 0
            for (let model in results) {
                let vals = results[model];
                for (let i = 0; i < vals.length; i++) {
                    vals[i].model = model;
                    if (vals[i].active == false) {
                        self.indexed_db.unlink(model, vals[i]);
                    }
                }
                vals = vals.filter(r => r['active'] == true);
                if (vals && vals.length) {
                    count_update += vals.length
                    self.indexed_db.write(model, vals);
                    self.save_results(model, vals)
                }
            }
            console.log('Total update from Backend: ' + count_update)
        },

        async fetchNewUpdateFromBackEnd() {
            const product_ids = this.db.product_ids
            const product_template_ids = this.db.product_template_ids
            const partner_ids = this.db.partner_ids
            if (product_ids.length != 0) {
                let productObject = this.get_model('product.product');
                let productTemplateObject = this.get_model('product.template');
                let partnerObject = this.get_model('res.partner');
                let productsMissed = await this.rpc({
                    model: 'product.product',
                    method: 'search_read',
                    domain: [['id', 'not in', product_ids], ['sale_ok', '=', true], ['available_in_pos', '=', true]],
                    fields: productObject.fields
                }, {
                    shadow: true,
                    timeout: 75000
                })
                console.log('[Missed products] ' + productsMissed.length)
                if (productsMissed.length) {
                    this.indexed_db.write('product.product', productsMissed);
                    this.save_results('product.product', productsMissed);
                }
                let productTemplatesMissed = await this.rpc({
                    model: 'product.template',
                    method: 'search_read',
                    domain: [['id', 'not in', product_template_ids], ['sale_ok', '=', true], ['available_in_pos', '=', true]],
                    fields: productTemplateObject.fields
                }, {
                    shadow: true,
                    timeout: 75000
                })
                console.log('[Missed product templates] ' + productTemplatesMissed.length)
                if (productTemplatesMissed.length) {
                    this.indexed_db.write('product.template', productTemplatesMissed);
                    this.save_results('product.template', productTemplatesMissed);
                }
                let partnersMissed = await this.rpc({
                    model: 'res.partner',
                    method: 'search_read',
                    domain: [['id', 'not in', partner_ids]],
                    fields: partnerObject.fields
                }, {
                    shadow: true,
                    timeout: 75000
                })
                console.log('[Missed partners] ' + partnersMissed.length)
                if (partnersMissed.length) {
                    this.indexed_db.write('res.partner', partnersMissed);
                    this.save_results('res.partner', partnersMissed);
                }
            }
            console.log('[END] fetchNewUpdateFromBackEnd')
        },

        save_results: function (model, results) {
            // TODO: load data from POS Cache SDK no need to store in IndexDB
            if(this.db.pos_load_data_from_pos_cache_sdk){
                this.db.set_last_write_date_by_model(model, results);
                return;
            }

            // TODO: When loaded all results from indexed DB, we restore back to POS Odoo
            const recordsRemoved = results.filter(r => r['active'] == false)
            if (recordsRemoved && recordsRemoved.length) {
                for (let i = 0; i < recordsRemoved.length; i++) {
                    this.indexed_db.unlink(model, recordsRemoved[i]);
                }
            }
            results = results.filter(r => r['active'] == true);

            if (model == 'product.product') {
                this.total_products += results.length;
                let process_time = this.get_process_time(this.total_products, this.model_ids[model]['count']) * 100;
                console.log('LOADED total products ' + this.total_products)
                this.product_ids = this.product_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'product.template') {
                this.total_product_templates += results.length;
                let process_time = this.get_process_time(this.total_product_templates, this.model_ids[model]['count']) * 100;
                console.log('LOADED total product templates ' + this.total_product_templates)
                this.product_template_ids = this.product_template_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'product.template.barcode') {
                this.total_product_template_barcode += results.length;
                let process_time = this.get_process_time(this.total_product_template_barcode, this.model_ids[model]['count']) * 100;
                console.log('LOADED total product template barcode ' + this.total_product_template_barcode)
                this.product_template_barcode_ids = this.product_template_barcode_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'stock.production.lot') {
                this.total_lots += results.length;
                let process_time = this.get_process_time(this.total_lots, this.model_ids[model]['count']) * 100;
                console.log('LOADED total lots ' + this.total_lots)
                this.lot_ids = this.lot_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'stock.quant') {
                this.total_stock_quant += results.length;
                let process_time = this.get_process_time(this.total_stock_quant, this.model_ids[model]['count']) * 100;
                console.log('LOADED total stock quant ' + this.total_stock_quant)
                this.stock_quant_ids = this.stock_quant_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'product.brand') {
                this.total_product_brand += results.length;
                let process_time = this.get_process_time(this.total_product_brand, this.model_ids[model]['count']) * 100;
                console.log('LOADED total product brand ' + this.total_product_brand)
                this.product_brand_ids = this.product_brand_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'pos.voucher') {
                this.total_pos_voucher  += results.length;
                let process_time = this.get_process_time(this.total_pos_voucher , this.model_ids[model]['count']) * 100;
                console.log('LOADED total pos voucher ' + this.total_pos_voucher )
                this.pos_voucher_ids = this.pos_voucher_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'product.pricelist.item') {
                this.total_pricelists += results.length;
                let process_time = this.get_process_time(this.total_pricelists, this.model_ids[model]['count']) * 100;
                console.log('LOADED total pricelists ' + this.total_pricelists)
                // Update items to pricelist
                results.forEach(item => {
                    var pricelist_id = item.pricelist_id[0];
                    var pricelist = this.pricelist_by_id[pricelist_id];
                    if (pricelist) pricelist.items.push(item);
                })
                this.pricelist_ids = this.pricelist_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'res.partner') {
                this.total_clients += results.length;
                let process_time = this.get_process_time(this.total_clients, this.model_ids[model]['count']) * 100;
                console.log('LOADED total partners ' + this.total_clients)
                this.partner_ids = this.partner_ids.concat(_.pluck(results, 'id'))
            }


            // Start Promotions
            if (model == 'pos.promotion') {
                this.total_pos_promotion  += results.length;
                let process_time = this.get_process_time(this.total_pos_promotion, this.model_ids[model]['count']) * 100;
                console.log('LOADED total pos.promotion ' + this.total_pos_promotion )
                this.total_pos_promotion_ids = this.total_pos_promotion_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'pos.promotion.discount.order') {
                this.total_pos_promotion_discount_order  += results.length;
                let process_time = this.get_process_time(this.total_pos_promotion_discount_order, this.model_ids[model]['count']) * 100;
                console.log('LOADED total pos.promotion.discount.order ' + this.total_pos_promotion_discount_order )
                this.total_pos_promotion_discount_order_ids = this.total_pos_promotion_discount_order_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'pos.promotion.discount.category') {
                this.total_pos_promotion_discount_category  += results.length;
                let process_time = this.get_process_time(this.total_pos_promotion_discount_category, this.model_ids[model]['count']) * 100;
                console.log('LOADED total pos.promotion.discount.category ' + this.total_pos_promotion_discount_category )
                this.total_pos_promotion_discount_category_ids = this.total_pos_promotion_discount_category_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'pos.promotion.discount.quantity') {
                this.total_pos_promotion_discount_quantity  += results.length;
                let process_time = this.get_process_time(this.total_pos_promotion_discount_quantity, this.model_ids[model]['count']) * 100;
                console.log('LOADED total pos.promotion.discount.quantity ' + this.total_pos_promotion_discount_quantity )
                this.total_pos_promotion_discount_quantity_ids = this.total_pos_promotion_discount_quantity_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'pos.promotion.gift.condition') {
                this.total_pos_promotion_gift_condition  += results.length;
                let process_time = this.get_process_time(this.total_pos_promotion_gift_condition, this.model_ids[model]['count']) * 100;
                console.log('LOADED total pos.promotion.gift.condition ' + this.total_pos_promotion_gift_condition )
                this.total_pos_promotion_gift_condition_ids = this.total_pos_promotion_gift_condition_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'pos.promotion.gift.free') {
                this.total_pos_promotion_gift_free  += results.length;
                let process_time = this.get_process_time(this.total_pos_promotion_gift_free, this.model_ids[model]['count']) * 100;
                console.log('LOADED total pos.promotion.gift.free ' + this.total_pos_promotion_gift_free )
                this.total_pos_promotion_gift_free_ids = this.total_pos_promotion_gift_free_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'pos.promotion.discount.condition') {
                this.total_pos_promotion_discount_condition  += results.length;
                let process_time = this.get_process_time(this.total_pos_promotion_discount_condition, this.model_ids[model]['count']) * 100;
                console.log('LOADED total pos.promotion.discount.condition ' + this.total_pos_promotion_discount_condition )
                this.total_pos_promotion_discount_condition_ids = this.total_pos_promotion_discount_condition_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'pos.promotion.discount.apply') {
                this.total_pos_promotion_discount_apply  += results.length;
                let process_time = this.get_process_time(this.total_pos_promotion_discount_apply, this.model_ids[model]['count']) * 100;
                console.log('LOADED total pos.promotion.discount.apply ' + this.total_pos_promotion_discount_apply )
                this.total_pos_promotion_discount_apply_ids = this.total_pos_promotion_discount_apply_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'pos.promotion.special.category') {
                this.total_pos_promotion_special_category  += results.length;
                let process_time = this.get_process_time(this.total_pos_promotion_special_category, this.model_ids[model]['count']) * 100;
                console.log('LOADED total pos.promotion.special.category ' + this.total_pos_promotion_special_category )
                this.total_pos_promotion_special_category_ids = this.total_pos_promotion_special_category_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'pos.promotion.selected.brand') {
                this.total_pos_promotion_selected_brand  += results.length;
                let process_time = this.get_process_time(this.total_pos_promotion_selected_brand, this.model_ids[model]['count']) * 100;
                console.log('LOADED total pos.promotion.selected.brand ' + this.total_pos_promotion_selected_brand )
                this.total_pos_promotion_selected_brand_ids = this.total_pos_promotion_selected_brand_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'pos.promotion.tebus.murah.selected.brand') {
                this.total_pos_promotion_tebus_murah_selected_brand  += results.length;
                let process_time = this.get_process_time(this.total_pos_promotion_tebus_murah_selected_brand, this.model_ids[model]['count']) * 100;
                console.log('LOADED total pos.promotion.tebus.murah.selected.brand ' + this.total_pos_promotion_tebus_murah_selected_brand )
                this.total_pos_promotion_tebus_murah_selected_brand_ids = this.total_pos_promotion_tebus_murah_selected_brand_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'pos.promotion.specific.product') {
                this.total_pos_promotion_specific_product  += results.length;
                let process_time = this.get_process_time(this.total_pos_promotion_specific_product, this.model_ids[model]['count']) * 100;
                console.log('LOADED total pos.promotion.specific.product ' + this.total_pos_promotion_specific_product )
                this.total_pos_promotion_specific_product_ids = this.total_pos_promotion_specific_product_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'pos.promotion.multi.buy') {
                this.total_pos_promotion_multi_buy  += results.length;
                let process_time = this.get_process_time(this.total_pos_promotion_multi_buy, this.model_ids[model]['count']) * 100;
                console.log('LOADED total pos.promotion.multi.buy ' + this.total_pos_promotion_multi_buy )
                this.total_pos_promotion_multi_buy_ids = this.total_pos_promotion_multi_buy_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'pos.promotion.price') {
                this.total_pos_promotion_price  += results.length;
                let process_time = this.get_process_time(this.total_pos_promotion_price, this.model_ids[model]['count']) * 100;
                console.log('LOADED total pos.promotion.price ' + this.total_pos_promotion_price )
                this.total_pos_promotion_price_ids = this.total_pos_promotion_price_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'pos.promotion.tebus.murah') {
                this.total_pos_promotion_tebus_murah  += results.length;
                let process_time = this.get_process_time(this.total_pos_promotion_tebus_murah, this.model_ids[model]['count']) * 100;
                console.log('LOADED total pos.promotion.tebus.murah ' + this.total_pos_promotion_tebus_murah )
                this.total_pos_promotion_tebus_murah_ids = this.total_pos_promotion_tebus_murah_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'pos.promotion.multilevel.condition') {
                this.total_pos_promotion_multilevel_condition  += results.length;
                let process_time = this.get_process_time(this.total_pos_promotion_multilevel_condition, this.model_ids[model]['count']) * 100;
                console.log('LOADED total pos.promotion.multilevel.condition ' + this.total_pos_promotion_multilevel_condition )
                this.total_pos_promotion_multilevel_condition_ids = this.total_pos_promotion_multilevel_condition_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'pos.promotion.multilevel.gift') {
                this.total_pos_promotion_multilevel_gift  += results.length;
                let process_time = this.get_process_time(this.total_pos_promotion_multilevel_gift, this.model_ids[model]['count']) * 100;
                console.log('LOADED total pos.promotion.multilevel.gift ' + this.total_pos_promotion_multilevel_gift )
                this.total_pos_promotion_multilevel_gift_ids = this.total_pos_promotion_multilevel_gift_ids.concat(_.pluck(results, 'id'))
            }
            // End Promotions
            

            if (model == 'pos.order') {
                this.total_pos_order += results.length;
                let process_time = this.get_process_time(this.total_pos_order, this.model_ids[model]['count']) * 100;
                console.log('LOADED total pos_order ' + this.total_pos_order)
                this.posorder_ids = this.posorder_ids.concat(_.pluck(results, 'id'))
            }
            if (model == 'pos.order.line') {
                this.total_pos_order_line += results.length;
                let process_time = this.get_process_time(this.total_pos_order_line, this.model_ids[model]['count']) * 100;
                console.log('LOADED total pos_order_line ' + this.total_pos_order_line)
                this.posorderline_ids = this.posorderline_ids.concat(_.pluck(results, 'id'))
            }

            // Start Invoices
            if (model == 'account.move') {
                this.total_account_move += results.length;
                let process_time = this.get_process_time(this.total_account_move, this.model_ids[model]['count']) * 100;
                console.log('LOADED total account_move ' + this.total_account_move);
                this.account_move_ids = this.account_move_ids.concat(_.pluck(results, 'id'));
            }
            if (model == 'account.move.line') {
                this.total_account_move_line += results.length;
                let process_time = this.get_process_time(this.total_account_move_line, this.model_ids[model]['count']) * 100;
                console.log('LOADED total account_move_line ' + this.total_account_move_line);
                this.account_move_line_ids = this.account_move_line_ids.concat(_.pluck(results, 'id'));
            }
            // End Invoices

            let object = _.find(this.model_lock, function (object_loaded) {
                return object_loaded.model == model;
            });
            if (object) {
                try {
                    object.loaded(this, results, {})
                } catch (e) {
                    console.error(e)
                }
            } else {
                console.error('Could not find model: ' + model + ' for restoring datas');
                return false;
            }

            this.load_datas_cache = true;
            this.db.set_last_write_date_by_model(model, results);
            this.indexed_db.data_by_model[model] = null

        },
        api_install_datas: function (model_name) {
            let self = this;
            var pos_config_location = [self.config.stock_location_id[0]]
            for (let iloc = 0; iloc < self.config.stock_location_ids.length; iloc++) {
                    var loc_id = self.config.stock_location_ids[iloc]
                    if(self.config.stock_location_ids.indexOf(loc_id) <= 0 ){
                        pos_config_location.push(loc_id)
                    }
            }

            self.db.update_state_load_models(model_name);

            let installed = new Promise(function (resolve, reject) {
                function installing_data(model_name, min_id, max_id) {
                    self.setLoadingMessage(_t('Installing Model: ' + model_name + ' from ID: ' + min_id + ' to ID: ' + max_id));
                    let model = _.find(self.model_lock, function (model) {
                        return model.model == model_name;
                    });
                    if (min_id == 0) {
                        max_id = self.max_load;
                    }
                    self.rpc({
                        model: 'pos.cache.database',
                        method: 'install_data',
                        args: [null, model_name, min_id, max_id,self.config.id],
                        context: {
                            'pricelist_id': _.pluck(self.pricelists, 'id'),
                            'posconfig_id': self.config.id,
                            'location': pos_config_location,
                        }
                    }).then(function (results) {
                        min_id += self.next_load;
                        if (typeof results == "string") {
                            results = JSON.parse(results);
                        }
                        if (results.length > 0) {
                            max_id += self.next_load;
                            installing_data(model_name, min_id, max_id);
                            self.indexed_db.write(model_name, results);
                            self.save_results(model_name, results);

                        } else {
                            if (max_id < model['max_id']) {
                                max_id += self.next_load;
                                installing_data(model_name, min_id, max_id);
                            } else {
                                resolve()
                            }
                        }
                    }, function (error) {
                        console.error(error.message.message);
                        self.remove_indexed_db();
                        reject(error)
                    })
                    
                }

                installing_data(model_name, 0, self.first_load);
            });
            return installed;
        },
        remove_indexed_db: function () {
            let dbName = this.session.db;
            for (let i = 0; i <= 100; i++) {
                indexedDB.deleteDatabase(dbName + '_' + i);
            }
            console.warn('[remove_indexed_db] remove indexedDB!')
        },

        saveQueryLog(key, result) {
            console.warn('saving log of key: ' + key)
            rpc.query({
                model: 'pos.query.log',
                method: 'updateQueryLogs',
                args: [[], {
                    'key': key,
                    'result': result
                }],
            })
        },

        load_server_data_from_cache: async function (refeshCache = false, needLoaded = false) {
            const currentPosSessionId = await PosIDB.get('pos_session_id')
            const queryLogs = this.session.queryLogs
            var self = this;
            var progress = 0;
            var progress_step = 1.0 / self.models.length;
            var tmp = {}; // this is used to share a temporary state between models loaders
            const loaded = new Promise(function (resolve, reject) {
                async function load_model(index) {
                    if (index >= self.models.length) {
                        resolve();
                    } else {
                        var model = self.models[index];
                        var cond = typeof model.condition === 'function' ? model.condition(self, tmp) : true;
                        if (!cond) {
                            load_model(index + 1);
                            return;
                        }
                        if (!refeshCache && !needLoaded) {
                            self.setLoadingMessage(_t('Loading') + ' ' + (model.label || model.model || ''), progress);
                        }
                        var fields = typeof model.fields === 'function' ? model.fields(self, tmp) : model.fields;
                        var domain = typeof model.domain === 'function' ? model.domain(self, tmp) : model.domain;
                        var context = typeof model.context === 'function' ? model.context(self, tmp) : model.context || {};
                        var ids = typeof model.ids === 'function' ? model.ids(self, tmp) : model.ids;
                        var order = typeof model.order === 'function' ? model.order(self, tmp) : model.order;
                        progress += progress_step;
                        if (model.model) {
                            let modelCall = model.model
                            let requestString = JSON.stringify({
                                modelCall,
                                fields,
                                domain,
                                context,
                                ids,
                                order
                            });
                            var params = {
                                model: model.model,
                                context: _.extend(context, self.session.user_context || {}),
                            };

                            if (model.ids) {
                                params.method = 'read';
                                params.args = [ids, fields];
                            } else {
                                params.method = 'search_read';
                                params.domain = domain;
                                params.fields = fields;
                                params.orderBy = order;
                            }
                            model.key = requestString
                            // TODO: refeshCache if active is True, no need get data from cache, it mean only fetch server and save
                            // TODO: never save cache pos config and pos session
                            // TODO: if odoo.pos_session_id change, will refresh cache of local browse
                            if (!refeshCache && currentPosSessionId == odoo.pos_session_id && model.model != 'pos.config' && model.model != 'pos.session' && model.model != 'res.users') {
                                try {
                                    let result = await PosIDB.get(requestString)
                                    if (result == undefined && queryLogs[requestString]) {
                                        result = queryLogs[requestString]
                                    }
                                    if (result != undefined) {
                                        console.warn('Found ( ' + result.length + ' ) of ' + model.model + ' in Browse Cache.')
                                        Promise.resolve(model.loaded(self, result, tmp)).then(function () {
                                                load_model(index + 1);
                                            },
                                            function (err) {
                                                reject(err);
                                            });
                                    } else {
                                        self.rpc(params).then(function (result) {
                                            try { // catching exceptions in model.loaded(...)
                                                if (PosIDB.get('pos_session_id') !== odoo.pos_session_id) {
                                                    PosIDB.set('pos_session_id', odoo.pos_session_id);
                                                    PosIDB.set(requestString, result)
                                                }
                                                self.saveQueryLog(requestString, result)
                                                Promise.resolve(model.loaded(self, result, tmp))
                                                    .then(function () {
                                                            load_model(index + 1);
                                                        },
                                                        function (err) {
                                                            reject(err);
                                                        });
                                            } catch (err) {
                                                console.error(err.message, err.stack);
                                                reject(err);
                                            }
                                        }, function (err) {
                                            reject(err);
                                        });
                                    }

                                } catch (e) {
                                    console.warn('==> has error loading db POS-DB (indexedbd) get datas direct backend')
                                    if (queryLogs[requestString]) {
                                        let result = queryLogs[requestString]
                                        Promise.resolve(model.loaded(self, result, tmp)).then(function () {
                                                load_model(index + 1);
                                            },
                                            function (err) {
                                                reject(err);
                                            });
                                    } else {
                                        self.rpc(params).then(function (result) {
                                            try { // catching exceptions in model.loaded(...)
                                                if (currentPosSessionId == odoo.pos_session_id) {
                                                    PosIDB.set('pos_session_id', odoo.pos_session_id);
                                                    PosIDB.set(requestString, result)
                                                }
                                                self.saveQueryLog(requestString, result)
                                                Promise.resolve(model.loaded(self, result, tmp))
                                                    .then(function () {
                                                            load_model(index + 1);
                                                        },
                                                        function (err) {
                                                            reject(err);
                                                        });
                                            } catch (err) {
                                                console.error(err.message, err.stack);
                                                reject(err);
                                            }
                                        }, function (err) {
                                            reject(err);
                                        });
                                    }
                                }

                            } else {
                                self.rpc(params).then(function (result) {
                                    try { // catching exceptions in model.loaded(...)
                                        PosIDB.set('pos_session_id', odoo.pos_session_id);
                                        PosIDB.set(requestString, result)
                                        self.saveQueryLog(requestString, result)
                                        if (!needLoaded) {
                                            Promise.resolve(model.loaded(self, result, tmp))
                                                .then(function () {
                                                        load_model(index + 1);
                                                    },
                                                    function (err) {
                                                        reject(err);
                                                    });
                                        } else {
                                            Promise.resolve()
                                            load_model(index + 1);
                                        }

                                    } catch (err) {
                                        console.error(err.message, err.stack);
                                        reject(err);
                                    }
                                }, function (err) {
                                    reject(err);
                                });
                            }
                        } else if (model.loaded) {
                            try { // catching exceptions in model.loaded(...)
                                Promise.resolve(model.loaded(self, tmp))
                                    .then(function () {
                                            load_model(index + 1);
                                        },
                                        function (err) {
                                            reject(err);
                                        });
                            } catch (err) {
                                reject(err);
                            }
                        } else {
                            load_model(index + 1);
                        }
                    }
                }

                try {
                    return load_model(0);
                } catch (err) {
                    return Promise.reject(err);
                }
            });
            return loaded.then(function () {
                self.models = self.models.concat(self.model_lock);
                self.session.queryLogs = null
                if (self.config.qrcode_order_screen && self.config.sync_multi_session) {
                    self.listenEventConfirmPlaceOrderOfUsers = new listenEventConfirmPlaceOrderOfUsers(self);
                    self.listenEventConfirmPlaceOrderOfUsers.start();
                }
            });
        },
        load_server_data_from_iot: function (refeshCache = false, needLoaded = false) {
            const self = this;
            var progress = 0;
            var progress_step = 1.0 / self.models.length;
            var tmp = {}; // this is used to share a temporary state between models loaders
            const iotUrl = 'http://' + odoo.proxy_ip + ':8069'
            const iotConnection = new Session(void 0, iotUrl, {
                use_cors: true
            });
            var loaded = new Promise(function (resolve, reject) {
                async function load_model(index) {
                    if (index >= self.models.length) {
                        resolve();
                    } else {
                        var model = self.models[index];
                        var cond = typeof model.condition === 'function' ? model.condition(self, tmp) : true;
                        if (!cond) {
                            load_model(index + 1);
                            return;
                        }
                        if (!refeshCache && !needLoaded) {
                            self.setLoadingMessage(_t('Loading') + ' ' + (model.label || model.model || ''), progress);
                        }

                        var fields = typeof model.fields === 'function' ? model.fields(self, tmp) : model.fields;
                        var domain = typeof model.domain === 'function' ? model.domain(self, tmp) : model.domain;
                        var context = typeof model.context === 'function' ? model.context(self, tmp) : model.context || {};
                        var ids = typeof model.ids === 'function' ? model.ids(self, tmp) : model.ids;
                        var order = typeof model.order === 'function' ? model.order(self, tmp) : model.order;
                        progress += progress_step;

                        if (model.model) {
                            var params = {
                                model: model.model,
                                context: _.extend(context, self.session.user_context || {}),
                            };

                            if (model.ids) {
                                params.method = 'read';
                                params.args = [ids, fields];
                            } else {
                                params.method = 'search_read';
                                params.domain = domain;
                                params.fields = fields;
                                params.orderBy = order;
                            }
                            let modelCall = model.model
                            let requestString = JSON.stringify({
                                modelCall,
                                fields,
                                domain,
                                context,
                                ids,
                                order
                            });
                            let cacheResult = null
                            try {
                                cacheResult = await iotConnection.rpc('/hw_cache/get', {key: requestString})
                            } catch (e) {
                                console.error(e)
                            }
                            if (!cacheResult || refeshCache) {
                                self.rpc(params).then(function (result) {
                                    iotConnection.rpc('/hw_cache/save', {key: requestString, value: result})
                                    try { // catching exceptions in model.loaded(...)
                                        if (!needLoaded) {
                                            Promise.resolve(model.loaded(self, result, tmp))
                                                .then(function () {
                                                        load_model(index + 1);
                                                    },
                                                    function (err) {
                                                        reject(err);
                                                    });
                                        } else {
                                            Promise.resolve()
                                            load_model(index + 1);
                                        }

                                    } catch (err) {
                                        console.error(err.message, err.stack);
                                        reject(err);
                                    }
                                }, function (err) {
                                    reject(err);
                                });
                            } else {
                                try { // catching exceptions in model.loaded(...)
                                    if (!needLoaded) {
                                        Promise.resolve(model.loaded(self, cacheResult, tmp))
                                            .then(function () {
                                                    load_model(index + 1);
                                                },
                                                function (err) {
                                                    reject(err);
                                                });
                                    } else {
                                        Promise.resolve()
                                        load_model(index + 1);
                                    }
                                } catch (err) {
                                    console.error(err.message, err.stack);
                                    reject(err);
                                }
                            }
                        } else if (model.loaded) {
                            try { // catching exceptions in model.loaded(...)
                                Promise.resolve(model.loaded(self, tmp))
                                    .then(function () {
                                            load_model(index + 1);
                                        },
                                        function (err) {
                                            reject(err);
                                        });
                            } catch (err) {
                                reject(err);
                            }
                        } else {
                            load_model(index + 1);
                        }
                    }
                }

                try {
                    return load_model(0);
                } catch (err) {
                    return Promise.reject(err);
                }
            });
            return loaded.then(function () {
                self.models = self.models.concat(self.model_lock);
                if (self.config.qrcode_order_screen && self.config.sync_multi_session) {
                    self.listenEventConfirmPlaceOrderOfUsers = new listenEventConfirmPlaceOrderOfUsers(self);
                    self.listenEventConfirmPlaceOrderOfUsers.start();
                }
            });
        },
        set_currency_from_pricelist: function (refeshCache = false, needLoaded = false) {
            var self = this
            var currency_pricelist_id = self.default_pricelist.currency_id[0]
            self.currency = self.currencies.filter(c => c.id == currency_pricelist_id)[0]
        },
        // TODO: after 20.06.2021, use cached all request to Browse DB
        load_server_data: function (refeshCache = false, needLoaded = false) {
            console.log('--***--   BEGIN load_server_data ---***---')
            const self = this;

            // TODO: Load data from POS Cache SDK when module equip3_pos_cache installed
            if(self.db.pos_load_data_from_pos_cache_sdk){
                console.log('--***--   BEGIN load_server_data_from_pos_cache_sdk ---***---')
                return self.load_server_data_from_pos_cache_sdk(refeshCache, needLoaded).then(function () {
                    self.set_currency_from_pricelist();
                });
            }

            if (odoo.cache != 'browse' && odoo.cache != 'iot') {
                let dont_load_models = ['res.bank'];
                for (var i = self.models.length - 1; i >= 0; i--) {
                    if(dont_load_models.includes(self.models[i].model)){
                        console.log('[load_server_data] skip model: ', self.models[i].model)
                        self.models.splice(i, 1);
                    }
                }

                return _super_PosModel.load_server_data.apply(this, arguments).then(function () {
                    self.set_currency_from_pricelist()
                    self.models = self.models.concat(self.model_lock);
                });
            }

            console.log('[POS Config] active cache feature !!!')
            console.log('cache type: ' + odoo.cache)
            self.set_currency_from_pricelist()
            if (odoo.cache == 'iot') {
                return this.load_server_data_from_iot(refeshCache, needLoaded)
            } else {
                return this.load_server_data_from_cache(refeshCache, needLoaded)
            }

        },
    });
    db.include({
        init: function (options) {
            this._super(options);
            this.write_date_by_model = {};
            this.products_removed = [];
            this.partners_removed = [];
        },
        set_last_write_date_by_model: function (model, results) {
            /* TODO: this method overide method set_last_write_date_by_model of Databse.js
                We need to know last records updated (change by backend clients)
                And use field write_date compare datas of pos and datas of backend
                We are get best of write date and compare
             */
            for (let i = 0; i < results.length; i++) {
                let line = results[i];
                if (!this.write_date_by_model[model]) {
                    this.write_date_by_model[model] = line.write_date
                    if(!line.write_date){
                        console.warn('[set_last_write_date_by_model] write_date is undefined');
                    }
                    continue
                }
                if (this.write_date_by_model[model] != line.write_date && new Date(this.write_date_by_model[model]).getTime() < new Date(line.write_date).getTime()) {
                    this.write_date_by_model[model] = line.write_date
                    if(!line.write_date){
                        console.warn('[set_last_write_date_by_model] write_date is undefined.');
                    }
                    this.product_max_id = line['id']
                }
            }
            console.log('Last Write Date of model ' + model + ' is ' + this.write_date_by_model[model])
        },
        search_product_in_category: function (category_id, query) {
            let self = this;
            let results = this._super(category_id, query);
            results = _.filter(results, function (product) {
                return self.products_removed.indexOf(product['id']) == -1
            });
            return results;
        },
        get_product_by_category: function (category_id) {
            let self = this;
            let list = this._super(category_id);
            if (category_id == 0) {
                list = this.getAllProducts(this.limit)
            }
            list = _.filter(list, function (product) {
                return self.products_removed.indexOf(product['id']) == -1
            });
            if (window.posmodel.config.default_product_sort_by == 'a_z') {
                list = list.sort(window.posmodel.sort_by('display_name', false, function (a) {
                    if (!a) {
                        a = 'N/A';
                    }
                    return a.toUpperCase()
                }));
            } else if (window.posmodel.config.default_product_sort_by == 'z_a') {
                list = list.sort(window.posmodel.sort_by('display_name', true, function (a) {
                    if (!a) {
                        a = 'N/A';
                    }
                    return a.toUpperCase()
                }));
            } else if (window.posmodel.config.default_product_sort_by == 'low_price') {
                list = list.sort(window.posmodel.sort_by('lst_price', false, parseInt));
            } else if (window.posmodel.config.default_product_sort_by == 'high_price') {
                list = list.sort(window.posmodel.sort_by('lst_price', true, parseInt));
            } else if (window.posmodel.config.default_product_sort_by == 'pos_sequence') {
                list = list.sort(window.posmodel.sort_by('pos_sequence', true, parseInt));
            }
//            list = list.filter(p => p.sale_ok && p.available_in_pos)
            list = list.filter(p => p.available_in_pos)
            return list;
        },
        search_partner: function (query) {
            let self = this;
            let results = this._super(query);
            results = _.filter(results, function (partner) {
                if(typeof partner == 'undefined'){
                    return false;
                }
                return self.partners_removed.indexOf(partner['id']) == -1
            });
            return results;
        },
        get_partners_sorted: function (max_count) {
            // TODO: improved performace to big data partners , default odoo get 1000 rows, but we only allow default render 20 rows
            if (max_count && max_count >= 20) {
                max_count = 20;
            }
            let self = this;
            let results = this._super(max_count);
            results = _.filter(results, function (partner) {
                if(typeof partner == 'undefined'){
                    return false;
                }
                return self.partners_removed.indexOf(partner['id']) == -1
            });
            return results;
        },
    });

    models.load_models([
        {
            label: 'Reload Session',
            condition: function (self) {
                return self.pos_session.required_reinstall_cache;
            },
            loaded: function (self) {
                return self.reloadPosScreen()
            },
        },
        {
            label: 'Ping Cache Server',
            condition: function (self) {
                return odoo.cache == 'iot';
            },
            loaded: function (self) {
                const iotUrl = 'http://' + odoo.proxy_ip + ':8069'
                const iotConnection = new Session(void 0, iotUrl, {
                    use_cors: true
                });
                return iotConnection.rpc('/hw_cache/ping', {}).then(function (result) {
                    if (result == 'ping') {
                        console.log('Cache Server is running')
                    }
                }, function (error) {
                    alert('Could not connect to IOT IP Address:' + iotUrl)
                })
            },
        },
    ], {
        after: 'pos.config'
    });

    models.load_models([ 

        // Start: Pricelist Items
        {
            label: 'Pricelist Items - Cache Data',
            installed: true,
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                return true;
            },
            loaded: async function (self) {
                await self.indexed_db.get_datas('product.pricelist.item', 1);
                const pricelists = self.indexed_db.data_by_model['product.pricelist.item'];
                if (pricelists) {
                    await self.save_results('product.pricelist.item', pricelists);
                }
            }
        },
        {
            label: 'Installing Pricelist Items',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                return self.total_pricelists == 0 ;
            },
            loaded: function (self) {
                return self.api_install_datas('product.pricelist.item');
            }
        },
        {
            label: 'Pricelist Items - New Updated',
            installed: true,
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                return true;
            },
            loaded: async function (self) {
                await self.onLoadPosSyncPricelistItems();
            }
        },
        // End: Pricelist Items

        // Start: POS Orders
        {
            label: 'POS Orders - Cache Data',
            installed: true,
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                return true;
            },
            loaded: async function (self) {
                await self.indexed_db.get_datas('pos.order', 1);
                await self.indexed_db.get_datas('pos.order.line', 1);

                const pos_orders = self.indexed_db.data_by_model['pos.order']
                if (pos_orders) {
                    await self.save_results('pos.order', pos_orders)
                }
                const posline_orders = self.indexed_db.data_by_model['pos.order.line']
                if (posline_orders) {
                    await self.save_results('pos.order.line', posline_orders)
                }
            }
        },
        {
            label: 'Installing POS Orders',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                let loaded = self.db.get_state_load_models('pos.order');
                return self.total_pos_order == 0 && self.config.pos_orders_management && (loaded == false);
            },
            loaded: function (self) {
                return self.api_install_datas('pos.order')
            }
        },
        {
            label: 'Installing POS Orders Lines',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                let loaded = self.db.get_state_load_models('pos.order.line');
                return self.total_pos_order_line == 0 && self.config.pos_orders_management && (loaded == false);
            },
            loaded: function (self) {

                return self.api_install_datas('pos.order.line')
            }
        },
            /**
             * Skip get new update from database when Open POS for faster load
             * 
            {
                label: 'POS Orders - New Updated',
                installed: true,
                loaded: async function (self) {
                    
                }
            },
            */
        // End: POS Orders

        // Start: Partners
        {
            label: 'Partners - Cache Data',
            installed: true,
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                return true;
            },
            loaded: async function (self) {
                await self.indexed_db.get_datas('res.partner', 1);

                const partners = self.indexed_db.data_by_model['res.partner'];
                if (partners) {
                    await self.save_results('res.partner', partners);
                }
            }
        },
        {
            label: 'Installing Partners',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                let loaded = self.db.get_state_load_models('res.partner');
                return self.total_clients == 0 && (loaded == false);
            },
            loaded: function (self) {
                return self.api_install_datas('res.partner');
            }
        },
        {
            label: 'Partners - New Updated',
            installed: true,
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                return true;
            },
            loaded: async function (self) {
                await self.onLoadPosSyncPartners();
            }
        },
        // End: Partners

        // Start: Products
        {
            label: 'Products - Cache Data',
            installed: true,
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                return true;
            },
            loaded: async function (self) {
                await self.indexed_db.get_datas('product.product', 1);
                await self.indexed_db.get_datas('product.template', 1);
                await self.indexed_db.get_datas('product.template.barcode', 1);
                await self.indexed_db.get_datas('stock.quant', 1);
                await self.indexed_db.get_datas('product.brand', 1);
                await self.indexed_db.get_datas('stock.production.lot', 1);

                const products = self.indexed_db.data_by_model['product.product'];
                if (products) {
                    await self.save_results('product.product', products);
                }
                const product_templates = self.indexed_db.data_by_model['product.template'];
                if (product_templates) {
                    await self.save_results('product.template', product_templates);
                }
                const product_template_barcodes = self.indexed_db.data_by_model['product.template.barcode'];
                if (product_template_barcodes) {
                    await self.save_results('product.template.barcode', product_template_barcodes);
                }
                const stock_quants = self.indexed_db.data_by_model['stock.quant'];
                if (stock_quants) {
                    await self.save_results('stock.quant', stock_quants)
                }
                const product_brands = self.indexed_db.data_by_model['product.brand'];
                if (product_brands) {
                    await self.save_results('product.brand', product_brands);
                }
                const lots = self.indexed_db.data_by_model['stock.production.lot'];
                if (lots) {
                    await self.save_results('stock.production.lot', lots);
                }
            }
        },
        {
            label: 'Installing Products',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                return self.total_products == 0;
            },
            loaded: function (self) {
                self.first_install_cache = true
                return self.api_install_datas('product.product');
            }
        },
        {
            label: 'Installing Product Templates',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                return self.total_product_templates == 0 ;
            },
            loaded: function (self) {
                self.first_install_cache = true
                return self.api_install_datas('product.template');
            }
        },
        {
            label: 'Installing Product Template Barcode',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                return self.total_product_template_barcode == 0 ;
            },
            loaded: function (self) {
                return self.api_install_datas('product.template.barcode');
            }
        },
        {
            label: 'Installing Stock Quant',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                return self.total_stock_quant == 0 ;
            },
            loaded: function (self) {
                return self.api_install_datas('stock.quant');
            }
        },
        {
            label: 'Installing Product Brand',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                return self.total_product_brand == 0 ;
            },
            loaded: function (self) {
                return self.api_install_datas('product.brand');
            }
        },
        {
            label: 'Installing Stock Production Lots',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                return self.total_lots == 0 ;
            },
            loaded: function (self) {
                return self.api_install_datas('stock.production.lot');
            }
        },
        {
            label: 'Products - New Updated',
            installed: true,
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                return true;
            },
            loaded: async function (self) {
                await self.onLoadPosSyncProducts();
            }
        },
        // End: Products

        // Start: Vouchers
        {
            label: 'Installing Vouchers',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                return self.total_pos_voucher == 0 ;
            },
            loaded: function (self) {
                return self.api_install_datas('pos.voucher');
            }
        },
            /**
             * Skip get new update from database when Open POS for faster load
             * 
            {
                label: 'Vouchers - New Updated',
                installed: true,
                loaded: async function (self) {
                    
                }
            },
            */
        // End: Vouchers

        // Start POS Invoices
        {
            label: 'Invoices - Cache Data',
            installed: true,
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                return self.config.management_invoice;
            },
            loaded: async function (self) {
                await self.indexed_db.get_datas('account.move', 1);
                await self.indexed_db.get_datas('account.move.line', 1);
                
                const account_moves = self.indexed_db.data_by_model['account.move'];
                if (account_moves) {
                    await self.save_results('account.move', account_moves);
                }

                const account_move_lines = self.indexed_db.data_by_model['account.move.line'];
                if (account_move_lines) {
                    await self.save_results('account.move.line', account_move_lines);
                }
            }
        },
        {
            label: 'Installing Invoices (account.move)',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                return self.total_account_move == 0 && self.config.management_invoice;
            },
            loaded: function (self) {
                return self.api_install_datas('account.move');
            }
        },
        {
            label: 'Installing Invoice Lines (account.move.line)',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                return self.total_account_move_line == 0 && self.config.management_invoice;
            },
            loaded: function (self) {
                return self.api_install_datas('account.move.line');
            }
        },
            /**
             * Skip get new update from database when Open POS for faster load
             * 
            {
                label: 'Invoices - New Updated',
                installed: true,
                loaded: async function (self) {
                    
                }
            },
            */
        // End POS Invoices

        // Start POS Promotions
        {
            label: 'Installing Promotions (pos.promotion)',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                if(self.config.is_force_sync_promotion){
                    return false;
                }
                let loaded = self.db.get_state_load_models('pos.promotion');
                return self.total_pos_promotion == 0 && (loaded == false);
            },
            loaded: function (self) {
                return self.api_install_datas('pos.promotion')
            }
        },
        {
            label: 'Installing Promotions (pos.promotion.discount.order)',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                if(self.config.is_force_sync_promotion){
                    return false;
                }
                let loaded = self.db.get_state_load_models('pos.promotion.discount.order');
                return self.total_pos_promotion_discount_order == 0 && (loaded == false);
            },
            loaded: function (self) {
                return self.api_install_datas('pos.promotion.discount.order')
            }
        },
        {
            label: 'Installing Promotions (pos.promotion.discount.category)',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                if(self.config.is_force_sync_promotion){
                    return false;
                }
                let loaded = self.db.get_state_load_models('pos.promotion.discount.category');
                return self.total_pos_promotion_discount_category == 0 && (loaded == false);
            },
            loaded: function (self) {
                return self.api_install_datas('pos.promotion.discount.category')
            }
        },
        {
            label: 'Installing Promotions (pos.promotion.discount.quantity)',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                if(self.config.is_force_sync_promotion){
                    return false;
                }
                let loaded = self.db.get_state_load_models('pos.promotion.discount.quantity');
                return self.total_pos_promotion_discount_quantity == 0 && (loaded == false);
            },
            loaded: function (self) {
                return self.api_install_datas('pos.promotion.discount.quantity')
            }
        },
        {
            label: 'Installing Promotions (pos.promotion.gift.condition)',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                if(self.config.is_force_sync_promotion){
                    return false;
                }
                let loaded = self.db.get_state_load_models('pos.promotion.gift.condition');
                return self.total_pos_promotion_gift_condition == 0 && (loaded == false);
            },
            loaded: function (self) {
                return self.api_install_datas('pos.promotion.gift.condition')
            }
        },
        {
            label: 'Installing Promotions (pos.promotion.gift.free)',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                if(self.config.is_force_sync_promotion){
                    return false;
                }
                let loaded = self.db.get_state_load_models('pos.promotion.gift.free');
                return self.total_pos_promotion_gift_free == 0 && (loaded == false);
            },
            loaded: function (self) {
                return self.api_install_datas('pos.promotion.gift.free')
            }
        },
        {
            label: 'Installing Promotions (pos.promotion.discount.condition)',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                if(self.config.is_force_sync_promotion){
                    return false;
                }
                let loaded = self.db.get_state_load_models('pos.promotion.discount.condition');
                return self.total_pos_promotion_discount_condition == 0 && (loaded == false);
            },
            loaded: function (self) {
                return self.api_install_datas('pos.promotion.discount.condition')
            }
        },
        {
            label: 'Installing Promotions (pos.promotion.discount.apply)',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                if(self.config.is_force_sync_promotion){
                    return false;
                }
                let loaded = self.db.get_state_load_models('pos.promotion.discount.apply');
                return self.total_pos_promotion_discount_apply == 0 && (loaded == false);
            },
            loaded: function (self) {
                return self.api_install_datas('pos.promotion.discount.apply')
            }
        },
        {
            label: 'Installing Promotions (pos.promotion.special.category)',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                if(self.config.is_force_sync_promotion){
                    return false;
                }
                let loaded = self.db.get_state_load_models('pos.promotion.special.category');
                return self.total_pos_promotion_special_category == 0 && (loaded == false);
            },
            loaded: function (self) {
                return self.api_install_datas('pos.promotion.special.category')
            }
        },
        {
            label: 'Installing Promotions (pos.promotion.selected.brand)',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                if(self.config.is_force_sync_promotion){
                    return false;
                }
                let loaded = self.db.get_state_load_models('pos.promotion.selected.brand');
                return self.total_pos_promotion_selected_brand == 0 && (loaded == false);
            },
            loaded: function (self) {
                return self.api_install_datas('pos.promotion.special.category')
            }
        },
        {
            label: 'Installing Promotions (pos.promotion.tebus.murah.selected.brand)',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                if(self.config.is_force_sync_promotion){
                    return false;
                }
                let loaded = self.db.get_state_load_models('pos.promotion.tebus.murah.selected.brand');
                return self.total_pos_promotion_tebus_murah_selected_brand == 0 && (loaded == false);
            },
            loaded: function (self) {
                return self.api_install_datas('pos.promotion.special.category')
            }
        },
        {
            label: 'Installing Promotions (pos.promotion.specific.product)',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                if(self.config.is_force_sync_promotion){
                    return false;
                }
                let loaded = self.db.get_state_load_models('pos.promotion.specific.product');
                return self.total_pos_promotion_specific_product == 0 && (loaded == false);
            },
            loaded: function (self) {
                return self.api_install_datas('pos.promotion.specific.product')
            }
        },
        {
            label: 'Installing Promotions (pos.promotion.multi.buy)',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                if(self.config.is_force_sync_promotion){
                    return false;
                }
                let loaded = self.db.get_state_load_models('pos.promotion.multi.buy')
                return self.total_pos_promotion_multi_buy == 0 && (loaded == false);
            },
            loaded: function (self) {
                return self.api_install_datas('pos.promotion.multi.buy')
            }
        },
        {
            label: 'Installing Promotions (pos.promotion.price)',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                if(self.config.is_force_sync_promotion){
                    return false;
                }
                let loaded = self.db.get_state_load_models('pos.promotion.price')
                return self.total_pos_promotion_price == 0 && (loaded == false);
            },
            loaded: async function (self) {
                return self.api_install_datas('pos.promotion.price')
            }
        },
        {
            label: 'Installing Promotions (pos.promotion.tebus.murah)',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                if(self.config.is_force_sync_promotion){
                    return false;
                }
                let loaded = self.db.get_state_load_models('pos.promotion.tebus.murah')
                return self.total_pos_promotion_tebus_murah == 0 && (loaded == false);
            },
            loaded: async function (self) {
                return self.api_install_datas('pos.promotion.tebus.murah')
            }
        },
        {
            label: 'Installing Promotions (pos.promotion.multilevel.condition)',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                if(self.config.is_force_sync_promotion){
                    return false;
                }
                let loaded = self.db.get_state_load_models('pos.promotion.multilevel.condition')
                return self.total_pos_promotion_multilevel_condition == 0 && (loaded == false);
            },
            loaded: async function (self) {
                return self.api_install_datas('pos.promotion.multilevel.condition')
            }
        },
        {
            label: 'Installing Promotions (pos.promotion.multilevel.gift)',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                if(self.config.is_force_sync_promotion){
                    return false;
                }
                let loaded = self.db.get_state_load_models('pos.promotion.multilevel.gift')
                return self.total_pos_promotion_multilevel_gift == 0 && (loaded == false);
            },
            loaded: async function (self) {
                return self.api_install_datas('pos.promotion.multilevel.gift')
            }
        },
        {
            label: 'Promotions - New Updated',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                if(self.config.is_force_sync_promotion){
                    return false;
                }
                return true;
            },
            loaded: async function (self) {
                await self.onLoadPosSyncPromotions();
            }
        },
        {
            label: 'Force Sync Promotions',
            condition: function (self) {
                if(self.db.pos_load_data_from_pos_cache_sdk){
                    return false;
                }
                if(self.config.is_force_sync_promotion){
                    return true;
                }
                return false;
            },
            loaded: async function (self) {
                console.warn('[onLoadForceSyncPromotions] -> Start');
                let results = await self.rpc({
                    model: 'pos.cache.database',
                    method: 'onLoadForceSyncPromotions',
                    args: [[], self.config.id],
                }, {
                    shadow: true,
                    timeout: 1200000 // 20 minutes
                });
                for (let model in results) {
                    let count_update = 0;
                    let vals = results[model];
                    for (let i = 0; i < vals.length; i++) {
                        vals[i].model = model;
                        if (vals[i].active == false) {
                            self.indexed_db.unlink(model, vals[i]);
                        }
                    }
                    vals = vals.filter(r => r['active'] == true);
                    if (vals && vals.length) {
                        count_update += vals.length;
                        self.indexed_db.write(model, vals);
                        self.save_results(model, vals)
                    }
                    console.warn('[onLoadForceSyncPromotions] Total update '+ model +' from Backend: ' + count_update);
                }
            }
        },
        // End POS Promotions

        {
            label: 'POS Payment',
            model: 'pos.payment',
            fields: [
                'payment_date',
                'pos_order_id',
                'amount',
                'payment_method_id',
                'name',
            ],
            domain: function (self) {
                return [['pos_order_id', 'in', self.order_ids]]
            },
            loaded: function (self, payments) {
                if(!self.pos_payment_by_order_id){
                    self.pos_payment_by_order_id = {}
                }
                for (let payment of payments){
                    let order_id = payment.pos_order_id[0];
                    let order = self.db.order_by_id[order_id];
                    if(order){
                        order['payments'].push(payment);
                    }
                    if (!self.pos_payment_by_order_id[order_id]) {
                        self.pos_payment_by_order_id[order_id] = [payment];
                    } else {
                        self.pos_payment_by_order_id[order_id].push(payment);
                    }
                }
            }
        }, {
            label: 'POS Pack Operation Lot',
            model: 'pos.pack.operation.lot',
            fields: [
                'lot_name',
                'pos_order_line_id',
                'product_id',
                'lot_id',
                'quantity',
            ],
            domain: function (self) {
                return [['pos_order_line_id', 'in', self.orderline_ids]]
            },
            condition: function (self) {
                return self.config.pos_orders_management;
            },
            loaded: function (self, pack_operation_lots) {
                self.pack_operation_lots = pack_operation_lots;
                self.pack_operation_lots_by_pos_order_line_id = {};
                for (let i = 0; i < pack_operation_lots.length; i++) {
                    let pack_operation_lot = pack_operation_lots[i];
                    if (!pack_operation_lot.pos_order_line_id) {
                        continue
                    }
                    if (!self.pack_operation_lots_by_pos_order_line_id[pack_operation_lot.pos_order_line_id[0]]) {
                        self.pack_operation_lots_by_pos_order_line_id[pack_operation_lot.pos_order_line_id[0]] = [pack_operation_lot]
                    } else {
                        self.pack_operation_lots_by_pos_order_line_id[pack_operation_lot.pos_order_line_id[0]].push(pack_operation_lot)
                    }
                }
            }
        }, {
            label: 'Sale Orders',
            model: 'sale.order',
            fields: [
                'create_date',
                'pos_config_id',
                'pos_location_id',
                'name',
                'origin',
                'client_order_ref',
                'state',
                'warehouse_id',
                'pos_branch_id',
                'date_order',
                'validity_date',
                'user_id',
                'partner_id',
                'pricelist_id',
                'invoice_ids',
                'partner_shipping_id',
                'payment_term_id',
                'note',
                'amount_tax',
                'amount_total',
                'picking_ids',
                'delivery_address',
                'delivery_date',
                'delivery_phone',
                'book_order',
                'is_self_pickup',
                'delivered_state',
                'payment_partial_amount',
                'payment_partial_method_id',
                'write_date',
                'ean13',
                'write_date',

                'ean13',
                'pos_order_id',
            ],
            domain: function (self) {
                return [['pos_order_id', '=', false]];
            },
            context: function (self) {
                return {pos_config_id: self.config.id}
            },
            loaded: function (self, orders) {
                self.saveSaleOrders(orders)
            }
        }, {
            model: 'sale.order.line',
            fields: [
                'name',
                'discount',
                'product_id',
                'order_id',
                'price_unit',
                'price_subtotal',
                'price_tax',
                'price_total',
                'product_uom',
                'product_uom_qty',
                'qty_delivered',
                'qty_invoiced',
                'tax_id',
                // 'variant_ids',
                'state',
                'write_date'
            ],
            domain: function (self) {
                return [['order_id', 'in', self.booking_ids]]
            },
            context: {'pos': true},
            loaded: function (self, order_lines) {
                self.saveSaleOrderLines(order_lines)
            }
        },
        {
            model: 'coupon.program',
            fields: [
                'name',
                'rule_id',
                'reward_id',
                'sequence',
                'maximum_use_number',
                'program_type',
                'promo_code_usage',
                'promo_code',
                'promo_applicability',
                'coupon_ids',
                'coupon_count',
                'validity_duration',
                'gift_product_id',
                'company_id'
            ],
            condition: function (self) {
                return self.config.load_coupon_program
            },
            domain: function (self) {
                return [
                    ['company_id', '=', self.company.id]
                ]
            },
            loaded: function (self, couponPrograms) {
                self.couponGiftCardTemplate = [];
                self.couponProgramsAutomatic = [];
                self.couponRule_ids = [];
                self.couponReward_ids = [];
                self.couponProgram_by_code = {};
                self.couponProgram_by_id = {};
                self.couponProgram_ids = [];
                self.couponPrograms = couponPrograms;
                self.couponPrograms.forEach(p => {
                    if (!self.couponRule_ids.includes(p.rule_id[0])) {
                        self.couponRule_ids.push(p.rule_id[0])
                    }
                    if (!self.couponReward_ids.includes(p.rule_id[0])) {
                        self.couponReward_ids.push(p.reward_id[0])
                    }
                    if (p.promo_code) {
                        self.couponProgram_by_code[p.promo_code] = p
                    }
                    self.couponProgram_by_id[p.id] = p;
                    self.couponProgram_ids.push(p.id)
                    if (self.config.coupon_program_ids.includes(p.id)) {
                        self.couponProgramsAutomatic.push(p)
                    }
                    if (self.config.coupon_giftcard_ids.includes(p.id)) {
                        self.couponGiftCardTemplate.push(p)
                    }
                })

            }
        },
        {
            label: 'Coupons',
            model: 'coupon.coupon',
            fields: [
                'code',
                'expiration_date',
                'state',
                'partner_id',
                'program_id',
                'discount_line_product_id',
                'is_gift_card',
                'is_returned_order',
                'base_amount',
                'balance_amount',
                'redeem_amount',
            ],
            domain: function (self) {
                return [['state', 'in', ['new', 'sent']], ['program_id', 'in', self.couponProgram_ids]]
            },
            loaded: function (self, coupons) {
                self.coupons = coupons;
                self.coupon_by_code = {};
                self.coupon_by_id = {};
                self.coupon_ids = [];
                self.coupons_by_partner_id = {}
                self.coupons.forEach(c => {
                    self.coupon_by_id[c.id] = c;
                    self.coupon_ids.push(c.id)
                    self.coupon_by_code[c.code] = c
                    if (c.partner_id) {
                        if (!self.coupons_by_partner_id[c.partner_id[0]]) {
                            self.coupons_by_partner_id[c.partner_id[0]] = [c]
                        } else {
                            self.coupons_by_partner_id[c.partner_id[0]].push(c)
                        }
                    }
                })
            }
        },
        {
            label: 'Coupon Rules',
            model: 'coupon.rule',
            fields: [
                'rule_date_from',
                'rule_date_to',
                'rule_partners_domain',
                'rule_products_domain',
                'rule_min_quantity',
                'rule_minimum_amount',
                'rule_minimum_amount_tax_inclusion',
                'applied_partner_ids',
                'applied_product_ids',
            ],
            domain: function (self) {
                return [['id', 'in', self.couponRule_ids]]
            },
            loaded: function (self, couponRules) {
                self.couponRules = couponRules;
                self.couponRule_by_id = {};
                self.couponRule_ids = [];
                self.couponRules.forEach(r => {
                    self.couponRule_by_id[r.id] = r;
                    self.couponRule_ids.push(r.id)
                    if(self.couponPrograms){
                        let program = self.couponPrograms.find(p => p.rule_id[0] == r.id)
                        if (program) {
                            program.rule = r
                        }
                    }
                })

            }
        },
        {
            model: 'coupon.reward',
            fields: [
                'reward_type',
                'reward_product_id',
                'reward_product_quantity',
                'discount_type',
                'discount_percentage',
                'discount_apply_on',
                'discount_specific_product_ids',
                'discount_max_amount',
                'discount_fixed_amount',
                'discount_line_product_id',
            ],
            domain: function (self) {
                return [['id', 'in', self.couponReward_ids]]
            },
            loaded: function (self, couponRewards) {
                self.couponRewards = couponRewards;
                self.couponReward_by_id = {};
                self.couponReward_ids = [];
                self.couponRewards.forEach(rw => {
                    self.couponReward_by_id[rw.id] = rw;
                    self.couponReward_ids.push(rw.id)
                    if(self.couponPrograms){
                        let program = self.couponPrograms.find(p => p.reward_id[0] == rw.id)
                        if (program) {
                            program.reward = rw
                        }
                    }
                })
            }
        },
        {
            label: 'Vouchers',
            model: 'pos.voucher', // load vouchers
            fields: ['write_date', 'active', 'code', 'value', 'apply_type', 'method', 'number'],
            domain: function (self) {
                let current_date = moment().utc().format('YYYY-MM-DD 00:00:00');
                console.log('LOADED Vouchers is after: ', current_date)
                return [['end_date','>', current_date], ['state','=', 'active']]
            },
            context: {'pos': true},
            loaded: function (self, vouchers) {
                self.vouchers = vouchers;
                self.voucher_by_id = {};
                for (let x = 0; x < vouchers.length; x++) {
                    self.voucher_by_id[vouchers[x].id] = vouchers[x];
                }
            }
        },
    ]);

    models.load_models({
        model: 'pos.order',
        fields: [
            'create_date',
            'name',
            'date_order',
            'user_id',
            'amount_tax',
            'amount_total',
            'amount_paid',
            'amount_return',
            'pricelist_id',
            'partner_id',
            'sequence_number',
            'session_id',
            'state',
            'account_move',
            'picking_ids',
            'picking_type_id',
            'location_id',
            'note',
            'nb_print',
            'pos_reference',
            'payment_journal_id',
            'fiscal_position_id',
            'ean13',
            'expire_date',
            'is_return',
            'is_returned',
            'voucher_id',
            'email',
            'write_date',
            'config_id',
            'is_paid_full',
            'session_id',
            'shipping_id',
            'payment_paid',
            'active',
        ],
        condition: function (self) {
            return self.config.pos_orders_management;
        },
        domain: function (self) {
            let domain = [];
            return domain
        },
        loaded: function (self, orders) {
            self.savePosOrders(orders)
        }
    })


    models.load_models({
        model: 'pos.order.line',
        fields: [
            'name',
            'notice',
            'product_id',
            'price_unit',
            'qty',
            'price_subtotal',
            'price_subtotal_incl',
            'discount',
            'order_id',
            'promotion',
            'promotion_id', //TODO: for return order
            'promotion_reason',
            'is_return',
            'uom_id',
            'user_id',
            'note',
            'discount_reason',
            'create_uid',
            'write_date',
            'create_date',
            'config_id',
            'returned_qty',
            'pack_lot_ids',
            'active',
            'pos_coupon_id',
            'pos_coupon_reward_description',
        ],
        condition: function (self) {
            return self.config.pos_orders_management;
        },
        domain: function (self) {
            return [['order_id', 'in', self.order_ids]]
        },
        loaded: function (self, order_lines) {
            self.savePosOrderLines(order_lines)
        }
    });


    models.load_models([
        {
            model: 'account.move',
            fields: [
                'create_date',
                'name',
                'date',
                'ref',
                'state',
                'move_type',
                'auto_post',
                'journal_id',
                'partner_id',
                'amount_tax',
                'amount_total',
                'amount_untaxed',
                'amount_residual',
                'invoice_user_id',
                'payment_reference',
                'payment_state',
                'invoice_date',
                'invoice_date_due',
                'invoice_payment_term_id',
                'stock_move_id',
                'write_date',
                'currency_id',
            ],
            condition: function (self) {
                let loaded = self.db.get_state_load_models('account.move');
                return self.config.management_invoice && (loaded == false);
            },
            context: function (self) {
                return {pos_config_id: self.config.id}
            },
            loaded: function (self, moves) {
                self.saveMoves(moves)
            },
        },
        {
            model: 'account.move.line',
            fields: [
                'move_id',
                'move_name',
                'date',
                'ref',
                'journal_id',
                'account_id',
                'sequence',
                'name',
                'quantity',
                'price_unit',
                'discount',
                'debit',
                'credit',
                'balance',
                'price_subtotal',
                'price_total',
                'write_date'
            ],
            condition: function (self) {
                let loaded = self.db.get_state_load_models('account.move.line');
                return self.config.management_invoice && (loaded == false);
            },
            loaded: function (self, invoice_lines) {
                self.db.save_invoice_lines(invoice_lines);
            },
        },
    ]);


    let _super_Order = models.Order.prototype;
    models.Order = models.Order.extend({
        set_client: function (client) {
            var order = this.pos.get_order()
            if(order){
                client_old = order.get_client()
                if(client_old && client && client_old.id != client['id']) {
                    order.remove_all_promotion_line();
                    this.pos.apply_promotion_succeed = false;
                }
            }
            
            if (!this.pos.the_first_load && client && client['id'] && this.pos.deleted['res.partner'] && this.pos.deleted['res.partner'].indexOf(client['id']) != -1) {
                client = null;
                return this.env.pos.alert_message({
                    title: this.env._t('Warning'),
                    body: this.env._t('This client deleted from backend')
                })
            }
            _super_Order.set_client.apply(this, arguments);
        },
    });

    let _SuperOrderLine = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
        initialize: function(attr,options) {
            _SuperOrderLine.initialize.apply(this,arguments);
            this.sync_line_id = this.sync_line_id || false;
        },
        init_from_JSON: function(json) {
            _SuperOrderLine.init_from_JSON.apply(this, arguments);
            this.sync_line_id = json.sync_line_id;
        },
        export_as_JSON: function() {
            var res = _SuperOrderLine.export_as_JSON.apply(this, arguments);
            res['sync_line_id'] = this.sync_line_id;
            return res;
        },
        clone: function () {
            let res = _SuperOrderLine.clone.call(this);
            res.sync_line_id = this.sync_line_id;
            return res;
        },
        export_for_printing: function(){
            var res = _SuperOrderLine.export_for_printing.apply(this, arguments);
            res['sync_line_id'] = this.sync_line_id;
            return res;
        },
    });


});