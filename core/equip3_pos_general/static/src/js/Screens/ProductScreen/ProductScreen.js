odoo.define('equip3_pos_general.ProductScreen', function (require) {
    'use strict';

    const ProductScreen = require('point_of_sale.ProductScreen')
    const Registries = require('point_of_sale.Registries')
    const {posbus} = require('point_of_sale.utils')
    const {useListener} = require('web.custom_hooks')
    const {useState} = owl.hooks
    const {Gui} = require('point_of_sale.Gui')
    const NumberBuffer = require('point_of_sale.NumberBuffer');
    const {useBarcodeReader} = require('point_of_sale.custom_hooks');


    const GenProductScreen = (ProductScreen) =>
        class extends ProductScreen {
            constructor() {
                super(...arguments);
            }

            mounted() {
                super.mounted();
            }

            willUnmount() {
                super.willUnmount()
            }

            _weight_scale_barcode(code) {
                var notfound = true
                var weight_scale = this.env.pos.db.pos_weight_scale_barcode_format
                if (!code || code == "" || !this.env.pos.config.weight_scale_barcode_format_id) {
                    return false
                }

                var data = weight_scale.filter((r)=>{return r.id == this.env.pos.config.weight_scale_barcode_format_id[0]});  
                if(data){
                    data = data[0]
                    var dictdata = {}
                    if (data.total_digit==code.length){
                        var weight_scale_line = this.env.pos.db.pos_weight_scale_barcode_format_line.filter((r)=>{return r.parent_id[0] == data.id});
                        var count_cut = 0
                        for (var io = 0; io < weight_scale_line.length; io++) {
                            var data_line = weight_scale_line[io]
                            var real_number = code.substr(count_cut, data_line.digit);
                            count_cut += data_line.digit
                            if(real_number.length > 0){
                                if (data_line.data=='Weight'){
                                    var c_ratio = '1'
                                    for (var io = 1; io < data_line.digit; io++) {
                                        c_ratio+='0'
                                    }
                                    c_ratio = data_line.coefficient_ratio / parseInt(c_ratio)
                                    real_number = parseInt(real_number) * c_ratio
                                }
                                dictdata[data_line.data] = real_number
                            }
                        }
                        if('Product Code' in dictdata){
                            var product = this.env.pos.db.getAllProducts().filter(p =>  p['default_code'] == dictdata['Product Code'] && p['to_weight'] == true)
                            if(product.length > 0){
                                notfound = false
                                var order = this.env.pos.get_order()
                                var dict_add = {'quantity': 1,'weight_scale':true}
                                if('Price' in dictdata){
                                    dict_add['price'] = parseInt(dictdata['Price'])
                                }
                                if('Weight' in dictdata){
                                    dict_add['quantity'] = dictdata['Weight'] 
                                }
                                order.add_product(product[0], dict_add);
                                return true
                            }
                        }
                    }
                }
                
                if(notfound){
                    return false
                }
            }

            async suggestItemsCrossSelling(product){
                let self = this;
                let order = false;
                let crossItems = false;
                let is_cross_selling = false;

                // TODO: only offer cross selling product once
                if(product.cross_selling) {
                    if(product.product_tmpl_id){
                        crossItems = self.env.pos.cross_items_by_product_tmpl_id[product.product_tmpl_id];
                        if(crossItems){
                            is_cross_selling = true;
                        }
                    }
                    if(is_cross_selling){
                        order = self.env.pos.get_order();
                        if (!order.already_suggest_cross_selling_ids) {
                            is_cross_selling = true;
                        } else {
                            is_cross_selling = true;
                            if(order.already_suggest_cross_selling_ids.includes(product.id)){
                                is_cross_selling = false;
                            }
                        }
                    }
                }

                if(is_cross_selling){
                    if (!order.already_suggest_cross_selling_ids) {
                        order.already_suggest_cross_selling_ids = []
                    }
                    order.already_suggest_cross_selling_ids.push(product.id);

                    let {confirmed, payload: results} =  await Gui.showPopup('CrossSalePopUps', {
                        title: self.env._t('Product Suggestions'),
                        items: crossItems 
                    });
                    if (confirmed) {
                        let selectedCrossItems = results.items;
                        for (let index in selectedCrossItems) {
                            let item = selectedCrossItems[index];
                            var _product = self.env.pos.db.get_product_by_id(item['product_id'][0]);
                            if(_product) {
                                var price = item['list_price'];
                                var discount = 0;
                                if (item['discount_type'] == 'fixed') {
                                    price = price - item['discount']
                                }
                                if (item['discount_type'] == 'percent') {
                                    discount = item['discount']
                                }
                                
                                var exist_in_orderline = false;
                                var is_pos_groupable = false;
                                if(order.get_orderlines().length > 1){
                                    for (var i = 0; i < order.orderlines.length; i++) {
                                        if(order.get_orderlines().at(i).product.id == _product.id){
                                            exist_in_orderline = order.get_orderlines().at(i);
                                            let orderline = order.get_orderlines().at(i);
                                            exist_in_orderline = orderline;
                                            is_pos_groupable = exist_in_orderline.get_unit().is_pos_groupable;
                                        }
                                    }
                                }

                                if(!is_pos_groupable){
                                    exist_in_orderline = false
                                }

                                if(!exist_in_orderline){
                                    order.add_product(_product, {
                                        quantity: item['quantity'],
                                        price: price,
                                        merge: false,
                                        extras: {
                                            is_from_cross_sale: true,
                                        }
                                    });
                                }
                                
                                if(exist_in_orderline){
                                   exist_in_orderline.set_quantity( exist_in_orderline.get_quantity() + 1);
                                }

                                if (discount > 0) {
                                    order.get_selected_orderline().set_discount(discount)
                                }
                            }
                        }
                    }
                }
                return Promise.resolve(is_cross_selling);
            }

            async _clickProduct(event) {
                super._clickProduct(event);                
                let self = this;
                let product = self.get_product_object(event.detail);
                if(product.product_variant_ids){
                    product = self.env.pos.db.get_product_by_id(product.product_variant_ids[0]);
                }
                await self.suggestItemsCrossSelling(product);
            }
 
        }

    Registries.Component.extend(ProductScreen, GenProductScreen);
    return GenProductScreen;
});
