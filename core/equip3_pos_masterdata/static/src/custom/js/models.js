odoo.define('equip3_pos_masterdata.custom_models', function (require) {
    'use strict';
    var rpc = require('pos.rpc');
    var models = require('point_of_sale.models');
    var pos_re_models = require('equip3_pos_masterdata.load_models');
    var pos_re_order = require('equip3_pos_masterdata.order');
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


    models.load_models({
        model: 'combo.option',
        fields: ['combo_name','item_ids'],
        loaded: function(self,pos_combo_ids){
            self.db.add_pos_combo(pos_combo_ids);
        },
    })


    models.load_models({
        model: 'product.template.barcode',
        fields: ['write_date','active','name','id','product_uom_id','product_id','uom_id','product_uom_category_id'],
        loaded: function (self, product_multi_barcode) {
                if(!self.product_multi_barcode){
                    self.product_multi_barcode = product_multi_barcode;
                    self.product_multi_barcode_by_product_id = {};
                    for (var i = 0; i < self.product_multi_barcode.length; i++) {
                        var rec = self.product_multi_barcode[i];
                        var product_id = rec.product_id[0]

                        if (!self.product_multi_barcode_by_product_id[product_id]) {
                            self.product_multi_barcode_by_product_id[product_id] = [rec];
                        } else {
                            self.product_multi_barcode_by_product_id[product_id].push(rec);
                        }
                    }
                }
                else{
                    for (var i = 0; i < product_multi_barcode.length; i++) {
                        var rec = product_multi_barcode[i];
                        var product_id = rec.product_id[0]
                        
                        var check = self.product_multi_barcode.findIndex(el => el.id === rec.id)
                        if(check>=0){
                            self.product_multi_barcode.splice(check, 1);
                        }   
                        self.product_multi_barcode.push(rec)

                        if (!self.product_multi_barcode_by_product_id[product_id]) {
                            self.product_multi_barcode_by_product_id[product_id] = [rec]
                        }
                        else{
                            var check = self.product_multi_barcode_by_product_id[product_id].findIndex(el => el.id === rec.id)
                            if(check>=0){
                                self.product_multi_barcode_by_product_id[product_id].splice(check, 1);
                            }
                            self.product_multi_barcode_by_product_id[product_id].push(rec)
                        }
                    }
                }
            }
    })


    models.load_models({
        model: 'product.brand',
        fields: ['brand_name','write_date','active'],
        loaded: function(self,brands){
            if(!self.pos_product_brands){
                self.pos_product_brands = brands;
            }
            else{
                for (var i = 0; i < brands.length; i++) {
                    var check = self.pos_product_brands.findIndex(el => el.id === brands[i].id)
                    if(check>=0){
                        self.pos_product_brands.splice(check, 1);
                    }
                    self.pos_product_brands.push(brands[i])
                }
            }
            
        },
    })



    models.load_models([
    {
        model: 'stock.quant',
        fields: ['write_date','active','display_name','location_id','product_uom_id','company_id','lot_id','product_id','product_tmpl_id','tracking','warehouse_id','quantity'],
        loaded: function (self, stock_quant) {
                if(!self.stock_quant){
                    self.stock_quant = stock_quant;
                    self.stock_quant_by_product_tmpl_id = {};
                    self.stock_quant_by_product_id = {};
                    for (var i = 0; i < self.stock_quant.length; i++) {
                        var rec_stock_quant = self.stock_quant[i];
                        var product_id = rec_stock_quant.product_id[0]
                        var product_tmpl_id = rec_stock_quant.product_tmpl_id[0]

                        if (!self.stock_quant_by_product_tmpl_id[product_tmpl_id]) {
                            self.stock_quant_by_product_tmpl_id[product_tmpl_id] = [rec_stock_quant];
                        } else {
                            self.stock_quant_by_product_tmpl_id[product_tmpl_id].push(rec_stock_quant);
                        }

                        if (!self.stock_quant_by_product_id[product_id]) {
                            self.stock_quant_by_product_id[product_id] = [rec_stock_quant];
                        } else {
                            self.stock_quant_by_product_id[product_id].push(rec_stock_quant);
                        }
                    }
                }
                else{
                    for (var i = 0; i < stock_quant.length; i++) {
                        var rec_stock_quant = stock_quant[i];
                        var product_id = rec_stock_quant.product_id[0]
                        var product_tmpl_id = rec_stock_quant.product_tmpl_id[0]
                        
                        var check = self.stock_quant.findIndex(el => el.id === rec_stock_quant.id)
                        if(check>=0){
                            self.stock_quant.splice(check, 1);
                        }   
                        self.stock_quant.push(rec_stock_quant)

                        if(self.stock_quant_by_product_tmpl_id[product_tmpl_id]){
                            var check = self.stock_quant_by_product_tmpl_id[product_tmpl_id].findIndex(el => el.id === rec_stock_quant.id)
                            if(check>=0){
                                self.stock_quant_by_product_tmpl_id[product_tmpl_id].splice(check, 1);
                            }
                            self.stock_quant_by_product_tmpl_id[product_tmpl_id].push(rec_stock_quant)
                        }
                        else{
                            self.stock_quant_by_product_tmpl_id[product_tmpl_id] = [rec_stock_quant]
                        }

                        if(self.stock_quant_by_product_id[product_id]){
                            var check = self.stock_quant_by_product_id[product_id].findIndex(el => el.id === rec_stock_quant.id)
                            if(check>=0){
                                self.stock_quant_by_product_id[product_id].splice(check, 1);
                            }
                            self.stock_quant_by_product_id[product_id].push(rec_stock_quant)
                        }
                        else{
                            self.stock_quant_by_product_id[product_id] = [rec_stock_quant]
                        }
                    }
                }
            }
    },
    {
        model: 'bi.product.pack',
        fields: [
            'write_date',
            'product_id',
            'bi_product_template',
            'qty_uom',
        ],
        domain: function (self) {
            return [['bi_product_template.available_in_pos','=', true]]
        },
        loaded: function (self, bundles) {
            if(!self.product_bundle_by_product_tmpl_id){
                self.product_bundle_by_product_tmpl_id = {}
            }

            for(let bundle of bundles){
                let product_id = bundle.product_id[0];
                let product_tmpl_id = bundle.bi_product_template[0];

                if (!self.product_bundle_by_product_tmpl_id[product_tmpl_id]) {
                    self.product_bundle_by_product_tmpl_id[product_tmpl_id] = [bundle];
                } else {
                    self.product_bundle_by_product_tmpl_id[product_tmpl_id].push(bundle);
                }
            }
        }
    },

    ]);

    models.load_fields('product.template', ['is_can_be_po','active', 'write_date', 'type','is_combo_product', 'combo_option_id', 'combo_option_items', 'is_employee_meal', 'product_brand_ids', 'cross_selling']);
    models.load_fields('product.product', ['is_can_be_po','name','active', 'write_date', 'type','is_combo_product', 'combo_option_id', 'combo_option_items', 'is_employee_meal', 'product_brand_ids', 'cross_selling']);
    models.load_fields("pos.promotion", ['is_stack', 'card_payment_id','new_type','new_based_on','discount_fixed_amount_lp','discount_fixed_amount_fo']);
    models.load_fields("pos.config", ['is_complementary', 'required_ask_seat', 'complementary_journal_id']);
    models.load_fields("res.users", ['cashier_code']);
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
            this.set_is_complementary(json.is_complementary);
        },
        export_as_JSON: function() {
            var res = _super_orderline.export_as_JSON.apply(this, arguments);
            res['item_state'] = this.get_item_state();
            if(this.get_item_state() == 'cancelled' && this.get_quantity() != 0){
                this.set_quantity(0);
            }
            res['required_ask_seat'] = this.get_required_ask_seat();
            res['is_complementary'] = this.get_is_complementary();
            return res;
        },
        export_for_printing: function(){
            var receipt_template = this.pos.get_receipt_template()
            var res = _super_orderline.export_for_printing.apply(this, arguments);
            var lot_sn = ''
            if(this.get_lot_lines()){
                for (let i = 0; i < this.get_lot_lines().length; i++) {
                    lot_sn+=this.get_lot_lines()[i].attributes.lot_name + ' '
                }
            }
            var full_product_name = this.product.display_name
            if (full_product_name.indexOf('['+this.product.default_code+']') < 0&&this.product.default_code){
                full_product_name = '['+this.product.default_code+']'+' ' + full_product_name 
            }
            var is_receipt_tax_include_orderline = false
            if(receipt_template){
                is_receipt_tax_include_orderline = receipt_template.is_receipt_tax_include_orderline
            }
            var detail_all_price = this.get_all_prices()
            if(!is_receipt_tax_include_orderline){
                var price_with_pricelist = this.get_price_unit_w_pricelist_before_tax()
                var taxdetails = detail_all_price.taxdetail_name
            }
            else{
                var price_with_pricelist = this.get_price_unit_w_pricelist_after_tax()
                var taxdetails = {}
            }
            var name_promotion = '';
            var promotion_type = ''
            var promotion_discount = ''
            if (this.promotion){
                name_promotion = this.promotion_name
                promotion_type = this.promotion_type
                promotion_discount = Math.round(this.promotion_discount,1)+' %'
            }

            res['promotion_type'] = promotion_type
            res['promotion_discount'] = promotion_discount
            res['name_promotion'] = name_promotion
            res['receipt_template'] = receipt_template
            res['item_state'] = this.get_item_state();
            res['required_ask_seat'] = this.get_required_ask_seat();
            res['all_total_discount'] = this.get_all_total_discount();
            res['full_product_name'] = full_product_name
            res['product_only_name'] = this.product.display_name.replace('['+this.product.default_code+'] ', '');
            res['lot_sn'] = lot_sn
            res['price_with_pricelist'] = price_with_pricelist
            res['taxdetails'] = taxdetails
            res['pos_coupon_reward_description'] = this.pos_coupon_reward_description;
            res['pos_coupon_reward_discount'] = this.pos_coupon_reward_discount;
            res['pos_coupon_id'] = this.pos_coupon_id;
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
            var receipt_template = this.pos.get_receipt_template()
            var receipt = _super_order.export_for_printing.apply(this, arguments);
            var taxdetails = {}
            if(receipt && receipt.orderlines && receipt.orderlines.length){
                receipt['orderlines'] = receipt.orderlines.filter((line)=>{return line.item_state == 'ordered'});
            }
            var total_tax = 0
            if('orderlines' in receipt){
                for (let i = 0; i < receipt['orderlines'].length; i++) {
                    var line = receipt['orderlines'][i]
                    var taxdetails_line = line['taxdetails']
                    $.each(taxdetails_line, function (i, v) {
                        total_tax += v
                        if(i in taxdetails){
                            taxdetails[i] = taxdetails[i] + v
                        }
                        else{
                            taxdetails[i] = v
                        }
                    })
                }
            }

        
            
            receipt['total_discount_wo_pricelist'] = this.get_total_discount_wo_pricelist();
            receipt['total'] = this.get_total_with_tax() 
            receipt['taxtotal'] = this.get_total_with_tax_without_rounding() - this.get_total_without_tax()
            receipt['rounding_order'] = this.rounding_from_payment || 0 
            receipt['mdr_customer'] = this.total_mdr_amount_customer
            receipt['subtotal_without_tax'] = receipt['total'] - total_tax - receipt['rounding_order'] - receipt['mdr_customer']
            if (!receipt_template.is_receipt_disc_in_orderline){
                receipt['subtotal_without_tax'] += receipt['total_discount_wo_pricelist']
            }
            receipt['taxdetails'] = taxdetails

            if(receipt_template.icon_coupon_base64){
                receipt['icon_coupon_base64'] = receipt_template.icon_coupon_base64;
            }
            
            receipt['savings_summary_text'] = false;
            if(receipt_template.is_receipt_savings_summary && receipt_template.savings_summary_text){
                let savings_amount = this.get_savings_amount();
                if(savings_amount > 0){
                    receipt['savings_summary_text'] = receipt_template.savings_summary_text.replace('()', this.pos.format_currency(savings_amount));
                }
            }
            return receipt;
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
    });
    
});