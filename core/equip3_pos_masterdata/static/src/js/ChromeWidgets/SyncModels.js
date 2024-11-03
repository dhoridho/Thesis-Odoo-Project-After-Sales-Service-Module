odoo.define('equip3_pos_masterdata.SyncModels', function (require) {
    'use strict';

    const models = require('point_of_sale.models');
    const PosProductTemplate = require('equip3_pos_masterdata.PosProductTemplate');
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');
    const time = require('web.time');
    const {useState} = owl;

    class SyncModels extends PosComponent {
        constructor() {
            super(...arguments);
            this.env.pos.process_sync_model = {
                'stock.quant': false
            }

            this.sync_state = useState({ 
                product: '',
                partner: '',
                pricelist: '',
                lots: '',
                vouchers: '',
                pos_orders:'',
                promotions: '',
                invoices: '',
                coupons: '',
            });
            this.warning_message = useState({ state: 'hidden' });
        }

        _sync_partner_label(){
            return 'Partners';
        }

        _warning_message1(){
            return this.env._t('Cannot close, There are still process on going');
        }
        _warning_message2(){
            return this.env._t('Cannot Sync All, There are still process on going');
        }

        close_warning_message(ev){
            $(ev.target).addClass('oe_hidden');
        }

        is_show_invoices(){
            if(this.env.pos.config.management_invoice){
                return true;
            }
            return false;
        }

        is_show_pos_orders(){
            if(this.env.pos.config.pos_orders_management){
                return true;
            }
            return false;
        }
        

        async close(ev) {
            let $popup = $(ev.target).closest('.popup');
            let in_process = false;
            for(let state in this.sync_state){
                if( this.sync_state[state] == 'connecting' ){
                    in_process = true;
                    break;
                }
            }
            if(in_process){
                $popup.find('.sync-models-list-warning').text(this._warning_message1());
                $popup.find('.sync-models-list-warning').removeClass('oe_hidden');
            }else{
                this.trigger('close-popup');
            }
        }

        async sync(type){
            if(type == 'product'){
                this.syncProduct();
            }
            if(type == 'partner'){
                this.syncPartner();
            }
            if(type == 'pricelist'){
                this.syncPricelist();
            }
            if(type == 'lots'){
                this.syncLotsSerialNumbers();
            }
            if(type == 'vouchers'){
                this.syncVouchers();
            }
            if(type == 'pos_orders'){
                this.syncPOSOrders();
            }
            if(type == 'promotions'){
                this.syncPromotions();
            }
            if(type == 'invoices'){
                this.syncInvoices();
            }
            if(type == 'coupons'){
                this.syncCoupons();
            }

        }

        async syncAll(ev) { 
            let $btn = $(ev.target);
            let $popup = $btn.closest('.popup');
            if(!$btn.hasClass('loading')){

                let in_process = false;
                for(let state in this.sync_state){
                    if( this.sync_state[state] == 'connecting' ){
                        in_process = true;
                        break;
                    }
                }
                if(in_process){
                    if(!$btn.hasClass('sync-all-loading')){
                        $popup.find('.sync-models-list-warning').text(this._warning_message2());
                        $popup.find('.sync-models-list-warning').removeClass('oe_hidden');
                    }
                    return;
                }

                $popup.find('.sync-models-list-warning').addClass('oe_hidden');

                $btn.addClass('loading');
                $popup.addClass('sync-all-loading');

                await this.syncProduct();
                await this.syncPartner();
                await this.syncPricelist();
                await this.syncLotsSerialNumbers();
                await this.syncVouchers();
                await this.syncCoupons();
                await this.syncPromotions();
                await this.syncPOSOrders();
                await this.syncInvoices();

                this.clear_cache_product_price();

                $btn.removeClass('loading');
                $popup.removeClass('sync-all-loading');
            }

        }

        async syncCoupons(){
            // TODO: sync pos.coupon
            let self = this;
            if(self.sync_state.coupons == 'connecting'){
                return;
            }
            let last_write_date = self.env.pos.db.write_date_by_model['pos.coupon'];
            let vals = {};
            if(last_write_date){
                vals['last_write_date'] = last_write_date;
            }
            console.log('[syncCoupons] ~ vals: ', vals)

            let args = [[], vals];
            self.env.pos.process_sync_model['pos.coupon'] = true;
            self.sync_state.coupons = 'connecting';
            let result = await self.rpc({
                model: 'pos.cache.database',
                method: 'sync_pos_coupon', 
                args: args
            }, {
                shadow: true,
                timeout: 1200000 // 20 minutes
            }).then(function (response) {
                return response;
            }, function (error) {
                if (error && error.message && error.message.code == -32098) {
                    console.error('[syncCoupons] ~ Server Offline')
                } else {
                    console.error('[syncCoupons] ~ Error 403')
                }
                self.env.pos.process_sync_model['pos.coupon'] = false;
                self.sync_state.coupons = 'error';
                return null;
            })
            if (result != null) {
                let coupons = result['pos.coupon'];
                console.log('[syncCoupons] ~ Results: pos.coupon: ' + coupons.length);
                if(coupons.length){
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
                }
            }

            self.env.pos.process_sync_model['pos.coupon'] = false;
            self.sync_state.coupons = 'done';
        }
        
        async syncInvoices(){
            let self = this
            if(!self.env.pos.config.management_invoice){
                return false;
            }
            await this.env.pos.syncInvoices(self);

            //TODO: Remove unused data
            if(self.env.pos.db.invoices){
                if (self.sync_state.invoices != 'error'){
                    self.sync_state.invoices == 'connecting';
                }
                let type = this.env.pos.config.load_invoices_type;
                let allowed_date = moment().utc().format('YYYY-MM-DD 00:00:00');
                if (type == 'last_3_days'){
                    allowed_date = moment().utc().subtract(3, 'day').format('YYYY-MM-DD 00:00:00');
                }
                if (type == 'last_7_days'){
                    allowed_date = moment().utc().subtract(7, 'day').format('YYYY-MM-DD 00:00:00');
                }
                if (type == 'last_1_month'){
                    allowed_date = moment().utc().subtract(1, 'months').format('YYYY-MM-DD 00:00:00');
                }
                if (type == 'last_1_year'){
                    allowed_date = moment().utc().subtract(1, 'year').format('YYYY-MM-DD 00:00:00');
                }

                const makeDate = str => {
                    const [_, yyyy, mm, dd, hh, min, ss] = str.match(/(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})/);
                    return new Date(yyyy, mm - 1, dd, hh, min, ss)
                };
                let latest_invoice = JSON.parse(JSON.stringify(self.env.pos.db.invoices));
                latest_invoice.sort((a, b) => makeDate(b.write_date) - makeDate(a.write_date));
                latest_invoice = latest_invoice[0];

                let unlink_invoice = self.env.pos.db.invoices.filter(o => {
                    if(!o.create_date){return true}
                    if(o.id == latest_invoice.id){ return false } // dont remove lastest updated invoice id
                    if(o.create_date){
                        return moment(o.create_date).isSameOrBefore(allowed_date);
                    }
                    return false;
                });
                let unlink_invoice_ids = unlink_invoice.map(o=>o.id);

                let latest_invoice_line = JSON.parse(JSON.stringify(self.env.pos.db.invoices_lines));
                latest_invoice_line.sort((a, b) => makeDate(b.write_date) - makeDate(a.write_date));
                latest_invoice_line = latest_invoice_line[0];

                let unlink_invoice_line = self.env.pos.db.invoices_lines.filter(o => {
                    if(o.id == latest_invoice_line.id){ return false } // dont remove lastest updated invoice line id
                    if(unlink_invoice_ids.includes(o.move_id[0])){
                        return true
                    }
                    return false;
                });

                console.log('[syncInvoices] ~ Start removing account.move in IndexedDB', unlink_invoice);
                self.env.pos.indexed_db.unlink_datas('account.move', unlink_invoice);
                console.log('[syncInvoices] ~ Finish removing account.move in IndexedDB');

                console.log('[syncInvoices] ~ Start removing account.move.line in IndexedDB', unlink_invoice_line);
                self.env.pos.indexed_db.unlink_datas('account.move.line', unlink_invoice_line);
                console.log('[syncInvoices] ~ Finish removing account.move.line in IndexedDB');

                if (self.sync_state.invoices != 'error'){
                    self.sync_state.invoices == 'done';
                }
            }
        }

        async syncPOSOrders(){
            let self = this
            if(!self.env.pos.config.pos_orders_management){
                return false;
            }
            // TODO: sync pos.order and pos.order.line
            await this.env.pos.syncPOSOrders(self);

            //TODO: Remove unused data
            if(self.env.pos.db.pos_all_orders){
                if (self.sync_state.invoices != 'error'){
                    self.sync_state.invoices == 'connecting';
                }
                let type = this.env.pos.config.filter_load_pos_order;
                let allowed_date = moment().utc().format('YYYY-MM-DD 00:00:00');
                if (type == 'last_3_days'){
                    allowed_date = moment().utc().subtract(3, 'day').format('YYYY-MM-DD 00:00:00');
                }
                if (type == 'last_7_days'){
                    allowed_date = moment().utc().subtract(7, 'day').format('YYYY-MM-DD 00:00:00');
                }
                if (type == 'last_1_month'){
                    allowed_date = moment().utc().subtract(1, 'months').format('YYYY-MM-DD 00:00:00');
                }
                if (type == 'last_1_year'){
                    allowed_date = moment().utc().subtract(1, 'year').format('YYYY-MM-DD 00:00:00');
                }

                const makeDate = str => {
                    const [_, yyyy, mm, dd, hh, min, ss] = str.match(/(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})/);
                    return new Date(yyyy, mm - 1, dd, hh, min, ss)
                };
                let latest_order = JSON.parse(JSON.stringify(self.env.pos.db.pos_all_orders));
                latest_order.sort((a, b) => makeDate(b.write_date) - makeDate(a.write_date));
                latest_order = latest_order[0];

                let unlink_orders = self.env.pos.db.pos_all_orders.filter(o => {
                    if(!o.create_date){return true}
                    if(o.id == latest_order.id){ return false } // dont remove lastest updated pos.order id
                    if(o.create_date){
                        return moment(o.create_date).isSameOrBefore(allowed_date);
                    }
                    return false;
                });
                let unlink_order_ids = unlink_orders.map(o=>o.id);
                
                let latest_order_line = JSON.parse(JSON.stringify(self.env.pos.db.pos_all_order_lines));
                latest_order_line.sort((a, b) => makeDate(b.write_date) - makeDate(a.write_date));
                latest_order_line = latest_order_line[0];

                let unlink_order_lines = self.env.pos.db.pos_all_order_lines.filter(o => {
                    if(o.id == latest_order_line.id){ return false } // dont remove lastest updated pos.order.line id
                    if(unlink_order_ids.includes(o.order_id[0])){
                        return true
                    }
                    return false;
                });

                console.log('[syncPOSOrders] ~ Start removing pos.order in IndexedDB', unlink_orders);
                self.env.pos.indexed_db.unlink_datas('pos.order', unlink_orders);
                console.log('[syncPOSOrders] ~ Finish removing pos.order in IndexedDB');

                console.log('[syncPOSOrders] ~ Start removing pos.order.line in IndexedDB', unlink_order_lines);
                self.env.pos.indexed_db.unlink_datas('pos.order.line', unlink_order_lines);
                console.log('[syncPOSOrders] ~ Finish removing pos.order.line in IndexedDB');
                
                if (self.sync_state.invoices != 'error'){
                    self.sync_state.invoices == 'done';
                }
            }
        }

        async syncProduct(){
            // TODO: sync product.template and product.product
            let self = this;
            if(self.sync_state.product == 'connecting'){
                return;
            }

            let vals = {
                'pos_config_id': self.env.pos.config.id,
                'product.product': self.env.pos.db.write_date_by_model['product.product'],
                'product.template': self.env.pos.db.write_date_by_model['product.template'],
                'product.template.barcode': self.env.pos.db.write_date_by_model['product.template.barcode'],
                'stock.quant': self.env.pos.db.write_date_by_model['stock.quant'],
                'product.brand': self.env.pos.db.write_date_by_model['product.brand'],
            }
            if(typeof vals['product.template'] == 'undefined'){
                vals['product.template'] = vals['product.product']
            }
            console.log('[syncProduct] ~ Get Last Updated: product.product: ' + vals['product.product'] +  '  product.template: ' + vals['product.template']+  '  product.brand: ' + vals['product.brand'])

            let args = [[], vals];

            self.env.pos.process_sync_model['product.product'] = true;
            self.sync_state.product = 'connecting';
            let result = await self.rpc({
                model: 'pos.cache.database',
                method: 'sync_pos_product', 
                args: args
            }, {
                shadow: true,
                timeout: 1200000 // 20 minutes
            }).then(function (response) {
                return response;
            }, function (error) {
                if (error && error.message && error.message.code == -32098) {
                    console.error('[syncProduct] ~ Server Offline')
                } else {
                    console.error('[syncProduct] ~ Error 403')
                }

                self.env.pos.process_sync_model['product.product'] = false;
                self.sync_state.product = 'error';
                return null;
            });

            if (result != null) {
                let product_templates = result['product_template'];
                let product_template_barcode = result['product_template_barcode'];
                let product_products = result['product_product'];
                let stock_quants = result['stock_quant'];
                let product_brands = result['product_brand'];
                console.log('[syncProduct] ~ Results: product.product: ' + product_products.length +  '  product.template: ' + product_templates.length+  '  product.brand: ' + product_brands.length+  '  stock.quant: ' + stock_quants.length);

                if(product_templates.length){
                    console.log('[syncProduct] ~ Updating variable product.template');
                    self.update_product_template(product_templates);
                    console.log('[syncProduct] ~ Finish variable product.template');
                }
                if(product_template_barcode.length){
                    console.log('[syncProduct] ~ Updating variable product.template.barcode');
                    self.update_product_template_barcode(product_template_barcode);
                    console.log('[syncProduct] ~ Finish variable product.template.barcode');
                }
                if(product_products.length){
                    console.log('[syncProduct] ~ Updating variable product.product');
                    self.update_product_product(product_products);
                    console.log('[syncProduct] ~ Finish variable product.product');
                }

                if(stock_quants.length){
                    console.log('[syncProduct] ~ Updating variable stock.quant');
                    self.update_stock_quant(stock_quants);
                    console.log('[syncProduct] ~ Finish variable stock.quant');
                }
                if(product_brands.length){
                    console.log('[syncProduct] ~ Updating variable product.brand');
                    self.update_product_brand(product_brands);
                    console.log('[syncProduct] ~ Finish variable product.brand');
                }
            }else{
                console.log('[syncProduct] ~ Results: product.product: 0  product.template: 0');
            }

            if(self.sync_state.product == 'error'){
                return false;
            }

            posbus.trigger('reload-products-screen');
            self.env.pos.process_sync_model['product.product'] = false;
            self.sync_state.product = 'done';

        }

        async syncPartner(){
            // TODO: sync res.partner
            var sync_models = this;
            await this.env.pos.syncPartner(sync_models)
        }

        async reloadPricelist(){
            console.log('{LoadModels} reload_pricelists')
            let self = this;
            let pricelists_model = _.filter(self.env.pos.models, function (model) {
                return model.pricelist;
            });
            if (pricelists_model) {
                let first_load = self.env.pos.load_server_data_by_model(pricelists_model[0]);
                self.env.pricelists_model = pricelists_model;
                return first_load.then(function () {
                    let second_load = self.env.pos.load_server_data_by_model(self.env.pricelists_model[1]);
                    return second_load.then(function () {
                        let order = self.env.pos.get_order();
                        let pricelist = self.env.pos._get_active_pricelist();
                        if (order && pricelist) {
                            order.set_pricelist(pricelist);
                        }
                        order.reset_client_use_coupon();
                    })
                })
            }
        }

        async syncPricelist(){
            // TODO: sync product.pricelist.item
            let self = this;
            if(self.sync_state.pricelist == 'connecting'){
                return;
            }
            let last_write_date = self.env.pos.db.write_date_by_model['product.pricelist.item']
            let vals = {
                'pricelist_id': self.env.pos.config.pricelist_id[0],
                'last_write_date': last_write_date,
            }
            console.log('[syncPricelist] ~ vals: ', vals)

            let args = [[], vals];
            self.env.pos.process_sync_model['product.pricelist.item'] = true;
            self.sync_state.pricelist = 'connecting';
            let result = await self.rpc({
                model: 'pos.cache.database',
                method: 'sync_pos_pricelist', 
                args: args
            }, {
                shadow: true,
                timeout: 1200000 // 20 minutes
            }).then(function (response) {
                return response;
            }, function (error) {
                if (error && error.message && error.message.code == -32098) {
                    console.error('[syncPricelist] ~ Server Offline')
                } else {
                    console.error('[syncPricelist] ~ Error 403')
                }
                self.env.pos.process_sync_model['product.pricelist.item'] = false;
                self.sync_state.pricelist = 'error';
                return null;
            })

            if (result != null) {
                let product_pricelist_items = result['product_pricelist_item'];
                console.log('[syncPricelist] ~ Results: product.pricelist.item: ' + product_pricelist_items.length);

                // TODO: remove deleted records
                let pricelist_item_ids = result['product_pricelist_item_ids'];
                if(pricelist_item_ids){
                    let deleted_ids = []
                    let current_item_ids = self.env.pos.default_pricelist.items.map((i)=>i.id);
                    for (let current_item_id of current_item_ids){
                        if(!pricelist_item_ids.includes(current_item_id)){
                            deleted_ids.push(current_item_id)
                        }
                    }
                    if (deleted_ids.length){
                        self.env.pos.indexed_db.unlink_data_by_ids('product.pricelist.item', deleted_ids);
                    }
                }

                if(product_pricelist_items){
                    console.log('[syncPricelist] ~ Updating variable product.pricelist.item'); 
                    let active_records = product_pricelist_items.filter(r => r['active'] == true);
                    if(active_records.length){
                        self.env.pos.indexed_db.write('product.pricelist.item', active_records);
                    }

                    let archived_records = product_pricelist_items.filter(r => r['active'] == false);
                    for (let i = 0; i < archived_records.length; i++) {
                        self.env.pos.indexed_db.unlink('product.pricelist.item', archived_records[i]);
                    }

                    self.env.pos.save_results('product.pricelist.item', product_pricelist_items);
                    await this.reloadPricelist()
                    console.log('[syncPricelist] ~ Finish variable product.pricelist.item');
                }
            }

            if(self.sync_state.pricelist == 'error'){
                return false;
            }

            this.clear_cache_product_price();

            posbus.trigger('reload-products-screen');
            self.sync_state.pricelist = 'done';
            self.env.pos.process_sync_model['product.pricelist.item'] = false;
        }

        async syncLotsSerialNumbers(){
            // TODO: sync stock.production.lot
            let self = this;
            if(self.sync_state.lots == 'connecting'){
                return;
            }
            let last_write_date = self.env.pos.db.write_date_by_model['stock.production.lot']
            let vals = { 
                'last_write_date': last_write_date,
            }

            console.log('[syncLotsSerialNumbers] ~ vals: ', vals)
             
            let args = [[], vals];
            self.sync_state.lots = 'connecting';
            let result = await self.rpc({
                model: 'pos.cache.database',
                method: 'sync_pos_lot_serial_number', 
                args: args
            }, {
                shadow: true,
                timeout: 1200000 // 20 minutes
            }).then(function (response) {
                return response;
            }, function (error) {
                if (error && error.message && error.message.code == -32098) {
                    console.error('[syncLotsSerialNumbers] ~ Server Offline')
                } else {
                    console.error('[syncLotsSerialNumbers] ~ Error 403')
                }
                self.sync_state.lots = 'error';
                return null;
            });

            if (result != null) {
                let stock_production_lots = result['stock_production_lot'];
                console.log('[syncPricelist] ~ Results: stock.production.lot: ' + stock_production_lots.length);

                if(stock_production_lots){
                    console.log('[syncLotsSerialNumbers] ~ Updating variable stock.production.lot'); 
                    let active_records = stock_production_lots.filter(r => r['active'] == true);
                    let archived_records = stock_production_lots.filter(r => r['active'] == false);

                    for (let i = 0; i < archived_records.length; i++) {
                        self.env.pos.indexed_db.unlink('stock.production.lot', archived_records[i]);
                    }

                    if(active_records.length){
                        let uniqueIds = [];
                        let lots = [...active_records, ...self.env.pos.lots];

                        self.env.pos.lots = [];
                        self.env.pos.lot_by_name = {};
                        self.env.pos.lot_by_id = {};
                        self.env.pos.lot_by_product_id = {};
                        for (let i = 0; i < lots.length; i++) {
                            let lot = lots[i];
                            if(!uniqueIds.includes(lot.id)){
                                uniqueIds.push(lot.id);
                                self.env.pos.lots.push(lot);

                                self.env.pos.lot_by_name[lot['name']] = lot;
                                self.env.pos.lot_by_id[lot['id']] = lot;
                                if (!self.env.pos.lot_by_product_id[lot.product_id[0]]) {
                                    self.env.pos.lot_by_product_id[lot.product_id[0]] = [lot];
                                } else {
                                    self.env.pos.lot_by_product_id[lot.product_id[0]].push(lot);
                                }
                            }
                        }

                        self.env.pos.indexed_db.write('stock.production.lot', active_records);
                    }

                    if(active_records.length > 0 || archived_records.length > 0){
                        self.env.pos.save_results('stock.production.lot', self.env.pos.lots);
                    }
                    console.log('[syncLotsSerialNumbers] ~ Finish variable stock.production.lot');
                }
            }

            if(self.sync_state.lots == 'error'){
                return false;
            }
            self.sync_state.lots = 'done';
        }

        async syncVouchers(){
            // TODO: sync pos.voucher
            let self = this;
            if(self.sync_state.vouchers == 'connecting'){
                return;
            }
            let last_write_date = self.env.pos.db.write_date_by_model['pos.voucher']
            let vals = { 
                'last_write_date': last_write_date,
            }
            console.log('[syncVouchers] ~ vals: ', vals)
             
            let args = [[], vals];
            self.sync_state.vouchers = 'connecting';
            let result = await self.rpc({
                model: 'pos.cache.database',
                method: 'sync_pos_voucher', 
                args: args
            }, {
                shadow: true,
                timeout: 1200000 // 20 minutes
            }).then(function (response) {
                return response;
            }, function (error) {
                if (error && error.message && error.message.code == -32098) {
                    console.error('[syncVouchers] ~ Server Offline')
                } else {
                    console.error('[syncVouchers] ~ Error 403')
                }
                self.sync_state.vouchers = 'error';
                return null;
            });

            if (result != null) {
                let vouchers = result['pos.voucher'];
                console.log('[syncPricelist] ~ Results: pos.voucher: ' + vouchers.length);
                if (!self.env.pos.vouchers){
                    self.env.pos.vouchers = [];
                }
                if (!self.env.pos.voucher_by_id){
                    self.env.pos.voucher_by_id = {};
                }
                if(vouchers){
                    console.log('[syncVouchers] ~ Updating variable pos.voucher'); 
                    let active_records = vouchers.filter(r => r['active'] == true);
                    let archived_records = vouchers.filter(r => r['active'] == false);
                    for (let i = 0; i < archived_records.length; i++) {
                        self.env.pos.indexed_db.unlink('pos.voucher', archived_records[i]);
                    }
                    if(active_records.length){
                        self.env.pos.indexed_db.write('pos.voucher', active_records);

                        self.vouchers = vouchers;
                        self.env.pos.vouchers = [...self.env.pos.vouchers, ...active_records];
                        for (let i = 0; i < active_records.length; i++) {
                            self.env.pos.voucher_by_id[active_records[i].id] = active_records[i];
                        }
                    }
                    self.env.pos.save_results('pos.voucher', vouchers);
                }
            }

            if(self.sync_state.vouchers == 'error'){
                return false;
            }
            self.sync_state.vouchers = 'done';
        }

        async syncPromotions(){
            let self = this;
            if(self.sync_state.promotions == 'connecting'){
                return;
            }
            let vals = {
                'pos_config_id': self.env.pos.config.id,
                'pos.promotion': self.env.pos.db.write_date_by_model['pos.promotion'],
                'promotion_ids': self.env.pos.promotion_ids,

            }
            console.log('[syncPromotions] ~ vals: ', vals)
             
            let args = [[], vals];

            self.env.pos.process_sync_model['pos.promotion'] = true;
            self.sync_state.promotions = 'connecting';
            let results = await self.rpc({
                model: 'pos.cache.database',
                method: 'sync_pos_promotion', 
                args: args
            }, {
                shadow: true,
                timeout: 1200000 // 20 minutes
            }).then(function (response) {
                return response;
            }, function (error) {
                if (error && error.message && error.message.code == -32098) {
                    console.error('[syncPromotions] ~ Server Offline')
                } else {
                    console.error('[syncPromotions] ~ Error 403')
                }
                self.env.pos.process_sync_model['pos.promotion'] = false;
                self.sync_state.promotions = 'error';
                return null;
            });
            
            if (results != null) {
                this.remove_deleted_promotion_and_childs(results);

                if(results['pos.promotion'].length){
                    self.env.pos.sync_models = true;
                    let promotions = results['pos.promotion']; 
                    self.env.pos.indexed_db.write('pos.promotion', promotions);
                    self.env.pos.save_results('pos.promotion', promotions);
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
            }

            self.env.pos.process_sync_model['pos.promotion'] = false;
            if(self.sync_state.promotions == 'error'){
                return false;
            }
            self.sync_state.promotions = 'done';
        }

        remove_deleted_promotion_and_childs(results){
            let self = this;
            let models = results.existing_ids_of_promotion_and_childs;
            if(!models){
                return false;
            }
            let promotion_models = self.env.pos.promotion_models;
            if(!promotion_models){
                return false;
            }
            for (let model in models){
                let existing_record_ids = models[model]; // in database
                let current_record_ids = promotion_models[model]; // in local browser
                let deleted_record_ids = [];
                if (existing_record_ids && current_record_ids) {
                    deleted_record_ids = current_record_ids.filter((id)=>existing_record_ids.includes(id)==false);
                }

                if(deleted_record_ids.length){
                    console.log('[syncPromotions] ~ Start removing ' + model + ' in IndexedDB', deleted_record_ids);
                    self.env.pos.indexed_db.unlink_data_by_ids(model, deleted_record_ids);

                    if (model == 'pos.promotion') {
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
                    if (model == 'pos.promotion.discount.order'){
                        if (self.env.pos.promotion_discount_order_by_id){
                            for (let deleted_id of deleted_record_ids) {
                                delete self.env.pos.promotion_discount_order_by_id[deleted_id]; 
                            }
                        }
                        if (self.env.pos.promotion_discount_order_by_promotion_id){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_discount_order_by_promotion_id,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.discount.category'){
                        if (self.env.pos.pos_disc_categ_new){
                            this.update_existing_record_by_object(
                                self.env.pos.pos_disc_categ_new,
                                existing_record_ids
                            )
                        }
                        // self.env.pos.promotion_by_category_id
                    }
                    if (model == 'pos.promotion.gift.condition'){
                        if (self.env.pos.promotion_gift_condition_by_promotion_id){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_gift_condition_by_promotion_id,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.gift.free'){
                        if (self.env.pos.promotion_gift_free_by_promotion_id){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_gift_free_by_promotion_id,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.discount.condition'){
                        if (self.env.pos.promotion_discount_condition_by_promotion_id){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_discount_condition_by_promotion_id,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.discount.apply'){
                        if (self.env.pos.promotion_discount_apply_by_promotion_id){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_discount_apply_by_promotion_id,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.price'){
                        if (self.env.pos.promotion_price_by_promotion_id){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_price_by_promotion_id,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.special.category'){
                        if (self.env.pos.promotion_special_category_by_promotion_id){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_special_category_by_promotion_id,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.selected.brand'){
                        if (self.env.pos.promotion_selected_brands){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_selected_brands,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.tebus.murah.selected.brand'){
                        if (self.env.pos.promotion_tebus_murah_selected_brands){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_tebus_murah_selected_brands,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.specific.product'){
                        if (self.env.pos.promotion_specific_product_by_promotion_id){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_specific_product_by_promotion_id,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.multi.buy'){
                        if (self.env.pos.multi_buy_by_promotion_id){
                            this.update_existing_record_by_object(
                                self.env.pos.multi_buy_by_promotion_id,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.tebus.murah'){
                        if (self.env.pos.promotion_tebus_murah_product_by_promotion_id){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_tebus_murah_product_by_promotion_id,
                                existing_record_ids
                            )
                        }
                    }
                    
                    if (model == 'pos.promotion.multilevel.condition'){
                        if (self.env.pos.promotion_multilevel_condition_by_promotion_id){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_multilevel_condition_by_promotion_id,
                                existing_record_ids
                            )
                        }
                    }
                    if (model == 'pos.promotion.multilevel.gift'){
                        if (self.env.pos.promotion_multilevel_gift_by_promotion_id){
                            this.update_existing_record_by_object(
                                self.env.pos.promotion_multilevel_gift_by_promotion_id,
                                existing_record_ids
                            )
                        }
                    }
                    console.log('[syncPromotions] ~ Finish removing ' + model + ' in IndexedDB');
                }
            }
        }

        update_existing_record_by_object(object, existing_record_ids){
            for (let object_id in object){
                object[object_id] = object[object_id].filter((o)=>existing_record_ids.includes(o.id)==true);
            }
        }

        update_product_template(records){
            const self = this;
            let active_records = records.filter(r => r['active'] == true);
            let archived_records = records.filter(r => r['active'] == false);

            for (let i = 0; i < archived_records.length; i++) {
                self.env.pos.indexed_db.unlink('product.template', archived_records[i]);
            }
            if(active_records.length){
                self.env.pos.get_model('product.template').loaded(self.env.pos, records);
                self.env.pos.indexed_db.write('product.template', active_records);
            }

            self.env.pos.db.add_templates(_.map(records, function (template) {
                template.categ = _.findWhere(self.product_categories, {'id': template.categ_id[0]});
                template.pos = self;
                return new PosProductTemplate.ProductTemplate({}, template);
            }));

            self.env.pos.save_results('product.template', records);
            return records;
        }

    
        update_product_template_barcode(records){
            const self = this;
            let active_records = records.filter(r => r['active'] == true);

            if(active_records.length){
                self.env.pos.product_template_barcode_model.loaded(self.env.pos, records);
                self.env.pos.indexed_db.write('product.template.barcode', active_records);
            }
            self.env.pos.save_results('product.template.barcode', records);
            return records;
        }


        update_stock_quant(records){
            const self = this;
            let active_records = records.filter(r => r['active'] == true);

            if(active_records.length){
                self.env.pos.stock_quant_model.loaded(self.env.pos, records);
                self.env.pos.indexed_db.write('stock.quant', active_records);
            }
            self.env.pos.save_results('stock.quant', records);
            self.env.pos.trigger('reload.quantity.available')
            return records;
        }

        update_product_brand(records){
            const self = this;
            let active_records = records.filter(r => r['active'] == true);

            if(active_records.length){
                self.env.pos.product_brand_model.loaded(self.env.pos, records);
                self.env.pos.indexed_db.write('product.brand', active_records);
            }
            self.env.pos.save_results('product.brand', records);
            return records;
        }

        update_product_product(records){
            const self = this;
            let active_records = records.filter(r => r['active'] == true);
            let archived_records = records.filter(r => r['active'] == false);

            for (let i = 0; i < archived_records.length; i++) {
                self.env.pos.indexed_db.unlink('product.product', archived_records[i]);
                self.env.pos.removeProductHasDeletedOutOfCart(archived_records[i].id);
            }
            if(active_records.length){
                self.env.pos.product_model.loaded(self.env.pos, records);
                self.env.pos.indexed_db.write('product.product', active_records);
            }

            self.env.pos.db.add_products(_.map(records, function (product) {
                product.categ = _.findWhere(self.product_categories, {'id': product.categ_id[0]});
                product.pos = self;
                return new models.Product({}, product);
            }));
            self.env.pos.save_results('product.product', records);
            return records;
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
            console.warn('[sync->clear_cache_product_price]: ', self.env.pos.db.cache_product_price);
        }

    }

    SyncModels.template = 'SyncModels';
    Registries.Component.add(SyncModels);
    return SyncModels;
});
