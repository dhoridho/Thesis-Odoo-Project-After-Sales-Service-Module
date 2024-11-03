odoo.define('equip3_pos_masterdata.SyncNotification', function (require) {
    'use strict';

    const models = require('point_of_sale.models');
    const PosProductTemplate = require('equip3_pos_masterdata.PosProductTemplate');
    const SyncNotification = require('point_of_sale.SyncNotification');
    const Registries = require('point_of_sale.Registries');
    const Session = require('web.Session');
    const {posbus} = require('point_of_sale.utils');

    const RetailSyncNotification = (SyncNotification) =>
        class extends SyncNotification {
            constructor() {
                super(...arguments);
            }

            mounted() {
                super.mounted();
                this.automaticPushOrderToBackEnd();
                this.autoSyncProductStock();
                this.autoSyncProducts();
                this.autoSyncPricelist();
                this.autoSyncPromotion();
                this.autoSyncCoupon();
            }

            async automaticPushOrderToBackEnd() {
                const self = this;
                const ordersInCached = this.env.pos.db.get_orders();
                if (ordersInCached && ordersInCached.length > 0) {
                    console.log('[automaticPushOrderToBackEnd] auto running')
                    await this.env.pos.push_orders(null, {show_error: true}).then(function (order_ids) {
                        setTimeout(_.bind(self.automaticPushOrderToBackEnd, self), 1000);
                        console.log('[automaticPushOrderToBackEnd] saved new order id: ' + order_ids[0])
                    }, function (err) {
                        setTimeout(_.bind(self.automaticPushOrderToBackEnd, self), 1000);
                    });
                } else {
                    setTimeout(_.bind(self.automaticPushOrderToBackEnd, self), 1000);
                }
            }

            async clear_cache_product_price(){
                let self = this;
                let product_ids = [];
                self.env.pos.db.clear_cache_product_price();

                // Product display List Mode
                let $product1 = $('.product-list-scroller > table >tr[data-product-id]');
                $product1.each(function(){
                    product_ids.push($(this).data('product-id'));
                });

                // Product display Grid Mode
                let $product2 = $('.product-list > article.product[data-product-id]');
                $product2.each(function(){
                    product_ids.push($(this).data('product-id'));
                });

                let pricelist = self.env.pos._get_active_pricelist();

                product_ids = [... new Set(product_ids)];
                for (let product_id of product_ids){
                    let product = self.env.pos.db.get_product_template_by_id(product_id);
                    for (let variant_id of product.product_variant_ids){
                        let variant = self.env.pos.db.get_product_by_id(variant_id);
                        let variant_price = variant.get_price_with_pricelist(pricelist, 1);
                    }
                    let price = product.get_price_with_pricelist(pricelist, 1);
                }
                console.warn('[auto sync->clear_cache_product_price]: ', self.env.pos.db.cache_product_price);
            }

            
            async autoSyncProducts() {
                const self = this; 
                let timeout = 3000;
                if(!self.env.pos.config.is_auto_sync_product){
                    return false;
                }
                let process_sync_model = self.env.pos.process_sync_model;
                if(process_sync_model && process_sync_model['product.product']){
                    console.warn('[autoSyncProducts] ~ Skipped -> There is manual sync product ongoing')
                    setTimeout(_.bind(self.autoSyncProducts, self), 10000); // Check every 10 seconds
                    return false;
                }

                let product_template_fields = [
                    'active', 'available_in_pos', 'barcode', 'categ', 'categ_id', 'combo_option_id', 
                    'combo_option_items', 'cross_selling', 'default_code', 'display_name', 'id', 
                    'is_combo_product', 'is_combo_product_new', 'is_employee_meal', 'is_gift_product', 
                    'lst_price', 'model' ,'name', 'pos_bom_id', 'pos_categ_id', 'pos_combo_ids', 
                    'product_brand_ids', 'product_variant_count', 'product_variant_id', 'product_variant_ids', 
                    'sale_ok', 'standard_price', 'taxes_id', 'to_weight', 'tracking', 'type', 'uom_id', 
                    'write_date'
                ];
                let product_product_fields = [
                    'active', 'attribute_line_ids', 'available_in_pos', 'barcode', 'categ', 'categ_id', 
                    'combo_option_id', 'combo_option_items', 'cross_selling', 'default_code', 'default_time', 
                    'description', 'description_sale', 'display_name', 'id', 'is_combo_product', 
                    'is_employee_meal', 'is_combo_product_new', 'is_employee_meal', 'is_gift_product', 
                    'lst_price', 'model', 'name', 'not_returnable', 'pos_bom_id', 'pos_categ_id', 'pos_combo_ids', 
                    'product_brand_ids', 'product_tmpl_id', 'standard_price', 'taxes_id', 'to_weight', 'tracking', 
                    'type', 'uom_id', 'write_date','is_can_be_po'
                ];
                
                async function _update(records){
                    if(records <= 0){
                        return Promise.resolve(true);
                    }
                    let product_templates = [];
                    let product_products = [];
                    let removed_barcodes = [];
                    for (let record of records){
                        let product_template = await self.env.pos.indexed_db.get_data_by_id('product.template', record.product_tmpl_id[0]);
                        if(_.isEmpty(product_template)){
                            let product_template_obj = self.env.pos.db.product_template_by_id[record.product_tmpl_id[0]];
                            if(product_template_obj){
                                product_template = {};
                                for(let product_template_field of product_template_fields){
                                    product_template[product_template_field] = product_template_obj[product_template_field];
                                }
                            }
                        }
                        if(!_.isEmpty(product_template)){
                            let product_template_name = '';
                            if(record.product_tmpl_id){
                                product_template_name = record.product_tmpl_id[1];
                            }
                            product_template.write_date = record.write_date;
                            product_template.lst_price = record.lst_price;
                            product_template.display_name = product_template_name;
                            product_template.name = product_template_name.replace(/[\[].*?[\]] */, ''); // replace default code
                            product_template.pos_categ_id = record.pos_categ_id;
                            product_template.barcode = record.barcode;
                            product_templates.push(product_template);
                        }

                        let product_product = await self.env.pos.indexed_db.get_data_by_id('product.product', record.id);
                        if(_.isEmpty(product_product)){
                            let product_product_obj = self.env.pos.db.product_by_id[record.id];
                            if(product_product_obj){
                                product_product = {};
                                for(let product_product_field of product_product_fields){
                                    product_product[product_product_field] = product_product_obj[product_product_field];
                                }
                            }
                        }
                        if(!_.isEmpty(product_product)){

                            if(product_product.barcode != record.barcode){
                                removed_barcodes.push(product_product.barcode);
                            }
                            product_product.barcode = record.barcode; 

                            product_product.write_date = record.write_date;
                            product_product.lst_price = record.lst_price;
                            product_product.display_name = record.display_name;
                            product_product.name = record.name;
                            product_product.pos_categ_id = record.pos_categ_id;
                            product_products.push(product_product);
                        }
                    }

                    if(product_templates.length){
                        console.warn('[autoSyncProducts] updating variable product.template ->', product_templates)
                        self.env.pos.get_model('product.template').loaded(self.env.pos, product_templates);
                        self.env.pos.indexed_db.write('product.template', product_templates);
                        self.env.pos.db.add_templates(_.map(product_templates, function (template) {
                            template.categ = _.findWhere(self.env.pos.product_categories, {'id': template.categ_id[0]});
                            template.pos = self.env.pos;
                            return new PosProductTemplate.ProductTemplate({}, template);
                        }));
                        self.env.pos.save_results('product.template', records);
                    }

                    if(product_products.length){
                        console.warn('[autoSyncProducts] updating variable product.product ->', product_products)
                        self.env.pos.product_model.loaded(self.env.pos, product_products);
                        self.env.pos.indexed_db.write('product.product', product_products);
                        self.env.pos.db.add_products(_.map(product_products, function (product) {
                            product.categ = _.findWhere(self.env.pos.product_categories, {'id': product.categ_id[0]});
                            product.pos = self.env.pos;
                            return new models.Product({}, product);
                        }));
                        self.env.pos.save_results('product.product', product_products);
                    }
                    
                    if(removed_barcodes.length){
                        if(self.env.pos.db.product_by_barcode){
                            for(let removed_barcode of removed_barcodes){
                                if(self.env.pos.db.product_by_barcode[removed_barcode]){
                                    delete self.env.pos.db.product_by_barcode[removed_barcode];
                                }
                            }
                        }
                    } 

                    let product_product_ids = product_products.map((p)=>p.id);
                    if(product_product_ids.length){
                        self.clear_cache_product_price();
                        let currentOrder = self.env.pos.get_order();
                        if(currentOrder){
                            currentOrder.orderlines.models.forEach((line)=>{
                                if(product_product_ids.includes(line.product.id)){
                                    let product = self.env.pos.db.product_by_id[line.product.id];
                                    let price = product.get_price(line.order.pricelist, line.get_quantity(), line.get_price_extra());
                                    line.product.name = product.name;
                                    line.product.display_name = product.display_name;
                                    line.set_full_product_name(product.display_name);
                                    line.set_unit_price(price);
                                }
                            });
                            currentOrder.trigger('change');
                        }

                        posbus.trigger('reload-products-screen');
                        await new Promise(res=>setTimeout(res,500)); // 0.5 second to update variable
                    }
                    return Promise.resolve(true);
                }


                let monitor_vals = {
                    id: 'product_' + moment().format('MMDDHHmmss'),
                    type: 'product', sequence: moment().format('MMDDHHmmss'),
                    date: moment().format('YYYY-MM-DD HH:mm:ss'),
                }

                // TODO: Search product.product within limit, if the result count is more than limit do it with pagination
                let last_write_date = self.env.pos.db.write_date_by_model['product.product'];
                try {
                    let start_execute_time = Date.now();
                    let limit = 100;
                    let vals = { 'product.product': last_write_date, 'limit': limit, 'offset': 0 };
                    let res = await self.env.pos.search_model_datas('auto_sync_products', vals);
                    if (res) {

                        if(self.env.pos.config.is_monitor_auto_sync){
                            monitor_vals.total_unsync_data = res['product_product_count'];
                            monitor_vals.total_synced_data = res['product_product'].length;
                            monitor_vals.duration = Date.now() - start_execute_time;
                            self.trigger_update_monitor(monitor_vals);
                        }

                        await _update(res['product_product']);
                        let count = res['product_product_count'];
                        let pages = (( count - (count%limit) ) / limit) + (count%limit > 0?1:0);
                        for (let page = 1; page < pages; page++){
                            let next_res_start_execute_time = Date.now();
                            vals['offset'] = limit * page;
                            let next_res = await self.env.pos.search_model_datas('auto_sync_products', vals);
                            if (!next_res) { // second attempt if error
                                next_res = await self.env.pos.search_model_datas('auto_sync_products', vals);
                            }
                            if(next_res){
                                await _update(next_res['product_product']);

                                if(self.env.pos.config.is_monitor_auto_sync){
                                    monitor_vals.total_unsync_data = res['product_product_count'];
                                    monitor_vals.total_synced_data = next_res['product_product'].length;
                                    monitor_vals.duration = Date.now() - next_res_start_execute_time;
                                    self.trigger_update_monitor(monitor_vals);
                                }
                            }
                        }
                    }
                } catch(err) {
                    timeout = 7000;
                    console.error('[autoSyncProducts] ~ Error', err.message)
                }
                setTimeout(_.bind(self.autoSyncProducts, self), timeout); // Check every 3 seconds
            }
            
            async autoSyncProductStock() {
                const self = this;
                let timeout = 3000; 
                if(!self.env.pos.config.is_auto_sync_product_stock){
                    return false;
                }
                if(self.env.pos.process_sync_model){
                    if(self.env.pos.process_sync_model['product.product']){
                        console.warn('[autoSyncProductStock] ~ Skipped -> There is manual sync product ongoing')
                        setTimeout(_.bind(self.autoSyncProductStock, self), 10000); // Check every 10 seconds
                        return false;
                    }
                }

                async function _update(records){
                    if(records <= 0){
                        return Promise.resolve(true);
                    }
                    let active_records = records.filter(r => r['active'] == true);
                    if(active_records.length){
                        self.env.pos.stock_quant_model.loaded(self.env.pos, records);
                        self.env.pos.indexed_db.write('stock.quant', active_records);
                    }
                    self.env.pos.save_results('stock.quant', records);
                    self.env.pos.trigger('reload.quantity.available');
                    await new Promise(res=>setTimeout(res,500)); // 0.5 second to update variable
                    return Promise.resolve(true);
                }


                let monitor_vals = {
                    id: 'product_stock_' + moment().format('MMDDHHmmss'),
                    type: 'product_stock', sequence: moment().format('MMDDHHmmss'),
                    date: moment().format('YYYY-MM-DD HH:mm:ss'),
                }

                // TODO: Search stock.quant within limit, if the result count is more than limit do it with pagination
                let last_write_date = self.env.pos.db.write_date_by_model['stock.quant'];
                try {
                    let start_execute_time = Date.now();
                    let limit = 100;
                    let vals = { 'stock.quant': last_write_date, 'limit': limit, 'offset': 0 };
                    let res = await self.env.pos.search_model_datas('auto_sync_product_stock', vals);
                    if (res) {

                        if(self.env.pos.config.is_monitor_auto_sync){
                            monitor_vals.total_unsync_data = res['stock_quant_count'];
                            monitor_vals.total_synced_data = res['stock_quant'].length;
                            monitor_vals.duration = Date.now() - start_execute_time;
                            self.trigger_update_monitor(monitor_vals);
                        }

                        await _update(res['stock_quant']);
                        let count = res['stock_quant_count'];
                        let pages = (( count - (count%limit) ) / limit) + (count%limit > 0?1:0);
                        for (let page = 1; page < pages; page++){
                            let next_res_start_execute_time = Date.now();
                            vals['offset'] = limit * page;
                            let next_res = await self.env.pos.search_model_datas('auto_sync_product_stock', vals);
                            if (!next_res) { // second attempt if error
                                next_res = await self.env.pos.search_model_datas('auto_sync_product_stock', vals);
                            }
                            if(next_res){
                                await _update(next_res['stock_quant']);

                                if(self.env.pos.config.is_monitor_auto_sync){
                                    monitor_vals.total_unsync_data = res['stock_quant_count'];
                                    monitor_vals.total_synced_data = next_res['stock_quant'].length;
                                    monitor_vals.duration = Date.now() - next_res_start_execute_time;
                                    self.trigger_update_monitor(monitor_vals);
                                }
                            }
                        }
                    }
                } catch(err) {
                    timeout = 7000;
                    console.error('[autoSyncProductStock] ~ Error', err.message)
                }
                setTimeout(_.bind(self.autoSyncProductStock, self), timeout); // Check every 3 seconds
            }


            async autoSyncPricelist() {
                const self = this; 
                let timeout = 3000;
                if(!self.env.pos.config.is_auto_sync_pricelist){
                    return false;
                }
                let process_sync_model = self.env.pos.process_sync_model;
                if(process_sync_model){
                    if(process_sync_model['product.product'] || process_sync_model['product.pricelist.item']){
                        console.warn('[autoSyncPricelist] ~ Skipped -> There is manual sync ongoing')
                        setTimeout(_.bind(self.autoSyncPricelist, self), 10000); // Check every 10 seconds
                        return false;
                    }
                }

                async function _update(records){
                    if(records <= 0){
                        return Promise.resolve(true);
                    }
                    let pricelist_by_id = {};
                    _.each(self.env.pos.pricelists, function (pricelist) {
                        pricelist_by_id[pricelist.id] = pricelist;
                    });
                    _.each(records, function (item) {
                        let pricelist = pricelist_by_id[item.pricelist_id[0]];
                        item.display_name = item.name;
                        item.active = true;
                        pricelist.items.push(item);
                        item.base_pricelist = pricelist_by_id[item.base_pricelist_id[0]];
                    });

                    let pricelist = pricelist_by_id[self.env.pos.config.pricelist_id[0]]
                    pricelist.items = [...new Map(pricelist.items.map(v => [v.id, v])).values()]
                    self.env.pos.save_results('product.pricelist.item', records);
                    self.clear_cache_product_price();

                    let order = self.env.pos.get_order();
                    let active_pricelist = self.env.pos._get_active_pricelist();
                    if (order && active_pricelist) {
                        order.set_pricelist(active_pricelist);
                    }

                    posbus.trigger('reload-products-screen');
                    await new Promise(res=>setTimeout(res,500)); // 0.5 second to update variable
                    return Promise.resolve(true);
                }

                let monitor_vals = {
                    id: 'pricelist_' + moment().format('MMDDHHmmss'),
                    type: 'pricelist', sequence: moment().format('MMDDHHmmss'),
                    date: moment().format('YYYY-MM-DD HH:mm:ss'),
                }

                // TODO: Search product.pricelist.item within limit, if the result count is more than limit do it with pagination
                let last_write_date = self.env.pos.db.write_date_by_model['product.pricelist.item'];
                try {
                    let start_execute_time = Date.now();
                    let limit = 100;
                    let vals = { 'product.pricelist.item': last_write_date, 'limit': limit, 'offset': 0 };
                    vals['pricelist_id'] = self.env.pos.config.pricelist_id[0];
                    let res = await self.env.pos.search_model_datas('auto_sync_pricelist', vals);
                    if (res) {  

                        if(self.env.pos.config.is_monitor_auto_sync){
                            monitor_vals.total_unsync_data = res['product_pricelist_item_count'];
                            monitor_vals.total_synced_data = res['product_pricelist_item'].length;
                            monitor_vals.duration = Date.now() - start_execute_time;
                            self.trigger_update_monitor(monitor_vals);
                        }

                        await _update(res['product_pricelist_item']);
                        let count = res['product_pricelist_item_count'];
                        let pages = (( count - (count%limit) ) / limit) + (count%limit > 0?1:0);
                        for (let page = 1; page < pages; page++){
                            let next_res_start_execute_time = Date.now();
                            vals['offset'] = limit * page;
                            let next_res = await self.env.pos.search_model_datas('auto_sync_pricelist', vals);
                            if (!next_res) { // second attempt if error
                                next_res = await self.env.pos.search_model_datas('auto_sync_pricelist', vals);
                            }
                            if(next_res){
                                await _update(next_res['product_pricelist_item']);

                                if(self.env.pos.config.is_monitor_auto_sync){
                                    monitor_vals.total_unsync_data = res['product_pricelist_item_count'];
                                    monitor_vals.total_synced_data = next_res['product_pricelist_item'].length;
                                    monitor_vals.duration = Date.now() - next_res_start_execute_time;
                                    self.trigger_update_monitor(monitor_vals);
                                }

                            }
                        }
                    }
                } catch(err) {
                    timeout = 7000;
                    console.error('[autoSyncPricelist] ~ Error', err.message)
                }
                setTimeout(_.bind(self.autoSyncPricelist, self), timeout); // Check every 3 seconds
            }


            async autoSyncPromotion() {
                const self = this; 
                let timeout = 3000;
                if(!self.env.pos.config.is_auto_sync_promotion){
                    return false;
                }
                let process_sync_model = self.env.pos.process_sync_model;
                if(process_sync_model){
                    if(process_sync_model['product.product'] || process_sync_model['pos.promotion'] || process_sync_model['pos.promotion']){
                        console.warn('[autoSyncPromotion] ~ Skipped -> There is manual sync ongoing')
                        setTimeout(_.bind(self.autoSyncPromotion, self), 10000); // Check every 10 seconds
                        return false;
                    }
                }

                async function _update(results){
                    if(results['pos.promotion'].length <= 0){
                        return Promise.resolve(true);
                    }

                    if(results['pos.promotion'].length){
                        self.env.pos.sync_models = true;
                        let promotions = results['pos.promotion']; 
                        self.env.pos.indexed_db.write('pos.promotion', promotions);
                        self.env.pos.save_results('pos.promotion', promotions);
                        self.env.pos.db.set_last_write_date_by_model('pos.promotion', promotions);

                        // TODO: update data when deleted
                        let deleted_record_ids = promotions.filter((o)=>o.active == false && o.state == 'disable').map((o)=>o.id);
                        if(deleted_record_ids.length){
                            if(self.env.pos.promotions){
                                self.env.pos.promotions = self.env.pos.promotions.filter((p)=>deleted_record_ids.includes(p.id)==false);
                            }
                            if(self.env.pos.promotion_by_id){
                                for (let deleted_id of deleted_record_ids) {
                                    delete self.env.pos.promotion_by_id[deleted_id]; 
                                }
                            }
                            if(self.env.pos.promotion_ids){
                                self.env.pos.promotion_ids = self.env.pos.promotion_ids.filter((id)=>deleted_record_ids.includes(id)==false);
                            }
                            self.env.pos.promotion_models['pos.promotion'] = self.env.pos.promotion_ids;
                        }

                        self.env.pos.sync_models = false;
                    }

                    if(results['pos.promotion.discount.order'].length){
                        self.env.pos.sync_models = true;
                        var discounts = results['pos.promotion.discount.order'];
                        self.env.pos.indexed_db.write('pos.promotion.discount.order', discounts);
                        self.env.pos.save_results('pos.promotion.discount.order', discounts);
                        self.env.pos.sync_models = false;
                    }

                    if(results['pos.promotion.discount.category'].length){
                        self.env.pos.sync_models = true;
                        var discounts_category = results['pos.promotion.discount.category'];
                        self.env.pos.indexed_db.write('pos.promotion.discount.category', discounts_category);
                        self.env.pos.save_results('pos.promotion.discount.category', discounts_category);
                        self.env.pos.sync_models = false;
                    }

                    if(results['pos.promotion.discount.quantity'].length){
                        self.env.pos.sync_models = true;
                        var discounts_quantity = results['pos.promotion.discount.quantity'];
                        self.env.pos.indexed_db.write('pos.promotion.discount.quantity', discounts_quantity);
                        self.env.pos.save_results('pos.promotion.discount.quantity', discounts_quantity);
                        self.env.pos.sync_models = false;
                    }

                    if(results['pos.promotion.gift.condition'].length){
                        self.env.pos.sync_models = true;
                        var gift_conditions = results['pos.promotion.gift.condition'];
                        self.env.pos.indexed_db.write('pos.promotion.gift.condition', gift_conditions);
                        self.env.pos.save_results('pos.promotion.gift.condition', gift_conditions);
                        self.env.pos.sync_models = false;
                    }

                    if(results['pos.promotion.gift.free'].length){
                        self.env.pos.sync_models = true;
                        var gifts_free = results['pos.promotion.gift.free'];
                        self.env.pos.indexed_db.write('pos.promotion.gift.free', gifts_free);
                        self.env.pos.save_results('pos.promotion.gift.free', gifts_free);
                        self.env.pos.sync_models = false;
                    }

                    if(results['pos.promotion.discount.condition'].length){
                        self.env.pos.sync_models = true;
                        var discount_conditions = results['pos.promotion.discount.condition'];
                        self.env.pos.indexed_db.write('pos.promotion.discount.condition', discount_conditions);
                        self.env.pos.save_results('pos.promotion.discount.condition', discount_conditions);
                        self.env.pos.sync_models = false;
                    }

                    if(results['pos.promotion.discount.apply'].length){
                        self.env.pos.sync_models = true;
                        var discounts_apply = results['pos.promotion.discount.apply'];
                        self.env.pos.indexed_db.write('pos.promotion.discount.apply', discounts_apply);
                        self.env.pos.save_results('pos.promotion.discount.apply', discounts_apply);
                        self.env.pos.sync_models = false;
                    }

                    if(results['pos.promotion.price'].length){
                        self.env.pos.sync_models = true;
                        var prices = results['pos.promotion.price'];
                        self.env.pos.indexed_db.write('pos.promotion.price', prices);
                        self.env.pos.save_results('pos.promotion.price', prices);
                        self.env.pos.sync_models = false;
                    }

                    if(results['pos.promotion.selected.brand'].length){
                        self.env.pos.sync_models = true;
                        var promotion_lines = results['pos.promotion.selected.brand'];
                        self.env.pos.indexed_db.write('pos.promotion.selected.brand', promotion_lines);
                        self.env.pos.save_results('pos.promotion.selected.brand', promotion_lines);
                        self.env.pos.sync_models = false;
                    }

                    if(results['pos.promotion.tebus.murah.selected.brand'].length){
                        self.env.pos.sync_models = true;
                        var promotion_lines = results['pos.promotion.tebus.murah.selected.brand'];
                        self.env.pos.indexed_db.write('pos.promotion.tebus.murah.selected.brand', promotion_lines);
                        self.env.pos.save_results('pos.promotion.tebus.murah.selected.brand', promotion_lines);
                        self.env.pos.sync_models = false;
                    }

                    if(results['pos.promotion.special.category'].length){
                        self.env.pos.sync_models = true;
                        var promotion_lines = results['pos.promotion.special.category'];
                        self.env.pos.indexed_db.write('pos.promotion.special.category', promotion_lines);
                        self.env.pos.save_results('pos.promotion.special.category', promotion_lines);
                        self.env.pos.sync_models = false;
                    }

                    if(results['pos.promotion.specific.product'].length){
                        self.env.pos.sync_models = true;
                        var promotion_lines = results['pos.promotion.specific.product'];
                        self.env.pos.indexed_db.write('pos.promotion.specific.product', promotion_lines);
                        self.env.pos.save_results('pos.promotion.specific.product', promotion_lines);
                        self.env.pos.sync_models = false;
                    }

                    if(results['pos.promotion.multi.buy'].length){
                        self.env.pos.sync_models = true;
                        var multi_buy = results['pos.promotion.multi.buy'];
                        self.env.pos.indexed_db.write('pos.promotion.multi.buy', multi_buy);
                        self.env.pos.save_results('pos.promotion.multi.buy', multi_buy);
                        self.env.pos.sync_models = false;
                    }

                    if(results['pos.promotion.tebus.murah'].length){
                        self.env.pos.sync_models = true;
                        var tebus_murah = results['pos.promotion.tebus.murah'];
                        self.env.pos.indexed_db.write('pos.promotion.tebus.murah', tebus_murah);
                        self.env.pos.save_results('pos.promotion.tebus.murah', tebus_murah);
                        self.env.pos.sync_models = false;
                    }

                    if(results['pos.promotion.multilevel.condition'].length){
                        self.env.pos.sync_models = true;
                        var multilevel_condition = results['pos.promotion.multilevel.condition'];
                        self.env.pos.indexed_db.write('pos.promotion.multilevel.condition', multilevel_condition);
                        self.env.pos.save_results('pos.promotion.multilevel.condition', multilevel_condition);
                        self.env.pos.sync_models = false;
                    }

                    if(results['pos.promotion.multilevel.gift'].length){
                        self.env.pos.sync_models = true;
                        var multilevel_gift = results['pos.promotion.multilevel.gift'];
                        self.env.pos.indexed_db.write('pos.promotion.multilevel.gift', multilevel_gift);
                        self.env.pos.save_results('pos.promotion.multilevel.gift', multilevel_gift);
                        self.env.pos.sync_models = false;
                    }
                   
                    return Promise.resolve(true);
                }

                let monitor_vals = {
                    id: 'promotion_' + moment().format('MMDDHHmmss'),
                    type: 'promotion', sequence: moment().format('MMDDHHmmss'),
                    date: moment().format('YYYY-MM-DD HH:mm:ss'),
                }

                // TODO: Search pos.promotion within limit, if the result count is more than limit do it with pagination
                let last_write_date = self.env.pos.db.write_date_by_model['pos.promotion'];
                try {
                    let start_execute_time = Date.now();
                    let limit = 100;
                    let vals = { 'pos.promotion': last_write_date, 'limit': limit, 'offset': 0 };
                    let res = await self.env.pos.search_model_datas('auto_sync_promotion', vals);
                    if (res) {  
                        
                        if(self.env.pos.config.is_monitor_auto_sync){
                            monitor_vals.total_unsync_data = res['pos_promotion_count'];
                            monitor_vals.total_synced_data = res['pos.promotion'].length;
                            monitor_vals.duration = Date.now() - start_execute_time;
                            self.trigger_update_monitor(monitor_vals);
                        }

                        await _update(res);
                        let count = res['pos_promotion_count'];
                        let pages = (( count - (count%limit) ) / limit) + (count%limit > 0?1:0);
                        for (let page = 1; page < pages; page++){
                            let next_res_start_execute_time = Date.now();
                            vals['offset'] = limit * page;
                            let next_res = await self.env.pos.search_model_datas('auto_sync_promotion', vals);
                            if (!next_res) { // second attempt if error
                                next_res = await self.env.pos.search_model_datas('auto_sync_promotion', vals);
                            }
                            if(next_res){
                                await _update(next_res);

                                if(self.env.pos.config.is_monitor_auto_sync){
                                    monitor_vals.total_unsync_data = res['pos_promotion_count'];
                                    monitor_vals.total_synced_data = next_res['pos.promotion'].length;
                                    monitor_vals.duration = Date.now() - next_res_start_execute_time;
                                    self.trigger_update_monitor(monitor_vals);
                                }
                            }
                        }
                    }
                } catch(err) {
                    timeout = 7000;
                    console.error('[autoSyncPromotion] ~ Error', err.message)
                }
                setTimeout(_.bind(self.autoSyncPromotion, self), timeout); // Check every 3 seconds
            }

            async autoSyncCoupon() {
                const self = this; 
                let timeout = 3000;
                if(!self.env.pos.config.is_auto_sync_coupon){
                    return false;
                }
                let process_sync_model = self.env.pos.process_sync_model;
                if(process_sync_model){
                    if(process_sync_model['product.product'] || process_sync_model['pos.coupon']){
                        console.warn('[autoSyncCoupon] ~ Skipped -> There is manual sync ongoing')
                        setTimeout(_.bind(self.autoSyncCoupon, self), 10000); // Check every 10 seconds
                        return false;
                    }
                }

                async function _update(coupons){
                    if(coupons <= 0){
                        return Promise.resolve(true);
                    }
                    let current_date = moment(moment().utc().format('YYYY-MM-DD HH:mm:ss'), 'YYYY-MM-DD HH:mm:ss');
                    coupons = coupons.filter(p => {
                        let start_date = moment(p.start_date, 'YYYY-MM-DD HH:mm:ss');
                        let end_date = moment(p.end_date, 'YYYY-MM-DD HH:mm:ss');
                        if(current_date.isAfter(start_date) && current_date.isBefore(end_date)){
                            return true;
                        }
                        return false;
                    });
                    self.env.pos.db.save_pos_coupon(coupons);
                    self.env.pos.db.set_last_write_date_by_model('pos.coupon', coupons);
                    return Promise.resolve(true);
                }

                let monitor_vals = {
                    id: 'coupon_' + moment().format('MMDDHHmmss'),
                    type: 'coupon', sequence: moment().format('MMDDHHmmss'),
                    date: moment().format('YYYY-MM-DD HH:mm:ss'),
                }

                // TODO: Search pos.coupon within limit, if the result count is more than limit do it with pagination
                let last_write_date = self.env.pos.db.write_date_by_model['pos.coupon'];
                try {
                    let start_execute_time = Date.now();
                    let limit = 100;
                    let vals = { 'pos.coupon': last_write_date, 'limit': limit, 'offset': 0 };
                    let res = await self.env.pos.search_model_datas('auto_sync_coupon', vals);
                    if (res) {  

                        if(self.env.pos.config.is_monitor_auto_sync){
                            monitor_vals.total_unsync_data = res['pos_coupon_count'];
                            monitor_vals.total_synced_data = res['pos_coupon'].length;
                            monitor_vals.duration = Date.now() - start_execute_time;
                            self.trigger_update_monitor(monitor_vals);
                        }

                        await _update(res['pos_coupon']);
                        let count = res['pos_coupon_count'];
                        let pages = (( count - (count%limit) ) / limit) + (count%limit > 0?1:0);
                        for (let page = 1; page < pages; page++){
                            let next_res_start_execute_time = Date.now();
                            vals['offset'] = limit * page;
                            let next_res = await self.env.pos.search_model_datas('auto_sync_coupon', vals);
                            if (!next_res) { // second attempt if error
                                next_res = await self.env.pos.search_model_datas('auto_sync_coupon', vals);
                            }
                            if(next_res){
                                await _update(next_res['pos_coupon']);

                                if(self.env.pos.config.is_monitor_auto_sync){
                                    monitor_vals.total_unsync_data = res['pos_coupon_count'];
                                    monitor_vals.total_synced_data = next_res['pos_coupon'].length;
                                    monitor_vals.duration = Date.now() - next_res_start_execute_time;
                                    self.trigger_update_monitor(monitor_vals);
                                }

                            }
                        }
                    }
                } catch(err) {
                    timeout = 7000;
                    console.error('[autoSyncCoupon] ~ Error', err.message)
                }
                setTimeout(_.bind(self.autoSyncCoupon, self), timeout); // Check every 3 seconds
            }

            trigger_update_monitor(value) {
                if(value.total_synced_data != 0){
                    posbus.trigger('update-monitor-auto-sync', value);
                }
            }

            async onClick() {
                this.env.pos._turn_on_save_order_to_server();
                
                super.onClick();
                const serverOrigin = this.env.pos.session.origin;
                const connection = new Session(void 0, serverOrigin, {
                    use_cors: true
                });
                const pingServer = await connection.rpc('/pos/passing/login', {}).then(function (result) {
                    return result
                }, function (error) {
                    return false;
                })
                if (!pingServer) {
                    await this.showPopup('OfflineErrorPopup', {
                        title: this.env._t('Offline'),
                        body: this.env._t('Your Internet or Hashmicro Server Offline'),
                    });
                    return true;
                } else {
                    this.env.pos.alert_message({
                        title: this.env._t('Hashmicro Server Online'),
                        body: this.env._t('Server still working online mode'),
                        timer: 3000,
                    })
                }
            }
        }
    Registries.Component.extend(SyncNotification, RetailSyncNotification);

    return RetailSyncNotification;
});
