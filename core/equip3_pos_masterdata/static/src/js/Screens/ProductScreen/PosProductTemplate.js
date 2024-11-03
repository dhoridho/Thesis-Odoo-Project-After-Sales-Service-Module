odoo.define('equip3_pos_masterdata.PosProductTemplate', function (require) {
"use strict";

var models = require('point_of_sale.models');
var PosDB = require("point_of_sale.DB");
const time = require('web.time');
const core = require('web.core');
const utils = require('web.utils');
const QWeb = core.qweb;
var round_pr = utils.round_precision;
const  exports = {};
var Orderline_super = models.Orderline.prototype;
PosDB.include({
    init: function(options){
        this.product_template_by_id = {};
        this.product_template_by_barcode = {};
        this.product_template_by_category_id = {};
        this.product_attribute_by_id = {};
        this.product_attribute_value_by_id = {};
        this._super(options);
    },
    get_product_template_by_id: function(id){
        return this.product_template_by_id[id];
    },
    get_product_template_by_ids: function(template_ids){
        var list = [];
        for (var i = 0, len = template_ids.length; i < len; i++) {
            if(this.product_template_by_id[template_ids[i]]) list.push(this.product_template_by_id[template_ids[i]]);
        }
        return list;
    },
    search_product_template_in_category: function (category_id, query) {
        let self = this;
        try {
            query = query.replace(/[\[\]\(\)\+\*\?\.\-\!\&\^\$\|\~\_\{\}\:\,\\\/]/g,'.');
            query = query.replace(/ /g,'.+');
            var re = RegExp("([0-9]+):.*?"+utils.unaccent(query),"gi");
        }catch(e){
            return [];
        }
        var results = [];
        for(var i = 0; i < this.limit; i++){
            var r = re.exec(this.category_search_string[category_id]);
            if(r){
                var id = Number(r[1]);
                results.push(this.get_product_template_by_id(id));
            }else{
                break;
            }
        }

        results = _.filter(results, function (product) {
            return self.products_removed.indexOf(product['id']) == -1
        });
        return results;
    },
    get_product_by_value_and_products: function(value_id, products){
        var list = [];
        for (var i = 0, len = products.length; i < len; i++) {
            if (products[i].attribute_value_ids.indexOf(value_id) != -1){
                list.push(products[i]);
            }
        }
        return list;
    },
    get_product_attribute_by_id: function(attribute_id){
        return this.product_attribute_by_id[attribute_id];
    },
    get_product_attribute_value_by_id: function(attribute_value_id){
        return this.product_attribute_value_by_id[attribute_value_id];
    },
    attribute_by_template_id: function(template_id){
        var template = this.product_template_by_id[template_id];
        return this.attribute_by_attribute_value_ids(template.attribute_value_ids);
    },
    attribute_by_attribute_value_ids: function(value_ids){
        var attribute_ids = [];
        for (var i = 0; i < value_ids.length; i++){
            var value = this.product_attribute_value_by_id[value_ids[i]];
            if (attribute_ids.indexOf(value.attribute_id[0])==-1){
                attribute_ids.push(value.attribute_id[0]);
            }
        }
        return attribute_ids;
    },
    add_templates: function(templates){
        var stored_categories = this.product_template_by_category_id;

        if(!templates instanceof Array){
            templates = [templates];
        }
        for(var i = 0, len = templates.length; i < len; i++){
            var product_template = templates[i];
            // if (product_template.id in this.product_template_by_id) continue;
            if (product_template.available_in_pos){
                var search_string = utils.unaccent(this._product_search_string(product_template));
                var categ_id = product_template.pos_categ_id ? product_template.pos_categ_id[0] : this.root_category_id;
//                product_template.product_tmpl_id = product_template.product_tmpl_id[0];
                if(!stored_categories[categ_id]){
                    stored_categories[categ_id] = [];
                }
                stored_categories[categ_id].push(product_template.id);

                if(this.category_search_string[categ_id] === undefined){
                    this.category_search_string[categ_id] = '';
                }
                this.category_search_string[categ_id] += search_string;

                var ancestors = this.get_category_ancestors_ids(categ_id) || [];

                for(var j = 0, jlen = ancestors.length; j < jlen; j++){
                    var ancestor = ancestors[j];
                    if(! stored_categories[ancestor]){
                        stored_categories[ancestor] = [];
                    }
                    stored_categories[ancestor].push(product_template.id);

                    if( this.category_search_string[ancestor] === undefined){
                        this.category_search_string[ancestor] = '';
                    }
                    this.category_search_string[ancestor] += search_string;
                }
            }
            this.product_template_by_id[product_template.id] = product_template;
            if(product_template.barcode){
                this.product_template_by_barcode[product_template.barcode] = product_template;
            }
        }
    },
    add_products: function(products){
        this._super(products);
        var templates = this.templates;
        if(templates) {
            for (var i = 0; i < templates.length; i++) {
                var attribute_value_ids = [];
                // Update Product information
                var primary_variant = true;
                for (var j = 0; j < templates[i].product_variant_ids.length; j++) {
                    var product = this.product_by_id[templates[i].product_variant_ids[j]]
                    if (product && product.attribute_value_ids) {
                        for (var k = 0; k < product.attribute_value_ids.length; k++) {
                            if (attribute_value_ids.indexOf(product.attribute_value_ids[k]) == -1) {
                                attribute_value_ids.push(product.attribute_value_ids[k]);
                            }
                        }
                        product.product_variant_count = templates[i].product_variant_count;
                        product.is_primary_variant = primary_variant;
                        primary_variant = false;
                    }
                }
            }
        }
    },
    add_product_attributes: function(product_attributes){
        if (product_attributes) {
            for(var i=0 ; i < product_attributes.length; i++){
                // store Product Attributes
                this.product_attribute_by_id[product_attributes[i].id] = product_attributes[i];
            }
        }
    },
    add_product_attribute_values: function(product_attribute_values){
        if (product_attribute_values){
            for(var i=0 ; i < product_attribute_values.length; i++){
                // store Product Attribute Values
                this.product_attribute_value_by_id[product_attribute_values[i].id] = product_attribute_values[i];
            }
        }
    },
    get_product_template_by_category: function (category_id) {
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
        list = list.filter(p => p.sale_ok && p.available_in_pos)
        return list;
    }
});

exports.ProductTemplate = Backbone.Model.extend({
    initialize: function(attr, options){
        _.extend(this, options);
    },
    isAllowOnlyOneLot: function() {
        const productUnit = this.get_unit();
        return this.tracking === 'lot' || !productUnit || !productUnit.is_pos_groupable;
    },
    get_unit: function() {
        var unit_id = this.uom_id;
        if(!unit_id){
            return undefined;
        }
        unit_id = unit_id[0];
        if(!this.pos){
            return undefined;
        }
        return this.pos.units_by_id[unit_id];
    },


    covertCurrency(pricelist, price) {
        let baseCurrency = this.pos.currency_by_id[this.pos.config.currency_id[0]];
        if (pricelist.currency_id && baseCurrency && baseCurrency.id != pricelist.currency_id[0]) {
            let currencySelected = this.pos.currency_by_id[pricelist.currency_id[0]];
            if (currencySelected && currencySelected['converted_currency'] != 0) {
                price = (currencySelected['converted_currency'] * price);
            }
        }
        return price
    },

    get_product_bundles() {
        if(this.pos.product_bundle_by_product_tmpl_id && this.id){
            let bundles = this.pos.product_bundle_by_product_tmpl_id[this.id];
            if(bundles && bundles.length){
                return bundles;
            }
        }
        return [];
    },

    get_qty_available() {
        var qty = 0;
        if(!this.pos.stock_quant_by_product_tmpl_id){
            return 0;
        }
        let stock_locations = this.pos.db.get_pos_stock_locations();
        if(!stock_locations){
            return 0;
        }

        let product_bundles = this.get_product_bundles();
        if(product_bundles.length){
            // TODO: Get qty available to buy, base on the lowes qty available in the bundles
            let qty_available_in_the_bundles = [];
            for(let bundle of product_bundles){
                let quantity = 0;
                if(this.pos.stock_quant_by_product_id){
                    let stock_quants = this.pos.stock_quant_by_product_id[bundle.product_id[0]];
                    if(stock_quants){
                        for (let quant of stock_quants){
                            if(stock_locations.includes(quant.location_id[0])){
                                quantity += quant.quantity;
                            }
                        } 
                    }
                }
                qty_available_in_the_bundles.push((quantity - (quantity%bundle.qty_uom) ) / bundle.qty_uom);
            }
            let qty_available = Math.min.apply(Math, qty_available_in_the_bundles);
            qty_available = qty_available<0?0:qty_available;
            qty += qty_available;
        }else{
            let stock_quants = this.pos.stock_quant_by_product_tmpl_id[this.id];
            if(stock_quants){
                for (let quant of stock_quants){
                    if(stock_locations.includes(quant.location_id[0])){
                        qty += quant.quantity;
                    }
                }
            }
        }
        return qty;
    },

    get_price: function (pricelist, quantity, price_extra, uom_id) {
        var price = this.get_price_with_pricelist(pricelist, quantity, price_extra, uom_id)[0];
        return price;
    },

    get_price_without_tax: function (pricelist, quantity, price_extra, uom_id) {
        let self = this;
            
        if (!quantity) {
            quantity = 1
        }
        var price = self['lst_price']
        if (!pricelist) {
            price =  self['lst_price'];
        }
        else{
            price = this.get_price_with_pricelist(pricelist, 1)[0]
        }

        var taxes =  this.pos.taxes;
        var taxes_ids = _.filter(self.taxes_id, t => t in self.pos.taxes_by_id);
        var tax_included = 0
        if(taxes_ids){
            var product_taxes = [];
            _(taxes_ids).each(function(el){
                var tax = _.detect(taxes, function(t){
                    return t.id === el;
                });
                product_taxes.push.apply(product_taxes, [tax]);
            });
            product_taxes = _.uniq(product_taxes, function(tax) { return tax.id; });
            var orderline = Orderline_super;
            Orderline_super.pos = this.pos
            var all_taxes = orderline.compute_all(product_taxes, price, 1,0.0000001);
            _(all_taxes.taxes).each(function(tax) {
                var taxdetail =  taxes.filter(p => p.id == tax.id) 
                if(taxdetail){
                    if(taxdetail[0].price_include){
                        tax_included+=tax.amount
                    }
                }
            });
        }
        price -=tax_included
        if (!pricelist) {
            return price
        }
        price = this.covertCurrency(pricelist, price);
        return price;
    },

    get_price_with_pricelist: function (pricelist, quantity, price_extra, uom_id) {
        let self = this;
        let rule_base = false;
        if (!quantity) {
            quantity = 1
        }
        let price = self['lst_price'];

        if(pricelist){
            let cache_price = self.pos.db.get_cache_product_price('product.template', self.id);
            if(cache_price){
                return [cache_price.price, cache_price.rule];
            }
        }

        let tax_amount = 0;
        var taxes =  this.pos.taxes;
        var taxes_ids = _.filter(self.taxes_id, t => t in self.pos.taxes_by_id);
        if(taxes_ids){
            var product_taxes = [];
            var taxtotal = 0;

            _(taxes_ids).each(function(el){
                var tax = _.detect(taxes, function(t){
                    return t.id === el;
                });
                product_taxes.push.apply(product_taxes, [tax]);
            });
            product_taxes = _.uniq(product_taxes, function(tax) { return tax.id; });
            var orderline = Orderline_super;
            Orderline_super.pos = this.pos
            var all_taxes = orderline.compute_all(product_taxes, price, 1,0.0000001);
            var tax_included = 0
            _(all_taxes.taxes).each(function(tax) {
                taxtotal += tax.amount;
                var taxdetail =  taxes.filter(p => p.id == tax.id) 
                if(taxdetail){
                    if(taxdetail[0].price_include){
                        tax_included+=tax.amount
                    }
                }
            });
            var tax_discount_policy = self.pos.company.tax_discount_policy
            if (tax_discount_policy!='untax'){
                price = round_pr(all_taxes['total_excluded']+tax_included, rounding)
            }
            else {
                var rounding = this.pos.currency.rounding;
                 price = round_pr(all_taxes['total_excluded']+tax_included, rounding)
            }
        }

        if (!pricelist) {
            self.pos.db.set_cache_product_price('product.template', self.id, { price: price, rule: rule_base });
            return [price,rule_base];
        }

        let date = moment(moment().utc().format('YYYY-MM-DD HH:mm:ss'), 'YYYY-MM-DD HH:mm:ss');
        let category_ids = [];
        let category = self.categ_id;
        while (category) {
            category_ids.push(category[0]);
            var categ_detail = self.pos.product_categories.filter(p => p.id == category[0])      
            if(categ_detail) {
                var categ_parent = categ_detail[0].parent_id
                category = categ_parent;
            }
            else{
                category = false
            }
                
        }
        let pos_category_ids = []
        let pos_category = self.pos_categ_id;
        while (pos_category) {
            pos_category_ids.push(pos_category[0]);
            var categ_detail = self.pos.pos_category_by_id[pos_category[0]]      
            if(categ_detail) {
                var categ_parent = categ_detail.parent_id
                pos_category = categ_parent;
            }
            else{
                pos_category = false
            }
                
        }
        if(self.multi_category){
            for (var i = 0; i < self.pos_categ_ids.length; i++) {
                var itempci = self.pos_categ_ids[i];
                pos_category = [itempci]
                while (pos_category) {
                    pos_category_ids.push(pos_category[0]);
                    var categ_detail = self.pos.pos_category_by_id[pos_category[0]]      
                    if(categ_detail) {
                        var categ_parent = categ_detail.parent_id
                        pos_category = categ_parent;
                    }
                    else{
                        pos_category = false
                    }
                        
                }
            }
        }

        var pricelist_items = [];
        if(!uom_id){
            uom_id = this.uom_id[0]
        }
        for (let i = 0; i < pricelist.items.length; i++) {
            
            let item = pricelist.items[i];
            if(item.pricelist_uom_id && item.pricelist_uom_id[0]!=uom_id){
                continue
            }
            if ((!item.date_start || moment(item.date_start).isSameOrBefore(date)) && (!item.date_end || moment(item.date_end).isSameOrAfter(date))){
                if (quantity<item.min_quantity){
                    continue
                }
                if(item.applied_on=='0_product_variant' && item.product_id && this.product_variant_count <= 1){
                    if(item.product_id[0] === self.product_variant_ids[0]){
                        pricelist_items.push(item)
                    }
                }
                else if(item.applied_on=='1_product' && item.id) {
                    if(item.product_tmpl_id[0] === self.id){
                        pricelist_items.push(item)
                    }
                }
                else if(item.applied_on=='4_pos_category' && item.pos_category_id){
                    if(_.contains(pos_category_ids, item.pos_category_id[0])){
                        pricelist_items.push(item)
                    }
                }
                else if(item.applied_on=='2_product_category' && item.categ_id && self.categ_id) {
                    if(_.contains(category_ids, item.categ_id[0])){
                        pricelist_items.push(item)
                    }
                }
                else if(item.applied_on=='3_global'){
                    pricelist_items.push(item)
                }
            }
                
        }

        // Re-ordering the pricelist_items based on min qty settings
        const pricelist_items_sort_by_min_qty = [];
        for (const object of pricelist_items) {
            pricelist_items_sort_by_min_qty.push(object);
        }
        pricelist_items_sort_by_min_qty.sort((a, b) => b['min_quantity'] - a['min_quantity']);
        pricelist_items = pricelist_items_sort_by_min_qty

        var new_pricelist_items = pricelist_items.filter(r => (r.applied_on=='0_product_variant'))
        if (new_pricelist_items.length==0){
            new_pricelist_items = pricelist_items.filter(r => (r.applied_on=='1_product'))
        }
        if (new_pricelist_items.length==0){
            new_pricelist_items = pricelist_items.filter(r => (r.applied_on=='4_pos_category'))
        }
        if (new_pricelist_items.length==0){
            new_pricelist_items = pricelist_items.filter(r => (r.applied_on=='2_product_category'))
        }
        if (new_pricelist_items.length==0){
            new_pricelist_items = pricelist_items.filter(r => (r.applied_on=='3_global'))
        }
        if(new_pricelist_items.length > 0){
            pricelist_items=new_pricelist_items
        }

        var rounding = this.pos.currency.rounding;
        _.find(pricelist_items, function (rule) {
            if (rule.base === 'pricelist') {
                price = self.get_price(rule.base_pricelist, quantity, uom_id);
            } else if (rule.base === 'standard_price') {
                price = self.standard_price;
            }
            if (rule.compute_price === 'fixed') {
                price = rule.fixed_price;
                rule_base = 'fixed'

                if (price<rule.minimum_price && rule.minimum_price){
                    price = rule.minimum_price
                }
                if (price>rule.maximum_price && rule.maximum_price){
                    price = rule.maximum_price
                }
                return true;
            } else if (rule.compute_price === 'percentage') {
                price = price - (price * (rule.percent_price / 100));

                if (price<rule.minimum_price && rule.minimum_price){
                    price = rule.minimum_price
                }
                if (price>rule.maximum_price && rule.maximum_price){
                    price = rule.maximum_price
                }
                return true;
            } else {
                let price_limit = price;
                price = price - (price * (rule.price_discount / 100));
                if (rule.price_round) {
                    price = round_pr(price, rule.price_round);
                }
                if (rule.price_surcharge && rule.type_surcharge == 'fixed') {
                    price += rule.price_surcharge;
                }
                if (rule.price_surcharge && rule.type_surcharge == 'percentage') {
                    var price_surcharge_percent = parseFloat((rule.price_surcharge/100).toFixed(2))
                    price += price * price_surcharge_percent;
                }

                if (rule.price_min_margin) {
                    let margin_amount = price_limit * rule.price_min_margin/100.0;
                    price = Math.max(price, price_limit + margin_amount);
                }
                if (rule.price_max_margin) {
                    let margin_amount = price_limit * rule.price_max_margin/100.0;
                    price = Math.min(price, price_limit + margin_amount);
                }

                if (price<rule.minimum_price && rule.minimum_price){
                    price = rule.minimum_price
                }
                if (price>rule.maximum_price && rule.maximum_price){
                    price = rule.maximum_price
                }
                return true;
            }
            return false;
        });
        price = this.covertCurrency(pricelist, round_pr(price, rounding));

        self.pos.db.set_cache_product_price('product.template', self.id, { price: price, rule: rule_base });
        return [price,rule_base];
    },

    get_pricelist_item_applied: function (pricelist, quantity, uom_id) {
        if (pricelist['items'] == undefined) {
            null
        }
        let date = moment().startOf('day');
        let category_ids = [];
        let category = this.categ;
        while (category) {
            category_ids.push(category.id);
            category = category.parent;
        }
        let pos_category_ids = []
        let pos_category = this.pos_category;
        while (pos_category) {
            pos_category_ids.push(pos_category.id);
            pos_category = pos_category.parent;
        }
        let pricelist_items = [];
        for (let i = 0; i < pricelist.items.length; i++) {
            let item = pricelist.items[i];
            if ((!item.product_tmpl_id || item.product_tmpl_id[0] === this.product_tmpl_id) &&
                (!item.product_id || item.product_id[0] === this.id) &&
                (!item.categ_id || _.contains(category_ids, item.categ_id[0])) &&
                (!item.pos_category_id || _.contains(pos_category_ids, item.pos_category_id[0])) &&
                (!item.date_start || moment(item.date_start).isSameOrBefore(date)) &&
                (!item.date_end || moment(item.date_end).isSameOrAfter(date))) {
                pricelist_items.push(item)
            }
        }
        let ret_pricelist_item = null;
//            pricelist_items = pricelist_items.filter(pi => (((uom_id && pi['uom_id'] && pi['uom_id'][0] == uom_id)) || (!uom_id)) && pi['min_price'] != undefined && pi['max_price'] != undefined && pi['max_price'] >= pi['min_price'])
        pricelist_items = pricelist_items.filter(pi => ((uom_id && pi['pricelist_uom_id'] && pi['pricelist_uom_id'][0] == uom_id) || !pi['pricelist_uom_id']) && pi['min_price'] != undefined && pi['max_price'] != undefined && pi['max_price'] >= pi['min_price'])
        if (pricelist_items.length >= 1) {
            ret_pricelist_item = pricelist_items[0]
        }
        return ret_pricelist_item;
    },
    /*
        This function return product amount with default tax set on product > sale > taxes
     */
    get_price_with_tax: function (pricelist) {
        let self = this;
        let price;
        let price_pricelist;
        let tax_discount_policy = self.pos.company.tax_discount_policy;

        if (pricelist) {
            price = this.get_price_with_pricelist(pricelist, 1)[0];
            price_pricelist = price;
        } else {
            price = self['lst_price'];
            price_pricelist = price
        }
        
        // if (tax_discount_policy=='untax'){
        //     price = price_pricelist
        // }

        let taxes_id = self['taxes_id'];
        if (!taxes_id) {
            return price_pricelist;
        }
        let tax_amount = 0;
        var taxes =  this.pos.taxes;
        var taxes_ids = _.filter(self.taxes_id, t => t in self.pos.taxes_by_id);
        if(taxes_ids){
            var product_taxes = [];
            var taxtotal = 0;

            _(taxes_ids).each(function(el){
                var tax = _.detect(taxes, function(t){
                    return t.id === el;
                });
                product_taxes.push.apply(product_taxes, [tax]);
            });
            product_taxes = _.uniq(product_taxes, function(tax) { return tax.id; });
            var orderline = Orderline_super;
            Orderline_super.pos = this.pos
            var tax_included = 0
            var all_taxes = orderline.compute_all(product_taxes, price, 1,0.0000001);
            _(all_taxes.taxes).each(function(tax) {
                taxtotal += tax.amount;
                var taxdetail =  taxes.filter(p => p.id == tax.id)  
                if(taxdetail){
                    if(taxdetail[0].price_include){
                        tax_included+=tax.amount
                        if(tax_discount_policy=='untax'){
                            taxtotal -= tax.amount;
                        }
                    }
                }
            });
            if (tax_discount_policy!='untax'){
                price = round_pr(all_taxes['total_excluded'] + tax_included, rounding)
            }
            else {
                var rounding = this.pos.currency.rounding;
                 price = round_pr(all_taxes['total_excluded']+tax_included, rounding)
            }

        }
        // if (tax_discount_policy!='untax'){
        //     if(price!=price_pricelist){
        //         var diff_price = price - price_pricelist
        //         var disc = (diff_price / price)*100
        //         price = price - (price*(disc/100))
        //     }
        // }
        

        if (taxtotal) {
            return price + taxtotal - tax_included
        } else {
            return price
        }
    },
});

models.load_models([{
    model: 'product.template',
    fields: [
        'name',
        'display_name',
        'categ_id',
        'lst_price',
        'product_variant_id',
        'product_variant_ids',
        'product_variant_count',
        'tracking',
        'sale_ok',
        'taxes_id',
        'active',
        'barcode',
        'pos_categ_id',
        'standard_price',
        'to_weight',
        'uom_id',
        'default_code',
        'available_in_pos',
    ],
    domain: function (self) {
        let domains = [
            ['available_in_pos', '=', true],
            ['sale_ok', '=', true]
        ];
        return domains
    },
    loaded: function (self, templates) {
        if(self.config && self.config.display_product_name_without_product_code){
            templates.forEach((curr, index, arr) => {
                let full_name = curr.display_name;
                full_name = full_name.replace(/[\[].*?[\]] */, '');
                if(curr.default_code){
                    full_name = curr.display_name.replace('['+curr.default_code+'] ', '');
                }
                templates[index].display_name = full_name
            });
        }
        var using_company_currency = self.config.currency_id[0] === self.company.currency_id[0];
        var conversion_rate = self.currency.rate / self.company_currency.rate;
        self.db.add_templates(_.map(templates, function (template) {
            if (!using_company_currency) {
                template.lst_price = round_pr(template.lst_price * conversion_rate, self.currency.rounding);
            }
            template.categ = _.findWhere(self.product_categories, {'id': template.categ_id[0]});
            template.pos = self;
            return new exports.ProductTemplate({}, template);
        }));
    }
}]);

return exports;

});
