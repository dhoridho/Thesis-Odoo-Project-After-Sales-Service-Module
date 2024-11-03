
odoo.define('equip3_pos_masterdata.load_models', function (require) {
    const models = require('point_of_sale.models');
    const time = require('web.time');
    const exports = {};
    const Backbone = window.Backbone;
    const bus = require('equip3_pos_masterdata.core_bus');
    const core = require('web.core');
    const _t = core._t;
    const session = require('web.session');
    const rpc = require('web.rpc');
    const ERROR_DELAY = 30000;
    const hr = require('pos_hr.employees')
    const {posbus} = require('point_of_sale.utils');
    const BigData = require('equip3_pos_masterdata.big_data');

    exports.posSyncBackend = Backbone.Model.extend({
        initialize: function (pos) {
            this.pos = pos;
        },
        start: function () {
            this.bus = bus.bus;
            this.bus.last = this.pos.db.load('bus_last', 0);
            this.bus.on("notification", this, this.on_notification);
            this.bus.start_polling();
        },
        force_update_ui: function (config) {
            this.pos.session['config'] = config
            this.pos.chrome.env.qweb.forceUpdate();
        },

        async on_notification(notifications) {
            if (notifications && notifications[0] && notifications[0][1]) {
                for (let i = 0; i < notifications.length; i++) {
                    let channel = notifications[i][0][1];
                    if (channel == 'pos.modifiers.background') {
                        this.force_update_ui(JSON.parse(notifications[i][1]))
                    }
                }
            }
        }
    });

    models.load_models([
        {
            model: 'pos.epson',
            fields: ['name', 'ip'],
            loaded: function (self, epson_printers) {
                self.epson_printer_default = null;
                self.epson_printers = [];
                self.epson_priner_by_id = {};
                self.epson_priner_by_ip = {};
                for (let i = 0; i < epson_printers.length; i++) {
                    self.epson_priner_by_id[epson_printers[i]['id']] = epson_printers[i];
                    self.epson_priner_by_ip[epson_printers[i]['ip']] = epson_printers[i];
                }
                // TODO: if pos have set printer_id, will use it for default print receipt
                let printer_id = self.config.printer_id;
                if (printer_id) {
                    let epson_printer_default = _.find(epson_printers, function (epson_printer) {
                        return epson_printer.id == printer_id[0];
                    });
                    if (epson_printer_default) {
                        epson_printer_default['print_receipt'] = true;
                        self.epson_printer_default = epson_printer_default;
                        self.epson_printers.push(epson_printer_default);
                    }
                }
            },
        },
        {
            model: 'pos.service.charge',
            fields: ['name', 'product_id', 'type', 'amount'],
            condition: function (self) {
                return self.config.service_charge_ids && self.config.service_charge_ids.length;
            },
            domain: function (self) {
                return [
                    ['id', 'in', self.config.service_charge_ids],
                ]
            },
            loaded: function (self, services_charge) {
                self.services_charge = services_charge;
                self.services_charge_ids = [];
                self.service_charge_by_id = {};
                for (let i = 0; i < services_charge.length; i++) {
                    let service = services_charge[i];
                    self.services_charge_ids.push(service.id);
                    self.service_charge_by_id[service.id] = service;
                }
            }
        },
        {
            model: 'res.bank',
            fields: ['name'],
            loaded: function (self, banks) {
                self.banks = banks;
                self.bank_by_id = {};
                for (let i = 0; i < banks.length; i++) {
                    let bank = banks[i];
                    self.bank_by_id[bank.id] = bank;
                }
            }
        },
        {
            model: 'res.lang',
            fields: ['name', 'code'],
            loaded: function (self, langs) {
                self.langs = langs
                self.lang_selected = langs.find(l => l.code == self.user.lang)
            }
        },

        {
            label: 'POS Coupon',
            model: 'pos.coupon',
            fields: [
                'write_date',
                'name',
                'number',
                'code',
                'type_apply',
                'product_ids',
                'minimum_purchase_quantity',
                'sequence_generate_method',
                'manual_input_sequence',
                'start_date',
                'end_date',
                'no_of_usage',
                'no_of_used',
                'coupon_program_id',
                'company_id',
                'state',
                'reward_type',
                'reward_product_ids',
                'reward_quantity',
                'reward_discount_type',
                'reward_discount_amount',
                'reward_max_discount_amount',
            ],
            domain: function (self) {
                let current_date = moment().utc().format('YYYY-MM-DD 00:00:00');
                let domains = [
                    ['state', '=', 'active'],
                    ['end_date','>=', current_date],
                ];
                return domains
            },
            loaded: function (self, coupons) {
                let current_date = moment(moment().utc().format('YYYY-MM-DD HH:mm:ss'), 'YYYY-MM-DD HH:mm:ss');
                coupons = coupons.filter(p => {
                    let start_date = moment(p.start_date, 'YYYY-MM-DD HH:mm:ss');
                    let end_date = moment(p.end_date, 'YYYY-MM-DD HH:mm:ss');
                    if(current_date.isAfter(start_date) && current_date.isBefore(end_date)){
                        return true;
                    }
                    return false;
                });
                self.db.save_pos_coupon(coupons);
                self.db.set_last_write_date_by_model('pos.coupon', coupons);
            }
        },
        {
            model: 'pos.promotion',
            fields: [
                'name',
                'sequence',
                'start_date',
                'end_date',
                'type',
                'product_id',
                'payment_method_ids',
                'discount_lowest_price',
                'max_discount_amount_lowest_price',
                'product_ids',
                'minimum_items',
                'discount_first_order',
                'special_customer_ids',
                'promotion_birthday',
                'promotion_birthday_type',
                'pos_branch_ids',
                'monday',
                'tuesday',
                'wednesday',
                'thursday',
                'friday',
                'saturday',
                'sunday',
                'from_time',
                'to_time',
                'special_days',
                'special_times',
                'method',
                'amount_total',
                'new_based_on',
                'new_type',
                'discount_fixed_amount_lp',
                'discount_fixed_amount_fo',
                'is_card_payment',
                'card_payment_ids',
                'tebus_murah_brand_ids',
                'tebus_murah_brand_min_amount',
                'tebus_murah_total_order_min_qty',
                'tebus_murah_selected_brand_apply_and_or',
                'tebus_murah_total_order_apply_and_or',
                'tebus_murah_brand_min_qty',
                'discount_apply_and_or',
                'discount_apply_min_amount',
                'discount_apply_min_qty',
                'discount_fix_amount_all_product',
                'free_item_apply_and_or',
                'free_item_apply_min_amount',
                'free_item_apply_min_qty',
                'is_multi_level_promotion',
                'tebus_murah_apply_min_qty',
                'tebus_murah_apply_and_or',
                'tebus_murah_apply_min_amount',
                'multilevel_condition_ids',
                'multilevel_gift_ids',
            ],
            domain: function (self) {
                let current_date = moment().utc().format('YYYY-MM-DD 00:00:00');
                let domains = [
                    ['state', '=', 'active'],
                    ['end_date','>=', current_date],
                    ['id', 'in', self.config.promotion_ids]
                ];
                return domains
            },
            promotion: true,
            loaded: function (self, promotions) {
                if(!self.promotion_models){
                    // TODO: store existing ids of promotion and childs to improve search
                    self.promotion_models = {};
                }
                if(!self.promotions){
                    self.promotions = [];
                }
                if(!self.promotion_by_id){
                    self.promotion_by_id = {};
                }
                if(!self.promotion_ids){
                    self.promotion_ids = [];
                }

                let current_date = moment(moment().utc().format('YYYY-MM-DD HH:mm:ss'), 'YYYY-MM-DD HH:mm:ss');
                promotions = promotions.filter(p => {
                    let start_date = moment(p.start_date, 'YYYY-MM-DD HH:mm:ss');
                    let end_date = moment(p.end_date, 'YYYY-MM-DD HH:mm:ss');
                    if(current_date.isAfter(start_date) && current_date.isBefore(end_date)){
                        return true;
                    }
                    return false;
                });

                let pos_branch_id = self.config.pos_branch_id;
                let promotion_applied = [];
                for (let promotion of promotions) {
                    if (pos_branch_id) {  // TODO case 1: if pos setting have set branch
                        if (!promotion.pos_branch_ids.length) {
                            promotion_applied.push(promotion);
                            continue
                        }
                        if (promotion.pos_branch_ids.indexOf(pos_branch_id[0]) != -1) {
                            promotion_applied.push(promotion);
                            continue
                        }
                    } else { // TODO case 2: if pos setting not set branch
                        if (promotion.pos_branch_ids.length == 0) {
                            promotion_applied.push(promotion);
                        }
                    }
                }

                self.promotions = [...self.promotions, ...promotion_applied];
                for(let promotion of promotions){
                    self.promotion_by_id[promotion.id] = promotion;
                    self.promotion_ids.push(promotion.id);
                }

                if(self.sync_models){
                    self.promotions = self.sync_models_unique_list_object(self.promotions);
                    self.promotion_ids = self.sync_models_unique_list(self.promotion_ids);
                }
                self.promotion_models['pos.promotion'] = self.promotion_ids;
            }
        }, {
            model: 'pos.promotion.discount.order',
            fields: ['minimum_amount', 'discount', 'promotion_id','discount_fixed_amount','max_discount_amount', 'discount2'],
            condition: function (self) {
                return self.promotion_ids && self.promotion_ids.length > 0;
            },
            domain: function (self) {
                return [['promotion_id', 'in', self.promotion_ids]]
            },
            promotion: true,
            loaded: function (self, records) {
                if(!self.promotion_models){
                    // TODO: store existing ids of promotion and childs to improve search
                    self.promotion_models = {};
                }
                if (!self.promotion_discount_order_by_id){
                    self.promotion_discount_order_by_id = {};
                }
                if (!self.promotion_discount_order_by_promotion_id){
                    self.promotion_discount_order_by_promotion_id = {};
                }

                let record_ids = [];
                let promotion_ids = [];
                for (let rule of records){
                    record_ids.push(rule.id);
                    self.promotion_discount_order_by_id[rule.id] = rule;

                    let promotion_id = rule.promotion_id[0];
                    promotion_ids.push(promotion_id);
                    if (!self.promotion_discount_order_by_promotion_id[promotion_id]) {
                        self.promotion_discount_order_by_promotion_id[promotion_id] = [rule];
                    } else {
                        self.promotion_discount_order_by_promotion_id[promotion_id].push(rule);
                    }
                }

                if(self.sync_models && promotion_ids.length){
                    let object = self.promotion_discount_order_by_promotion_id;
                    let updated_object_ids = promotion_ids;
                    self.sync_models_unique_object(object, updated_object_ids);
                }

                self.promotion_models['pos.promotion.discount.order'] = record_ids;
            }
        }, {
            model: 'pos.promotion.discount.category',
            fields: ['category_ids', 'discount', 'promotion_id','discount_fixed_amount','min_qty','max_discount_amount', 'discount2'],
            condition: function (self) {
                return self.promotion_ids && self.promotion_ids.length > 0;
            },
            domain: function (self) {
                return [['promotion_id', 'in', self.promotion_ids]]
            },
            promotion: true,
            loaded: function (self, records) {
                if(!self.promotion_models){
                    // TODO: store existing ids of promotion and childs to improve search
                    self.promotion_models = {};
                }
                if (!self.pos_disc_categ_new){
                    self.pos_disc_categ_new = [];
                }
                if (!self.promotion_by_category_id){
                    self.promotion_by_category_id = {};
                }

                let record_ids = [];
                let promotion_ids = [];
                for (let rule of records){
                    record_ids.push(rule.id);
                    let promotion_id = rule.promotion_id[0];
                    if(promotion_id){
                        promotion_ids.push(promotion_id);
                        if (!self.pos_disc_categ_new[promotion_id]) {
                            self.pos_disc_categ_new[promotion_id] = [rule];
                        } else {
                            self.pos_disc_categ_new[promotion_id].push(rule);
                        }
                    }
                    for (let category_id of rule.category_ids){
                        self.promotion_by_category_id[category_id] = rule;
                    }
                }

                if(self.sync_models && promotion_ids.length){
                    let object = self.pos_disc_categ_new;
                    let updated_object_ids = promotion_ids;
                    self.sync_models_unique_object(object, updated_object_ids);
                }
                self.promotion_models['pos.promotion.discount.category'] = record_ids;
            }
        }, {
            model: 'pos.promotion.discount.quantity',
            fields: ['product_ids', 'quantity', 'discount', 'promotion_id','discount_fixed_amount','max_discount_amount', 'discount2'],
            condition: function (self) {
                return self.promotion_ids && self.promotion_ids.length > 0;
            },
            domain: function (self) {
                return [['promotion_id', 'in', self.promotion_ids]]
            },
            promotion: true,
            loaded: function (self, records) {
                if(!self.promotion_models){
                    // TODO: store existing ids of promotion and childs to improve search
                    self.promotion_models = {};
                }
                if (!self.promotion_quantity_by_product_id){
                    self.promotion_quantity_by_product_id = {};
                }

                let record_ids = [];
                let product_ids = [];
                for (let rule of records){
                    record_ids.push(rule.id);
                    for (let product_id of rule.product_ids){
                        product_ids.push(product_id);
                        if (!self.promotion_quantity_by_product_id[product_id]) {
                            self.promotion_quantity_by_product_id[product_id] = [rule];
                        } else {
                            self.promotion_quantity_by_product_id[product_id].push(rule);
                        }
                    }
                }

                if(self.sync_models && product_ids.length){
                    let object = self.promotion_quantity_by_product_id;
                    let updated_object_ids = product_ids;
                    self.sync_models_unique_object(object, updated_object_ids);
                }

                self.promotion_models['pos.promotion.discount.quantity'] = record_ids;
            }
        }, {
            model: 'pos.promotion.gift.condition',
            fields: ['product_id', 'minimum_quantity', 'promotion_id'],
            condition: function (self) {
                return self.promotion_ids && self.promotion_ids.length > 0;
            },
            domain: function (self) {
                return [['promotion_id', 'in', self.promotion_ids]]
            },
            promotion: true,
            loaded: function (self, records) {
                if (!self.promotion_gift_condition_by_promotion_id){
                    self.promotion_gift_condition_by_promotion_id = {};
                }

                let record_ids = [];
                let promotion_ids = [];
                for (let rule of records){
                    record_ids.push(rule.id);
                    let promotion_id = rule.promotion_id[0];
                    promotion_ids.push(promotion_id);
                    if (!self.promotion_gift_condition_by_promotion_id[promotion_id]) {
                        self.promotion_gift_condition_by_promotion_id[promotion_id] = [rule];
                    } else {
                        self.promotion_gift_condition_by_promotion_id[promotion_id].push(rule);
                    }
                }

                if(self.sync_models && promotion_ids.length){
                    let object = self.promotion_gift_condition_by_promotion_id;
                    let updated_object_ids = promotion_ids;
                    self.sync_models_unique_object(object, updated_object_ids);
                }

                self.promotion_models['pos.promotion.gift.condition'] = record_ids;
            }
        }, {
            model: 'pos.promotion.gift.free',
            fields: ['quantity_free', 'promotion_id', 'type_apply','product_ids'],
            condition: function (self) {
                return self.promotion_ids && self.promotion_ids.length > 0;
            },
            domain: function (self) {
                return [['promotion_id', 'in', self.promotion_ids]]
            },
            promotion: true,
            loaded: function (self, records) {
                if (!self.promotion_gift_free_by_promotion_id){
                    self.promotion_gift_free_by_promotion_id = {};
                }

                let record_ids = [];
                let promotion_ids = [];
                for (let rule of records){
                    record_ids.push(rule.id);
                    let promotion_id = rule.promotion_id[0];
                    promotion_ids.push(promotion_id);
                    if (!self.promotion_gift_free_by_promotion_id[promotion_id]) {
                        self.promotion_gift_free_by_promotion_id[promotion_id] = [rule];
                    } else {
                        self.promotion_gift_free_by_promotion_id[promotion_id].push(rule);
                    }
                }

                if(self.sync_models && promotion_ids.length){
                    let object = self.promotion_gift_free_by_promotion_id;
                    let updated_object_ids = promotion_ids;
                    self.sync_models_unique_object(object, updated_object_ids);
                }

                self.promotion_models['pos.promotion.gift.free'] = record_ids;
            }
        }, {
            model: 'pos.promotion.discount.condition',
            fields: ['product_id', 'minimum_quantity', 'promotion_id'],
            condition: function (self) {
                return self.promotion_ids && self.promotion_ids.length > 0;
            },
            domain: function (self) {
                return [['promotion_id', 'in', self.promotion_ids]]
            },
            promotion: true,
            loaded: function (self, records) {
                if (!self.promotion_discount_condition_by_promotion_id){
                    self.promotion_discount_condition_by_promotion_id = {};
                }

                let record_ids = [];
                let promotion_ids = [];
                for (let rule of records){
                    record_ids.push(rule.id);
                    let promotion_id = rule.promotion_id[0];
                    promotion_ids.push(promotion_id);
                    if (!self.promotion_discount_condition_by_promotion_id[promotion_id]) {
                        self.promotion_discount_condition_by_promotion_id[promotion_id] = [rule];
                    } else {
                        self.promotion_discount_condition_by_promotion_id[promotion_id].push(rule);
                    }
                }
                
                if(self.sync_models && promotion_ids.length){
                    let object = self.promotion_discount_condition_by_promotion_id;
                    let updated_object_ids = promotion_ids;
                    self.sync_models_unique_object(object, updated_object_ids);
                }

                self.promotion_models['pos.promotion.discount.condition'] = record_ids;
            }
        }, {
            model: 'pos.promotion.discount.apply',
            fields: ['product_id', 'discount', 'promotion_id', 'type','discount_fixed_amount'],
            condition: function (self) {
                return self.promotion_ids && self.promotion_ids.length > 0;
            },
            domain: function (self) {
                return [['promotion_id', 'in', self.promotion_ids]]
            },
            promotion: true,
            loaded: function (self, records) {
                if (!self.promotion_discount_apply_by_promotion_id){
                    self.promotion_discount_apply_by_promotion_id = {};
                }

                let record_ids = [];
                let promotion_ids = [];
                for (let rule of records){
                    record_ids.push(rule.id);
                    let promotion_id = rule.promotion_id[0];
                    promotion_ids.push(promotion_id);
                    if (!self.promotion_discount_apply_by_promotion_id[promotion_id]) {
                        self.promotion_discount_apply_by_promotion_id[promotion_id] = [rule];
                    } else {
                        self.promotion_discount_apply_by_promotion_id[promotion_id].push(rule);
                    }
                }

                if(self.sync_models && promotion_ids.length){
                    let object = self.promotion_discount_apply_by_promotion_id;
                    let updated_object_ids = promotion_ids;
                    self.sync_models_unique_object(object, updated_object_ids);
                }

                self.promotion_models['pos.promotion.discount.apply'] = record_ids;
            }
        }, {
            model: 'pos.promotion.price',
            fields: ['product_id', 'minimum_quantity', 'price_down', 'promotion_id'],
            condition: function (self) {
                return self.promotion_ids && self.promotion_ids.length > 0;
            },
            domain: function (self) {
                return [['promotion_id', 'in', self.promotion_ids]]
            },
            promotion: true,
            loaded: function (self, records) {
                if (!self.promotion_price_by_promotion_id){
                    self.promotion_price_by_promotion_id = {};
                }

                let record_ids = [];
                let promotion_ids = [];
                for (let rule of records){
                    record_ids.push(rule.id);
                    let promotion_id = rule.promotion_id[0];
                    promotion_ids.push(promotion_id);

                    if (!self.promotion_price_by_promotion_id[promotion_id]) {
                        self.promotion_price_by_promotion_id[promotion_id] = [rule];
                    } else {
                        self.promotion_price_by_promotion_id[promotion_id].push(rule);
                    }
                }

                if(self.sync_models && promotion_ids.length){
                    let object = self.promotion_price_by_promotion_id;
                    let updated_object_ids = promotion_ids;
                    self.sync_models_unique_object(object, updated_object_ids);
                }

                self.promotion_models['pos.promotion.price'] = record_ids;
            }
        }, {
            model: 'pos.promotion.special.category',
            fields: ['category_id', 'type','promotion_id', 'qty_free','type_apply','category_ids','product_ids'],
            condition: function (self) {
                return self.promotion_ids && self.promotion_ids.length > 0;
            },
            domain: function (self) {
                return [['promotion_id', 'in', self.promotion_ids]]
            },
            promotion: true,
            loaded: function (self, records) {
                if(!self.promotion_models){
                    // TODO: store existing ids of promotion and childs to improve search
                    self.promotion_models = {};
                }
                if (!self.promotion_special_category_by_promotion_id){
                    self.promotion_special_category_by_promotion_id = {};
                }

                let record_ids = [];
                let promotion_ids = [];
                for (let rule of records){
                    record_ids.push(rule.id);
                    let promotion_id = rule.promotion_id[0];
                    promotion_ids.push(promotion_id);

                    if (!self.promotion_special_category_by_promotion_id[promotion_id]) {
                        self.promotion_special_category_by_promotion_id[promotion_id] = [rule];
                    } else {
                        self.promotion_special_category_by_promotion_id[promotion_id].push(rule);
                    }
                }

                if(self.sync_models && promotion_ids.length){
                    let object = self.promotion_special_category_by_promotion_id;
                    let updated_object_ids = promotion_ids;
                    self.sync_models_unique_object(object, updated_object_ids);
                }

                self.promotion_models['pos.promotion.special.category'] = record_ids;
            }
        }, 


        {
            model: 'pos.promotion.selected.brand',
            fields: ['promotion_id', 'type_apply','promotion_id', 'qty_qift','brand_gift_ids','product_ids','min_amount_qty','gift_based_on','write_date'],
            condition: function (self) {
                return self.promotion_ids && self.promotion_ids.length > 0;
            },
            domain: function (self) {
                return [['promotion_id', 'in', self.promotion_ids]]
            },
            promotion: true,
            loaded: function (self, records) {
                if(!self.promotion_selected_brands){
                    self.promotion_selected_brands = {};
                }

                let record_ids = [];
                let promotion_ids = [];
                for (let rule of records){
                    record_ids.push(rule.id);
                    let promotion_id = rule.promotion_id[0];
                    promotion_ids.push(promotion_id);

                    if (!self.promotion_selected_brands[promotion_id]) {
                        self.promotion_selected_brands[promotion_id] = [rule];
                    } else {
                        self.promotion_selected_brands[promotion_id].push(rule);
                    }
                }

                if(self.sync_models && promotion_ids.length){
                    let object = self.promotion_selected_brands;
                    let updated_object_ids = promotion_ids;
                    self.sync_models_unique_object(object, updated_object_ids);
                }

                self.promotion_models['pos.promotion.selected.brand'] = record_ids;
            }
        }, 

        {
            model: 'pos.promotion.tebus.murah.selected.brand',
            fields: ['promotion_id', 'type_apply', 'qty_qift','product_ids','write_date','active'],
            condition: function (self) {
                return self.promotion_ids && self.promotion_ids.length > 0;
            },
            domain: function (self) {
                return [['promotion_id', 'in', self.promotion_ids]]
            },
            promotion: true,
            loaded: function (self, records) {
                if(!self.promotion_tebus_murah_selected_brands){
                    self.promotion_tebus_murah_selected_brands = {};
                }

                let record_ids = [];
                let promotion_ids = [];
                for (let rule of records){
                    var display_name = false
                    if (rule.type_apply == 'same_brand') {
                        display_name = 'Same Brand'
                    }
                    if (rule.type_apply == 'selected_product') {
                        display_name = 'Selected Product'
                    }
                    rule.display_name = display_name
                    record_ids.push(rule.id);
                    let promotion_id = rule.promotion_id[0];
                    promotion_ids.push(promotion_id);

                    if (!self.promotion_tebus_murah_selected_brands[promotion_id]) {
                        self.promotion_tebus_murah_selected_brands[promotion_id] = [rule];
                    } else {
                        self.promotion_tebus_murah_selected_brands[promotion_id].push(rule);
                    }
                }

                if(self.sync_models && promotion_ids.length){
                    let object = self.promotion_tebus_murah_selected_brands;
                    let updated_object_ids = promotion_ids;
                    self.sync_models_unique_object(object, updated_object_ids);
                }

                self.promotion_models['pos.promotion.tebus.murah.selected.brand'] = record_ids;
            }
        }, 


        {
            model: 'pos.promotion.specific.product',
            fields: ['type_apply', 'product_id','promotion_id', 'qty_free','product_ids'],
            condition: function (self) {
                return self.promotion_ids && self.promotion_ids.length > 0;
            },
            domain: function (self) {
                return [['promotion_id', 'in', self.promotion_ids]]
            },
            promotion: true,
            loaded: function (self, records) {
                if (!self.promotion_specific_product_by_promotion_id){
                    self.promotion_specific_product_by_promotion_id = {};
                }

                let record_ids = [];
                let promotion_ids = [];
                for (let rule of records){
                    record_ids.push(rule.id);
                    let promotion_id = rule.promotion_id[0];
                    promotion_ids.push(promotion_id);

                    if (!self.promotion_specific_product_by_promotion_id[promotion_id]) {
                        self.promotion_specific_product_by_promotion_id[promotion_id] = [rule];
                    } else {
                        self.promotion_specific_product_by_promotion_id[promotion_id].push(rule);
                    }
                }

                if(self.sync_models && promotion_ids.length){
                    let object = self.promotion_specific_product_by_promotion_id;
                    let updated_object_ids = promotion_ids;
                    self.sync_models_unique_object(object, updated_object_ids);
                }

                self.promotion_models['pos.promotion.specific.product'] = record_ids;
            }
        }, {
            model: 'pos.promotion.multi.buy',
            fields: ['promotion_id', 'product_ids', 'list_price', 'qty_apply'],
            condition: function (self) {
                return self.promotion_ids && self.promotion_ids.length > 0;
            },
            domain: function (self) {
                return [['promotion_id', 'in', self.promotion_ids]]
            },
            promotion: true,
            loaded: function (self, records) {
                if (!self.multi_buy){
                    self.multi_buy = [];
                }
                if (!self.multi_buy_by_promotion_id){
                    self.multi_buy_by_promotion_id = {};
                }

                self.multi_buy = [...self.multi_buy, ...records];

                let record_ids = [];
                let promotion_ids = [];
                for (let rule of records){
                    record_ids.push(rule.id);
                    let promotion_id = rule.promotion_id[0];
                    promotion_ids.push(promotion_id);

                    if (!self.multi_buy_by_promotion_id[promotion_id]) {
                        self.multi_buy_by_promotion_id[promotion_id] = [rule];
                    } else {
                        self.multi_buy_by_promotion_id[promotion_id].push(rule);
                    }
                }

                if(self.sync_models && promotion_ids.length){
                    let object = self.multi_buy_by_promotion_id;
                    let updated_object_ids = promotion_ids;
                    self.sync_models_unique_object(object, updated_object_ids);
                    self.multi_buy = self.sync_models_unique_list_object(self.multi_buy);
                }

                self.promotion_models['pos.promotion.multi.buy'] = record_ids;
            }
        }, 
        {
            model: 'pos.promotion.tebus.murah',
            fields: ['promotion_id', 'product_id', 'price','quantity','product_ids'],
            condition: function (self) {
                return self.promotion_ids && self.promotion_ids.length > 0;
            },
            domain: function (self) {
                return [['promotion_id', 'in', self.promotion_ids]]
            },
            promotion: true,
            loaded: function (self, records) {
                if(!self.promotion_tebus_murah_product_by_promotion_id){
                    self.promotion_tebus_murah_product_by_promotion_id = {};
                }

                let record_ids = [];
                let promotion_ids = [];
                for (let rule of records){
                    record_ids.push(rule.id);
                    let promotion_id = rule.promotion_id[0];
                    promotion_ids.push(promotion_id);
                    let existing_rules = self.promotion_tebus_murah_product_by_promotion_id[promotion_id];
                    if (!existing_rules) {
                        self.promotion_tebus_murah_product_by_promotion_id[promotion_id] = [rule];
                    } else {
                        self.promotion_tebus_murah_product_by_promotion_id[promotion_id].push(rule);
                    }
                }
                if(self.sync_models){
                    let object = self.promotion_tebus_murah_product_by_promotion_id;
                    let updated_object_ids = promotion_ids;
                    self.sync_models_unique_object(object, updated_object_ids);
                }

                self.promotion_models['pos.promotion.tebus.murah'] = record_ids;
            }
        }, 

        {
            model: 'pos.promotion.multilevel.condition',
            fields: ['promotion_id', 'product_id', 'minimum_quantity'],
            condition: function (self) {
                return self.promotion_ids && self.promotion_ids.length > 0;
            },
            domain: function (self) {
                return [['promotion_id', 'in', self.promotion_ids]]
            },
            promotion: true,
            loaded: function (self, records) {
                if(!self.promotion_multilevel_condition_by_promotion_id){
                    self.promotion_multilevel_condition_by_promotion_id = {};
                }

                let record_ids = [];
                let promotion_ids = [];
                for (let rule of records){
                    record_ids.push(rule.id);
                    let promotion_id = rule.promotion_id[0];
                    promotion_ids.push(promotion_id);
                    let existing_rules = self.promotion_multilevel_condition_by_promotion_id[promotion_id];
                    if (!existing_rules) {
                        self.promotion_multilevel_condition_by_promotion_id[promotion_id] = [rule];
                    } else {
                        self.promotion_multilevel_condition_by_promotion_id[promotion_id].push(rule);
                    }
                }
                if(self.sync_models){
                    let object = self.promotion_multilevel_condition_by_promotion_id;
                    let updated_object_ids = promotion_ids;
                    self.sync_models_unique_object(object, updated_object_ids);
                }

                self.promotion_models['pos.promotion.multilevel.condition'] = record_ids;
            }
        }, 
        {
            model: 'pos.promotion.multilevel.gift',
            fields: ['promotion_id', 'product_id', 'quantity_free'],
            condition: function (self) {
                return self.promotion_ids && self.promotion_ids.length > 0;
            },
            domain: function (self) {
                return [['promotion_id', 'in', self.promotion_ids]]
            },
            promotion: true,
            loaded: function (self, records) {
                if(!self.promotion_multilevel_gift_by_promotion_id){
                    self.promotion_multilevel_gift_by_promotion_id = {};
                }

                let record_ids = [];
                let promotion_ids = [];
                for (let rule of records){
                    record_ids.push(rule.id);
                    let promotion_id = rule.promotion_id[0];
                    promotion_ids.push(promotion_id);
                    let existing_rules = self.promotion_multilevel_gift_by_promotion_id[promotion_id];
                    if (!existing_rules) {
                        self.promotion_multilevel_gift_by_promotion_id[promotion_id] = [rule];
                    } else {
                        self.promotion_multilevel_gift_by_promotion_id[promotion_id].push(rule);
                    }
                }
                if(self.sync_models){
                    let object = self.promotion_multilevel_gift_by_promotion_id;
                    let updated_object_ids = promotion_ids;
                    self.sync_models_unique_object(object, updated_object_ids);
                }

                self.promotion_models['pos.promotion.multilevel.gift'] = record_ids;
            }
        }, 
        {
            label: 'Stock Picking Type',
            model: 'stock.picking.type',
            fields: ['name', 'code', 'default_location_dest_id', 'default_location_src_id', 'display_name', 'return_picking_type_id'],
            domain: function (self) {
                return ['|', ['id', '=', self.config.picking_type_id[0]], ['id', 'in', self.config.multi_stock_operation_type_ids]];
            },
            loaded: function (self, stock_picking_types) {
                self.default_location_src_of_picking_type_ids = [];
                self.stock_picking_type_by_id = {};
                for (let i = 0; i < stock_picking_types.length; i++) {
                    let picking_type = stock_picking_types[i];
                    if (picking_type.warehouse_id) {
                        picking_type['name'] = picking_type.warehouse_id[1] + ' / ' + picking_type['name']
                    }
                    self.stock_picking_type_by_id[picking_type['id']] = picking_type;
                    if (!self.default_location_src_of_picking_type_ids.includes() && picking_type.default_location_src_id) {
                        self.default_location_src_of_picking_type_ids.push(picking_type.default_location_src_id[0])
                    }
                }
                self.stock_picking_types = stock_picking_types;
            }
        },
        {
            model: 'stock.location',
            fields: ['name', 'location_id', 'company_id', 'usage', 'barcode', 'display_name'],
            domain: function (self) {
                return ['|', '|', ['id', 'in', self.config.stock_location_ids], ['id', '=', self.config.stock_location_id[0]], ['id', 'in', self.default_location_src_of_picking_type_ids]];
            },
            loaded: function (self, stock_locations) {
                self.stock_locations = stock_locations;
                self.stock_location_by_id = {};
                self.stock_location_ids = [];
                for (let i = 0; i < stock_locations.length; i++) {
                    let stock_location = stock_locations[i];
                    self.stock_location_by_id[stock_location['id']] = stock_location;
                    if (stock_location.usage == 'internal') {
                        self.stock_location_ids.push(stock_location['id'])
                    }
                }
            },
        },
    ], {
        after: 'pos.config'
    });

    let extend_models = [
        {
            label: 'Multi Currency',
            model: 'res.currency',
            fields: [],
            domain: function (self) {
                return [['active', '=', true]]
            },
            loaded: function (self, currencies) {
                self.currency_by_id = {}
                let i = 0
                while (i < currencies.length) {
                    let currency = currencies[i]
                    currency['decimals'] = Math.ceil(Math.log(1.0 / currency.rounding) / Math.log(10))
                    self.currency_by_id[currencies[i].id] = currencies[i]
                    i++
                }
                self.currencies = currencies
                self.multi_currencies = []
                if (self.config.multi_currency) {
                    currencies.forEach(c => {
                        if (self.config.multi_currency_ids.includes(c.id)) {
                            self.multi_currencies.push(c)
                        }
                    })
                }
                self.base_currency = currencies.find(c => c.id == self.config.currency_id[0])
            }
        },
        {
            model: 'res.partner.group',
            fields: ['name', 'image', 'pricelist_applied', 'pricelist_id', 'height', 'width'],
            loaded: function (self, membership_groups) {
                self.membership_groups = membership_groups;
                self.membership_group_by_id = {};
                for (let i = 0; i < membership_groups.length; i++) {
                    let membership_group = membership_groups[i];
                    self.membership_group_by_id[membership_group.id] = membership_group;
                }
            },
            retail: true,
        },
        {
            label: 'Units of Measure',
            model: 'uom.uom',
            fields: [],
            domain: [],
            loaded: function (self, uoms) {
                self.uom_by_id = {};
                for (let i = 0; i < uoms.length; i++) {
                    let uom = uoms[i];
                    self.uom_by_id[uom.id] = uom;
                }
            }
        },
        {
            label: 'Sellers',
            model: 'res.users',
            fields: ['display_name', 'name', 'pos_security_pin', 'barcode', 'pos_config_id', 'partner_id', 'image_1920', 'cashier_code'],
            context: {sudo: true},
            domain: function (self) {
                let user_ids = [...self.config.user_ids, ...self.config.assigned_user_ids]
                return [['id', 'in', user_ids]]
            },
            loaded: function (self, users) {
                // TODO: have 2 case
                // TODO 1) If have set default_seller_id, default seller is default_seller_id
                // TODO 2) If have NOT set default_seller_id, default seller is pos_session.user_id
                self.users = users;
                self.user_by_id = {};
                self.user_by_pos_security_pin = {};
                self.user_by_barcode = {};
                self.default_seller = null;
                self.sellers = [];
                for (let i = 0; i < users.length; i++) {
                    let user = users[i];
                    if (user['pos_security_pin']) {
                        self.user_by_pos_security_pin[user['pos_security_pin']] = user;
                    }
                    if (user['barcode']) {
                        self.user_by_barcode[user['barcode']] = user;
                    }
                    self.user_by_id[user['id']] = user;
                    if (self.config.default_seller_id && self.config.default_seller_id[0] == user['id']) {
                        self.default_seller = user;
                    }
                    if (self.config.seller_ids.indexOf(user['id']) != -1) {
                        self.sellers.push(user)
                    }
                }
                if (!self.default_seller) { // TODO: if have not POS Config / default_seller_id: we set default_seller is user of pos session
                    let pos_session_user_id = self.pos_session.user_id[0];
                    if (self.user_by_id[pos_session_user_id]) {
                        self.default_seller = self.user_by_id[pos_session_user_id]
                    }
                }
            }
        },
        {
            model: 'pos.tag',
            fields: ['name', 'is_return_reason', 'color'],
            domain: [],
            loaded: function (self, tags) {
                self.tags = tags;
                self.tag_by_id = {};
                self.cancel_reasons = []
                self.return_reasons = [];
                let i = 0;
                while (i < tags.length) {
                    let tag = tags[i];
                    self.tag_by_id[tag.id] = tag;
                    if (tag.is_return_reason) {
                        self.return_reasons.push(tag)
                    }
                    if(self.config.reason_cancel_reason_ids){
                        if (self.config.reason_cancel_reason_ids.indexOf(tag.id) != -1) {
                            self.cancel_reasons.push(tag)
                        }
                    }
                    i++;
                }

            }
        }, {
            model: 'pos.note',
            fields: ['name'],
            loaded: function (self, notes) {
                self.notes = notes;
                self.note_by_id = {};
                let i = 0;
                while (i < notes.length) {
                    self.note_by_id[notes[i].id] = notes[i];
                    i++;
                }
            }
        }, {
            model: 'pos.combo.item',
            fields: ['product_id', 'product_combo_id', 'default', 'quantity', 'uom_id', 'tracking', 'required', 'price_extra'],
            domain: [],
            loaded: function (self, combo_items) {
                self.combo_items = combo_items;
                self.combo_item_by_id = {};
                for (let i = 0; i < combo_items.length; i++) {
                    let item = combo_items[i];
                    self.combo_item_by_id[item.id] = item;
                }
            }
        },
        {
            label: 'Global Discount',
            model: 'pos.global.discount',
            fields: ['name', 'amount', 'product_id', 'reason', 'type', 'branch_ids'],
            domain: function (self) {
                return [['id', 'in', self.config.discount_ids]];
            },
            condition: function (self) {
                return self.config.discount && self.config.discount_ids.length > 0;
            },
            loaded: function (self, discounts) {
                discounts = _.filter(discounts, function (discount) {
                    return discount.branch_ids.length == 0 || (self.config.pos_branch_id && discount.branch_ids && discount.branch_ids.indexOf(self.config.pos_branch_id[0]) != -1)
                });
                self.discounts = discounts;
                self.discount_by_id = {};
                let i = 0;
                while (i < discounts.length) {
                    self.discount_by_id[discounts[i].id] = discounts[i];
                    i++;
                }
            }
        },
        // {
        //     label: 'Product Variants',
        //     model: 'product.variant',
        //     fields: ['product_tmpl_id', 'attribute_id', 'value_id', 'price_extra', 'product_id', 'quantity', 'uom_id'],
        //     domain: function (self) {
        //         return [['active', '=', true]];
        //     },
        //     loaded: function (self, variants) {
        //         self.variants = variants;
        //         self.variant_by_product_tmpl_id = {};
        //         self.variant_by_id = {};
        //         for (let i = 0; i < variants.length; i++) {
        //             let variant = variants[i];
        //             variant.display_name = variant.attribute_id[1] + ' / ' + variant.value_id[1];
        //             self.variant_by_id[variant.id] = variant;
        //             if (!self.variant_by_product_tmpl_id[variant['product_tmpl_id'][0]]) {
        //                 self.variant_by_product_tmpl_id[variant['product_tmpl_id'][0]] = [variant]
        //             } else {
        //                 self.variant_by_product_tmpl_id[variant['product_tmpl_id'][0]].push(variant)
        //             }
        //         }
        //     }
        // },
        {
            label: 'Product Attributes',
            model: 'product.attribute',
            fields: ['name', 'multi_choice', 'product_tmpl_ids'],
            domain: function (self) {
                return [];
            },
            loaded: function (self, attributes) {
                self.product_attributes = attributes;
                self.product_attribute_by_id = {};
                for (let i = 0; i < attributes.length; i++) {
                    let attribute = attributes[i];
                    self.product_attribute_by_id[attribute.id] = attribute;
                }
            }
        },
        {
            label: 'Product Attributes',
            model: 'product.attribute.value',
            fields: ['name', 'attribute_id', 'sequence'],
            domain: function (self) {
                return [];
            },
            loaded: function (self, attribute_values) {
                self.product_attribute_values = attribute_values;
                self.product_attribute_value_by_id = {};
                self.product_attribute_value_by_attribute_id = {};
                for (let i = 0; i < attribute_values.length; i++) {
                    let attribute_value = attribute_values[i];
                    self.product_attribute_value_by_id[attribute_value.id] = attribute_value;
                    if (!self.product_attribute_value_by_attribute_id[attribute_value['attribute_id'][0]]) {
                        self.product_attribute_value_by_attribute_id[attribute_value['attribute_id'][0]] = [attribute_value]
                    } else {
                        self.product_attribute_value_by_attribute_id[attribute_value['attribute_id'][0]].push(attribute_value)
                    }
                }
            }
        },
        {
            label: 'Product Attributes',
            model: 'product.template.attribute.value',
            fields: ['name', 'product_attribute_value_id', 'attribute_id', 'product_tmpl_id'],
            domain: function (self) {
                return [['product_tmpl_id', '!=', null]];
            },
            loaded: function (self, template_attribute_values) {
                self.template_attribute_values = template_attribute_values;
                self.values_by_attribute_id = {}
                self.values_by_value_id = {}
                for (let i = 0; i < template_attribute_values.length; i++) {
                    let template_attribute_value = template_attribute_values[i];
                    if (!self.values_by_attribute_id[template_attribute_value['attribute_id'][0]]) {
                        self.values_by_attribute_id[template_attribute_value['attribute_id'][0]] = [template_attribute_value['id']]
                    } else {
                        self.values_by_attribute_id[template_attribute_value['attribute_id'][0]].push(template_attribute_value['id'])
                    }
                    if (!self.values_by_value_id[template_attribute_value['product_attribute_value_id'][0]]) {
                        self.values_by_value_id[template_attribute_value['product_attribute_value_id'][0]] = [template_attribute_value['id']]
                    } else {
                        self.values_by_value_id[template_attribute_value['product_attribute_value_id'][0]].push(template_attribute_value['id'])
                    }
                }
            }
        },
        {
            label: 'Product Template Attribute Value',
            model: 'product.template.attribute.value',
            fields: [],
            loaded: function (self, attribute_values) {
                self.attribute_value_by_id = {};
                for (let i = 0; i < attribute_values.length; i++) {
                    let attribute_value = attribute_values[i];
                    self.attribute_value_by_id[attribute_value.id] = attribute_value;
                }
            }
        },        
        {
            label: 'Price by Unit',
            model: 'product.uom.price',
            fields: [],
            domain: [],
            loaded: function (self, uoms_prices) {
                self.uom_price_by_uom_id = {};
                self.uoms_prices_by_product_tmpl_id = {};
                self.uoms_prices = uoms_prices;
                for (let i = 0; i < uoms_prices.length; i++) {
                    let item = uoms_prices[i];
                    if (item.product_tmpl_id) {
                        self.uom_price_by_uom_id[item.uom_id[0]] = item;
                        if (!self.uoms_prices_by_product_tmpl_id[item.product_tmpl_id[0]]) {
                            self.uoms_prices_by_product_tmpl_id[item.product_tmpl_id[0]] = [item]
                        } else {
                            self.uoms_prices_by_product_tmpl_id[item.product_tmpl_id[0]].push(item)
                        }
                    }
                }
            }
        },
        {
            label: 'Attribute Values Modifiers',
            model: 'pos.product.attribute',
            fields: ['attribute_id', 'display_name', 'product_id', 'sequence', 'value_ids'],
            loaded: function (self, attributeValues) {
                self.posProductAttributeValues = []
                self.attributeValueByProductId = {};
                attributeValues.forEach(v => {
                    if (!self.attributeValueByProductId[v.product_id[0]]) {
                        self.attributeValueByProductId[v.product_id[0]] = [v]
                    } else {
                        self.attributeValueByProductId[v.product_id[0]].push(v)
                    }
                    self.posProductAttributeValues = self.posProductAttributeValues.concat(v.value_ids)
                })
            }
        },

        {
            model: 'account.payment.term',
            fields: ['name'],
            domain: [],
            context: {'pos': true},
            loaded: function (self, payments_term) {
                self.payments_term = payments_term;
            }
        }, {
            model: 'product.cross',
            fields: ['product_id', 'list_price', 'quantity', 'discount_type', 'discount', 'product_tmpl_id'],
            domain: [],
            loaded: function (self, cross_items) {
                self.cross_items = cross_items;
                self.cross_item_by_id = {};
                self.cross_items_by_product_tmpl_id = {}
                for (let i = 0; i < cross_items.length; i++) {
                    let item = cross_items[i];
                    item.display_name = item.product_id[1];
                    item.display_name += _t(', Discount type: ') + item.discount_type
                    item.display_name += _t(', Discount value: ') + item.discount
                    self.cross_item_by_id[item['id']] = item;
                    if (!self.cross_items_by_product_tmpl_id[item.product_tmpl_id[0]]) {
                        self.cross_items_by_product_tmpl_id[item.product_tmpl_id[0]] = [item]
                    } else {
                        self.cross_items_by_product_tmpl_id[item.product_tmpl_id[0]].push(item)
                    }
                }
            }
        }, {
            label: 'POS Configuration',
            model: 'pos.config',
            fields: [],
            domain: function (self) {
                return []
            },
            loaded: function (self, configs) {
                self.config_by_id = {};
                self.configs = configs;
                for (let i = 0; i < configs.length; i++) {
                    let config = configs[i];
                    self.config_by_id[config['id']] = config;
                    if (self.config['id'] == config['id'] && config.logo) {
                        self.config.logo_shop = 'data:image/png;base64,' + config.logo
                    }
                }
                if (self.config_id) {
                    let config = _.find(configs, function (config) {
                        return config['id'] == self.config_id
                    });
                    if (config) {
                        let user = self.user_by_id[config.user_id[0]]
                        if (user) {
                            self.set_cashier(user);
                        }
                    }
                }
                let restaurant_order_config = configs.find(f => f.restaurant_order)
                self.restaurant_order_config = restaurant_order_config
            }
        },
        {
            label: 'Journals',
            model: 'account.journal', // TODO: loading journal and linked pos_method_type to payment_methods variable of posmodel
            fields: ['name', 'code', 'pos_method_type', 'profit_account_id', 'loss_account_id', 'currency_id', 'decimal_rounding', 'inbound_payment_method_ids', 'outbound_payment_method_ids'],
            domain: function (self) {
                return ['|', '|', '|', ['id', 'in', self.config.payment_journal_ids], ['type', '=', 'bank'], ['type', '=', 'cash'], ['company_id', '=', self.company.id]]
            },
            loaded: function (self, account_journals) {
                self.payment_journals = [];
                self.account_journals = account_journals;
                self.normal_payment_methods = [] // todo: this methods will display on payment screen
                self.journal_by_id = {};
                for (let i = 0; i < account_journals.length; i++) {
                    let account_journal = account_journals[i];
                    self.journal_by_id[account_journal.id] = account_journal;
                    if (!account_journal.currency_id) {
                        account_journal.currency_id = self.config.currency_id;
                    }
                    if (self.config.payment_journal_ids.indexOf(account_journal.id) != -1) {
                        self.payment_journals.push(account_journal)
                    }
                }
                if (self.payment_methods) {
                    for (let i = 0; i < self.payment_methods.length; i++) {
                        let payment_method = self.payment_methods[i];
                        if (payment_method.cash_journal_id) {
                            payment_method.journal = self.journal_by_id[payment_method.cash_journal_id[0]];
                            if(payment_method.journal){
                                payment_method.pos_method_type = payment_method.journal['pos_method_type']
                            }else{
                                console.warn('Payment Method "cash_journal_id" is Empty', payment_method.journal)
                            }
                            if (payment_method.pos_method_type == 'default') {
                                self.normal_payment_methods.push(payment_method)
                            }
                        } else {
                            self.normal_payment_methods.push(payment_method)
                        }
                    }
                }
            }
        },
        {
            label: 'Product Price by Quantity',
            model: 'product.price.quantity', // product price quantity
            fields: ['quantity', 'price_unit', 'product_tmpl_id'],
            loaded: function (self, records) {
                self.price_each_qty_by_product_tmpl_id = {};
                for (let i = 0; i < records.length; i++) {
                    let record = records[i];
                    let product_tmpl_id = record['product_tmpl_id'][0];
                    if (!self.price_each_qty_by_product_tmpl_id[product_tmpl_id]) {
                        self.price_each_qty_by_product_tmpl_id[product_tmpl_id] = [record];
                    } else {
                        self.price_each_qty_by_product_tmpl_id[product_tmpl_id].push(record);
                    }
                }
            }
        },
        {
            label: 'Stock Picking',
            model: 'stock.picking',
            fields: ['id', 'pos_order_id'],
            condition: function (self) {
                return self.config.pos_orders_management;
            },
            domain: [['is_picking_combo', '=', true], ['pos_order_id', '!=', null]],
            loaded: function (self, combo_pickings) {
                self.combo_pickings = combo_pickings;
                self.combo_picking_by_order_id = {};
                self.combo_picking_ids = [];
                for (let i = 0; i < combo_pickings.length; i++) {
                    let combo_picking = combo_pickings[i];
                    self.combo_picking_by_order_id[combo_picking.pos_order_id[0]] = combo_picking.id;
                    self.combo_picking_ids.push(combo_picking.id)
                }
            }
        },
        {
            label: 'Stock Move',
            model: 'stock.move',
            fields: ['combo_item_id', 'picking_id', 'product_id', 'product_uom_qty'],
            condition: function (self) {
                return self.config.pos_orders_management;
            },
            domain: function (self) {
                return [['picking_id', 'in', self.combo_picking_ids]]
            },
            loaded: function (self, moves) {
                self.stock_moves_by_picking_id = {};
                for (let i = 0; i < moves.length; i++) {
                    let move = moves[i];
                    if (!self.stock_moves_by_picking_id[move.picking_id[0]]) {
                        self.stock_moves_by_picking_id[move.picking_id[0]] = [move]
                    } else {
                        self.stock_moves_by_picking_id[move.picking_id[0]].push(move)
                    }
                }
            }
        },
        {
            label: 'Partner Titles',
            model: 'res.partner.title',
            condition: function (self) {
                return !self.config.hide_title
            },
            fields: ['name'],
            loaded: function (self, partner_titles) {
                self.partner_titles = partner_titles;
                self.partner_title_by_id = {};
                for (let i = 0; i < partner_titles.length; i++) {
                    let title = partner_titles[i];
                    self.partner_title_by_id[title.id] = title;
                }
            }
        },
        {
            label: 'Combo Items Limited',
            model: 'pos.combo.limit',
            fields: ['product_tmpl_id', 'pos_categ_id', 'quantity_limited', 'default_product_ids'],
            loaded: function (self, combo_limiteds) {
                self.combo_limiteds = combo_limiteds;
                self.combo_limiteds_by_product_tmpl_id = {};
                self.combo_category_limited_by_product_tmpl_id = {};
                for (let i = 0; i < combo_limiteds.length; i++) {
                    let combo_limited = combo_limiteds[i];
                    if (self.combo_limiteds_by_product_tmpl_id[combo_limited.product_tmpl_id[0]]) {
                        self.combo_limiteds_by_product_tmpl_id[combo_limited.product_tmpl_id[0]].push(combo_limited);
                    } else {
                        self.combo_limiteds_by_product_tmpl_id[combo_limited.product_tmpl_id[0]] = [combo_limited];
                    }
                    if (!self.combo_category_limited_by_product_tmpl_id[combo_limited.product_tmpl_id[0]]) {
                        self.combo_category_limited_by_product_tmpl_id[combo_limited.product_tmpl_id[0]] = {};
                        self.combo_category_limited_by_product_tmpl_id[combo_limited.product_tmpl_id[0]][combo_limited.pos_categ_id[0]] = combo_limited.quantity_limited;
                    } else {
                        self.combo_category_limited_by_product_tmpl_id[combo_limited.product_tmpl_id[0]][combo_limited.pos_categ_id[0]] = combo_limited.quantity_limited;
                    }
                }
            }
        },
        // {
        //     label: 'Shop Logo', // shop logo
        //     condition: function (self) {
        //         return true
        //     },
        //     loaded: function (self) {
        //         self.company_logo = new Image();
        //         return new Promise(function (resolve, reject) {
        //             self.company_logo.onload = function () {
        //                 let img = self.company_logo;
        //                 let ratio = 1;
        //                 let targetwidth = 300;
        //                 let maxheight = 150;
        //                 if (img.width !== targetwidth) {
        //                     ratio = targetwidth / img.width;
        //                 }
        //                 if (img.height * ratio > maxheight) {
        //                     ratio = maxheight / img.height;
        //                 }
        //                 let width = Math.floor(img.width * ratio);
        //                 let height = Math.floor(img.height * ratio);
        //                 let c = document.createElement('canvas');
        //                 c.width = width;
        //                 c.height = height;
        //                 let ctx = c.getContext('2d');
        //                 ctx.drawImage(self.company_logo, 0, 0, width, height);
        //
        //                 self.company_logo_base64 = c.toDataURL();
        //                 resolve()
        //
        //             };
        //             self.company_logo.onerror = function (error) {
        //                 return reject()
        //             };
        //             self.company_logo.crossOrigin = "anonymous";
        //             if (!self.is_mobile) {
        //                 self.company_logo.src = '/web/image' + '?model=pos.config&field=logo&id=' + self.config.id;
        //             } else {
        //                 self.company_logo.src = '/web/binary/company_logo' + '?dbname=' + self.session.db + '&write_date=' + self.company.write_date;
        //             }
        //         });
        //     },
        // },
    ];

    let _super_PosModel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        get_units_barcode_by_id: function (product_id) {
            let units = this.barcodes_by_product_id[product_id]
            if (!units) {
                return []
            }
            return units
        },
        get_taxes: function (product) {
            if (!product.taxes_id) {
                return []
            } else {
                taxes = []
                for (let i = 0; i < product.taxes_id.length; i++) {
                    let tax = this.taxes_by_id[product.taxes_id[i]];
                    if (tax) {
                        taxes.push(tax)
                    }
                }
                return taxes
            }
        },
        get_count_variant: function (product_tmpl_id) {
            if (this.db.total_variant_by_product_tmpl_id[product_tmpl_id]) {
                return this.db.total_variant_by_product_tmpl_id[product_tmpl_id]
            } else {
                return 0
            }
        },
        restore_orders: function () {
            let self = this;
            return rpc.query({
                model: 'pos.backup.orders',
                method: 'getUnpaidOrders',
                args: [[], {
                    config_id: this.config.id,
                }]
            }, {
                shadow: true,
                timeout: 60000
            }).then(function (unpaid_orders) {
                if (unpaid_orders.length) {
                    let restored = 0;
                    let json_orders = JSON.parse(unpaid_orders);
                    let rollback_orders = [];
                    for (let index in json_orders) {
                        let unpaid_order = json_orders[index];
                        let order_exist = _.find(self.db.get_unpaid_orders(), function (order) {
                            return order.uid == unpaid_order.uid
                        });
                        if (!order_exist) {
                            restored += 1;
                            console.log('[restore_orders] ' + restored + ' orders');
                            new models.Order({}, {
                                pos: self,
                                json: unpaid_order,
                            });
                        } else {
                            console.log(unpaid_order.uid + ' exist in your browse cache');
                        }
                    }
                    return rollback_orders;
                }
            });
        },
        automaticBackupUnpaidOrders: function () {
            let self = this;
            const unpaidOrders = this.db.get_unpaid_orders()
            console.log('[automaticBackupUnpaidOrders] total unpaid orders: ' + unpaidOrders.length)
            return rpc.query({
                model: 'pos.backup.orders',
                method: 'automaticBackupUnpaidOrders',
                args: [[], {
                    config_id: this.config.id,
                    unpaid_orders: unpaidOrders,
                    total_orders: unpaidOrders.length
                }]
            }, {
                shadow: true,
                timeout: 60000
            }).then(function (backup_id) {
                setTimeout(_.bind(self.automaticBackupUnpaidOrders, self), 5000);
            }, function (err) {
                setTimeout(_.bind(self.automaticBackupUnpaidOrders, self), 120000);
            });
        },


        polling_job_auto_paid_orders_draft: function () {
            let self = this;
            let params = {
                message: 'Automatic Paid Orders Draft have full fill payment',
                config_id: this.config.id
            };
            let sending = function () {
                return session.rpc("/pos/automation/paid_orders", params, {
                    shadow: true,
                    timeout: 65000,
                });
            };
            return sending().then(function (result) {
                result = JSON.parse(result);
                if (result['values'].length > 0) {
                    self.alert_message({
                        title: _t('Succeed'),
                        body: _t('Orders: ' + result['values'] + _t(' processed to paid')),
                        color: 'success'
                    })
                }
                setTimeout(_.bind(self.polling_job_auto_paid_orders_draft, self), 3000);
            }, function (err) {
                setTimeout(_.bind(self.polling_job_auto_paid_orders_draft, self), 3000);
            });
        },
        save_pos_screen_parameter_models_and_fields_load: function(){
            let self = this;// TODO: Save pos screen parameter models and fields
            let vals = {}
            for(let model of self.models){
                if(model.model && model.fields){
                    vals[model.model] = { fields: model.fields }
                }
            }
            if(!vals['stock.picking']){
                vals['stock.picking'] = { fields: ['id', 'pos_order_id'] }
            }
            if(!vals['stock.move']){
                vals['stock.move'] = { fields: ['id','combo_item_id', 'picking_id', 'product_id', 'product_uom_qty'] }
            }
            if(!vals['res.partner.title']){
                vals['res.partner.title'] = { fields: ['id','name'] }
            }
            if(!vals['account.payment.term']){
                vals['account.payment.term'] = { fields: ['id', 'name'] }
            }
            if(!vals['account.journal']){
                vals['account.journal'] = { fields: ['id','company_id','name','code','pos_method_type','profit_account_id',
                    'loss_account_id','currency_id','decimal_rounding','inbound_payment_method_ids',
                    'outbound_payment_method_ids'] }
            }
            if(!vals['pos.combo.limit']){
                vals['pos.combo.limit'] = { fields: ['id','product_tmpl_id','pos_categ_id','quantity_limited','default_product_ids'] }
            }
            self.rpc({
                model: 'pos.cache.database',
                method: 'save_pos_screen_parameter_models_and_fields_load',
                args: [null, vals]
            }, {
                shadow: true,
                timeout: 5000 // 5 seconds
            }).then(function (result) {
                console.warn('[save_pos_screen_parameter_models_and_fields_load] vals:', vals)
            });
        },
        load_server_data: function () {
            console.log('load_server_data 5')
            const self = this;

            self.save_pos_screen_parameter_models_and_fields_load();

            return _super_PosModel.load_server_data.apply(this, arguments).then(function () {
                let employee_ids = _.map(self.employees, function (employee) {
                    return employee.id;
                });
                let records = self.rpc({
                    model: 'hr.employee',
                    method: 'get_barcodes_and_pin_hashed',
                    args: [employee_ids],
                });
                records.then(function (employee_data) {
                    self.employees.forEach(function (employee) {
                        let data = _.findWhere(employee_data, {'id': employee.id});
                        if (data !== undefined) {
                            employee.barcode = data.barcode;
                            employee.pin = data.pin;
                        }
                    });
                });
                self.posSyncBackend = new exports.posSyncBackend(self);
                self.posSyncBackend.start();
                if (self.config.backup_orders_automatic) {
                    return self.restore_orders().then(function () {
                        self.automaticBackupUnpaidOrders();
                    })
                } else {
                    return true
                }
            })
        },
        initialize: function (session, attributes) {
            let pos_category_model = this.get_model('pos.category');
            if (pos_category_model) {
                pos_category_model.domain = function (self) {
                    if (self.config.limit_categories) {
                        return self.config.limit_categories && self.config.iface_available_categ_ids.length ? [['id', 'in', self.config.iface_available_categ_ids]] : [];
                    } else {
                        return []
                    }
                };
                pos_category_model.fields.push('image_128')
                pos_category_model.fields.push('category_type')

            }
            _super_PosModel.initialize.call(this, session, attributes);
            this.models = this.models.concat(extend_models);
        },

        //TODO: remove duplicate records from object
        sync_models_unique_object: function(object, updated_object_ids){
            for (let object_id in object){
                if (updated_object_ids.includes(parseInt(object_id))){
                    object[object_id] = [...new Map(object[object_id].map(item => [item['id'], item])).values()];
                }
            }
        },
        //TODO: remove duplicate records from list
        sync_models_unique_list: function(list){
            return [...new Set(list)];
        },
        //TODO: remove duplicate records from list of object
        sync_models_unique_list_object: function(list){
            return [...new Map(list.map(item => [item['id'], item])).values()];
        },

    });

    return exports;
});
