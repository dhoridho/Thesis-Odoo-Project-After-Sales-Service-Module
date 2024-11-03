"use strict";
odoo.define('equip3_pos_masterdata.order', function (require) {

    const models = require('point_of_sale.models');
    const core = require('web.core');
    const field_utils = require('web.field_utils');
    const _t = core._t;
    const MultiUnitWidget = require('equip3_pos_masterdata.multi_unit');
    const rpc = require('pos.rpc');
    const qweb = core.qweb;
    const PosComponent = require('point_of_sale.PosComponent');
    const utils = require('web.utils');
    const round_pr = utils.round_precision;
    const {posbus} = require('point_of_sale.utils');
    const round_di = utils.round_decimals;
    const {Gui} = require('point_of_sale.Gui');
    const NumberBuffer = require('point_of_sale.NumberBuffer');

    let _super_PosModel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        initialize: function (session, attributes) {
            _super_PosModel.initialize.apply(this, arguments);
            this.bind('change:selectedOrder', function (pos) {
                let order = pos.get_order();
                if (order) {
                    order.add_barcode('barcode'); // TODO: add barcode to html page
                }
            });
        }
    });

    let _super_Order = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize: function (attributes, options) {
            if(!this.fixed_creation_date){
                this.fixed_creation_date = moment().format('YYYY-MM-DD HH:mm:ss'); // local device
            }

            _super_Order.initialize.apply(this, arguments);

            let self = this;
            if (!this.note) {
                this.note = '';
            }
            if (!this.signature) {
                this.signature = '';
            }
            if (!this.lock) {
                this.lock = false;
            }
            if (!this.voucher_id) {
                this.voucher_id = false;
            }
            if (!this.voucher_amount) {
                this.voucher_amount = false;
            }
            if (!this.generate_voucher_id) {
                this.generate_voucher_id = false;
            }
            if (!this.is_use_pos_coupon ) {
                this.is_use_pos_coupon = false;
            }
            if (!this.pos_coupon_id ) {
                this.pos_coupon_id = false;
            }

            if(this.pricelist){
                this.currency_id = this.pricelist.currency_id[0];
                this.currency = this.pos.currency_by_id[this.currency_id];
            }
            if (!options.json) {
                if (this.pos.config.analytic_account_id) {
                    this.analytic_account_id = this.pos.config.analytic_account_id[0]
                }
                // let pos_config_currency_id = this.pos.config.currency_id[0];
                // let config_currency = this.pos.currency_by_id[pos_config_currency_id];
                // if (config_currency) {
                //     this.currency = config_currency;
                //     this.currency_id = this.pos.config.currency_id[0];
                // }
                this.status = 'Coming'
                let picking_type_id = this.pos.config.picking_type_id[0];
                this.set_picking_type(picking_type_id);
                this.plus_point = 0;
                this.redeem_point = 0;
            }
            this.bind('add remove', function (order) {
                self.pos.trigger('refresh.tickets', order)
            });
            this.orderlines.bind('change add remove', function (line) {
                self.pos.trigger('refresh.tickets')
            });
        },

        generate_unique_id: function () {
            function zero_pad(num,size){
                var s = ""+num;
                while (s.length < size) {
                    s = "0" + s;
                }
                return s;
            }

            let result = zero_pad(this.pos.pos_session.id,5);

            let cashier_code = false;
            if(!this.employee){
                this.employee = this.pos.get_cashier();
            }
            if (this.pos.users && this.employee && this.employee.user_id) {
                let user_cashier = this.pos.users.filter((c) => c.id==this.employee.user_id[0])
                if (user_cashier.length > 0){
                    cashier_code = user_cashier[0].cashier_code;
                }
            }
            if (cashier_code) {
                result += '-'+zero_pad(cashier_code,3)
            }

            result += '-'+ zero_pad(this.pos.pos_session.login_number,3);
            
            if(this.fixed_creation_date){
                let str_time = moment(this.fixed_creation_date, 'YYYY-MM-DD HH:mm:ss').format('HHmmss');
                result += '-'+ zero_pad(str_time,6)
            }
            
            result += '-'+ zero_pad(this.sequence_number,4);
            return result;
        },

        is_paid: function () {
            const isPaid = _super_Order.is_paid.apply(this, arguments);
            return isPaid
        },

        async ask_guest() {
            let {confirmed, payload: number} = await this.pos.chrome.showPopup('NumberPopup', {
                'title': _t('How many guests in this Table ?'),
                'startingValue': 0,
            });
            if (confirmed) {
                let value = Math.max(1, Number(number));
                if (value < 1) {
                    this.pos.set_table(null);
                    this.pos.alert_message({
                        title: _t('Alert'),
                        body: _t('Please input guest, and bigger than 1')
                    })
                } else {
                    this.guest_not_set = true
                    this.set_customer_count(value);
                }
            }
        },


        set_tip: async function (tip) {
            let tip_product = this.pos.db.get_product_by_id(this.pos.config.tip_product_id[0]);
            if (!tip_product) {
                let result = await this.pos.chrome.rpc({
                    model: 'product.product',
                    method: 'force_write',
                    args: [[this.pos.config.tip_product_id[0]], {
                        'available_in_pos': true,
                        'sale_ok': true,
                        'active': true,
                    }],
                    context: {}
                })
                if (result) {
                    await this.pos.syncProductsPartners();
                } else {
                    return this.pos.alert_message({
                        title: _t('Error'),
                        body: _t('Please check your internet or Server Offline Mode')
                    })
                }

            }
            _super_Order.set_tip.apply(this, arguments);
        },

        save_to_db: function () {
            _super_Order.save_to_db.apply(this, arguments);
            let selected_line = this.get_selected_orderline();
            if (selected_line) {
                this.pos.trigger('selected:line', selected_line)
            }
        },
        init_from_JSON: function (json) {
            // TODO: we removed line have product removed
            let lines = json.lines;
            let lines_without_product_removed = [];
            this.rounding_from_payment = 0
            for (let i = 0; i < lines.length; i++) {
                let line = lines[i];
                let product_id = line[2]['product_id'];
                let product = this.pos.db.get_product_by_id(product_id);
                if (product) {
                    lines_without_product_removed.push(line)
                }
            }
            json.lines = lines_without_product_removed;
            // ---------------------------------
            let res = _super_Order.init_from_JSON.apply(this, arguments);
            if (json.plus_point) {
                this.plus_point = json.plus_point;
            }
            if (json.redeem_point) {
                this.redeem_point = json.redeem_point;
            }
            if (json.booking_id) {
                this.booking_id = json.booking_id;
            }
            if (json.status) {
                this.status = json.status
            }
            if (json.date) {
                this.date = json.date;
            }
            if (json.name) {
                this.name = json.name;
            }
            if (json.email_invoice) {
                this.email_invoice = json.email_invoice;
            }
            if (json.email_invoice) {
                this.email_invoice = json.email_invoice;
            }
            if (json.delivery_date) {
                this.delivery_date = json.delivery_date;
            }
            if (json.delivery_address) {
                this.delivery_address = json.delivery_address;
            }
            if (json.delivery_phone) {
                this.delivery_phone = json.delivery_phone;
            }
            if (json.amount_debit) {
                this.amount_debit = json.amount_debit;
            }
            if (json.return_order_id) {
                this.return_order_id = json.return_order_id;
            }
            if (json.is_return) {
                this.is_return = json.is_return;
            }
            if (json.to_invoice) {
                this.to_invoice = json.to_invoice;
            }
            if (json.parent_id) {
                this.parent_id = json.parent_id;
            }
            if (json.payment_journal_id) {
                this.payment_journal_id = json.payment_journal_id;
            } else {
                this.payment_journal_id = this.pos.get_default_sale_journal();
            }
            if (json.ean13) {
                this.ean13 = json.ean13;
            }
            if (json.signature) {
                this.signature = json.signature
            }
            if (json.note) {
                this.note = json.note
            }
            if (json.lock) {
                this.lock = json.lock;
            } else {
                this.lock = false;
            }
            if (json.guest) {
                this.guest = json.guest;
            }
            if (json.guest_number) {
                this.guest_number = json.guest_number;
            }
            if (json.location_id) {
                let location = this.pos.stock_location_by_id[json.location_id];
                if (location) {
                    this.set_stock_location(location)
                } else {
                    let location = this.pos.get_source_stock_location();
                    this.set_stock_location(location)
                }
            } else {
                let location = this.pos.get_source_stock_location();
                if (location) {
                    this.set_stock_location(location);
                }
            }
            if (json.currency_id) {
                let currency = this.pos.currency_by_id[json.currency_id];
                this.currency = currency;
            }
            if (json.analytic_account_id) {
                this.analytic_account_id = json.analytic_account_id
            }
            if (json.shipping_id) {
                this.shipping_id = json.shipping_id
            }
            if (json.picking_type_id) {
                this.set_picking_type(json.picking_type_id)
            }
            if (json.guest_not_set) {
                this.guest_not_set = json.guest_not_set
            }

            if (json.sync_write_date) {
                this.sync_write_date = json.sync_write_date
            }
            if (json.sync_sequence_number) {
                this.sync_sequence_number = json.sync_sequence_number
            }
            if (json.fixed_creation_date) {
                this.fixed_creation_date = json.fixed_creation_date
            }
            if (json.client_use_voucher) {
                this.client_use_voucher = json.client_use_voucher
            }
            if (json.client_use_voucher_amount) {
                this.client_use_voucher_amount = json.client_use_voucher_amount
            }
            if (json.generate_voucher_id) {
                this.generate_voucher_id = json.generate_voucher_id
            }
            if (json.is_use_pos_coupon ) {
                this.is_use_pos_coupon  = json.is_use_pos_coupon
            }
            if (json.pos_coupon_id ) {
                this.pos_coupon_id  = json.pos_coupon_id
            }
            return res;
        },
        export_as_JSON: function () {
            let json = _super_Order.export_as_JSON.apply(this, arguments);
            if (this.promotion_amount) {
                json.promotion_amount = this.promotion_amount;
            }
            if (this.plus_point) {
                json.plus_point = this.plus_point;
            }
            if (this.redeem_point) {
                json.redeem_point = this.redeem_point;
            }
            if (this.booking_id) {
                json.booking_id = this.booking_id
            }
            if (this.status) {
                json.status = this.status
            } else {
                json.status = 'Coming'
            }
            if (this.email_invoice) {
                json.email_invoice = this.email_invoice;
                let client = this.get_client();
                if (client && client.email) {
                    json.email = client.email;
                }
            }
            if (this.delivery_date) {
                json.delivery_date = this.delivery_date;
            }
            if (this.delivery_address) {
                json.delivery_address = this.delivery_address;
            }
            if (this.delivery_phone) {
                json.delivery_phone = this.delivery_phone;
            }
            if (this.amount_debit) {
                json.amount_debit = this.amount_debit;
            }
            if (this.return_order_id) {
                json.return_order_id = this.return_order_id;
            }
            if (this.is_return) {
                json.is_return = this.is_return;
            }
            if (this.parent_id) {
                json.parent_id = this.parent_id;
            }
            if (this.payment_journal_id) {
                json.payment_journal_id = this.payment_journal_id;
            } else {
                this.payment_journal_id = this.pos.get_default_sale_journal();
            }
            if (this.note) {
                json.note = this.note;
            }
            if (this.signature) {
                json.signature = this.signature;
            }
            if (this.ean13) {
                json.ean13 = this.ean13;
                this.add_barcode('barcode')
            }
            if (!this.ean13 && this.uid) {
                let ean13_code = this.zero_pad('6', 4) + this.zero_pad(this.pos.pos_session.login_number, 4) + this.zero_pad(this.sequence_number, 4);
                let ean13 = ean13_code.split("");
                let ean13_array = [];
                for (let i = 0; i < ean13.length; i++) {
                    if (i < 12) {
                        ean13_array.push(ean13[i])
                    }
                }
                this.ean13 = ean13_code + this.generate_unique_ean13(ean13_array).toString();
                this.add_barcode('barcode')
            }
            if (this.lock) {
                json.lock = this.lock;
            } else {
                json.lock = false;
            }
            if (this.invoice_ref) {
                json.invoice_ref = this.invoice_ref
            }
            if (this.picking_ref) {
                json.picking_ref = this.picking_ref
            }
            if (this.guest) {
                json.guest = this.guest
            }
            if (this.guest_number) {
                json.guest_number = this.guest_number
            }
            if (this.location_id) {
                let stock_location_id = this.pos.config.stock_location_id;
                if (stock_location_id) {
                    let location = this.pos.stock_location_by_id[this.location_id];
                    if (location) {
                        json.location = location;
                        json.location_id = location.id;
                    }
                }
            }
            if (this.currency) {
                json.currency_id = this.currency.id
            }
            if (this.analytic_account_id) {
                json.analytic_account_id = this.analytic_account_id
            }
            if (this.shipping_id) {
                json.shipping_id = this.shipping_id
            }
            if (this.picking_type) {
                json.picking_type_id = this.picking_type.id;
            }
            if (this.guest_not_set) {
                json.guest_not_set = this.guest_not_set
            }
            if (this.state) {
                json.state = this.state
            }
            if (this.removed_user_id) {
                json.removed_user_id = this.removed_user_id
            }
            if (this.save_draft) {
                json.save_draft = this.save_draft
            }
            if (this.backend_id) {
                json.backend_id = this.backend_id
            }
            if (this.receiptBase64) {
                json.receiptBase64 = this.receiptBase64
            }
            if (this.rounding_from_payment) {
                json.rounding_from_payment = this.rounding_from_payment
            }

            if (this.sync_write_date) {
                json.sync_write_date = this.sync_write_date
            }
            if (this.sync_sequence_number) {
                json.sync_sequence_number = this.sync_sequence_number
            }
            if (this.fixed_creation_date) {
                json.fixed_creation_date = this.fixed_creation_date
            }
            if (this.client_use_voucher) {
                json.client_use_voucher = this.client_use_voucher
            }
            if (this.client_use_voucher_amount) {
                json.client_use_voucher_amount = this.client_use_voucher_amount
            }
            if (this.generate_voucher_id) {
                json.generate_voucher_id = this.generate_voucher_id
            }
            if (this.is_use_pos_coupon) {
                json.is_use_pos_coupon = this.is_use_pos_coupon
            }
            if (this.pos_coupon_id) {
                json.pos_coupon_id = this.pos_coupon_id
            }
            return json;
        },
        export_for_printing: function () {
            let receipt = _super_Order.export_for_printing.call(this);
            if (this.promotion_amount) {
                receipt.promotion_amount = this.promotion_amount;
            }
            receipt.plus_point = this.plus_point || 0;
            receipt.redeem_point = this.redeem_point || 0;
            let order = this.pos.get_order();
            if (!order) {
                return receipt
            }
            if (this.picking_type) {
                receipt['picking_type'] = this.picking_type;
            }
            if (this.location) {
                receipt['location'] = this.location;
            } else {
                let stock_location_id = this.pos.config.stock_location_id;
                if (stock_location_id) {
                    receipt['location'] = this.pos.stock_location_by_id[stock_location_id[0]];
                }
            }
            receipt['order'] = order
            receipt['currency'] = order.currency;
            receipt['guest'] = this.guest;
            receipt['guest_number'] = this.guest_number;
            receipt['delivery_date'] = this.delivery_date;
            receipt['delivery_address'] = this.delivery_address;
            receipt['delivery_phone'] = this.delivery_phone;
            receipt['note'] = this.note;
            const datetime_now = new Date();
            receipt['datetime_now'] = datetime_now.toLocaleString()
            receipt['signature'] = this.signature;
            if (this.shipping_client) {
                receipt['shipping_client'] = this.shipping_client;
            }
            if (this.fiscal_position) {
                receipt.fiscal_position = this.fiscal_position
            }
            if (this.amount_debit) {
                receipt['amount_debit'] = this.amount_debit;
            }
            let orderlines_by_category_name = {};
            let orderlines = order.orderlines.models;
            let categories = [];
            receipt['categories'] = [];
            receipt['orderlines_by_category_name'] = [];
            receipt['total_due'] = order.get_due(); // save amount due if have (display on receipt of parital order)
            if (order.internal_ref) {
                receipt['internal_ref'] = order.internal_ref
            }
            if (order.purchase_ref) {
                receipt['purchase_ref'] = order.purchase_ref
            }
            if (order.booking_uid) {
                receipt['booking_uid'] = order.booking_uid
            }
            if (order.sequence_number) {
                receipt['sequence_number'] = order.sequence_number
            }
            if (order.coupon_code) {
                receipt['coupon_code'] = this.coupon_code;
            }
            if (order.date_order) {
                receipt['date_order'] = this.date_order;
            }
            receipt['client'] = null
            if (order.get_client()) {
                receipt['client'] = order.get_client()
            }
            receipt['total_discount'] = order.get_total_discount()
            receipt['voucher_discount_amount'] = order.get_voucher_discount_amount();
            receipt['oloutlet_order_id'] = order.oloutlet_order_id;
            receipt['oloutlet_order_from'] = order.oloutlet_order_from;
            receipt['oloutlet_order_type'] = order.oloutlet_order_type;
            receipt['oloutlet_order_info'] = order.oloutlet_order_info;
            receipt['rounding_from_payment'] = order.rounding_from_payment;
            receipt['generate_voucher_value'] = order.generate_voucher_value || 0
            receipt['voucher_expired_date'] = order.voucher_expired_date || false
            receipt['voucher_number_use'] = order.voucher_number_use 
            receipt['voucher_min_amount'] = order.voucher_min_amount
            return receipt
        },

        isValidMinMaxPrice() {
            const self = this
            let order = this;
            var currency = false
            if(order){
                currency = order.currency
            }
            let pricelistOfOrder = this.pos._get_active_pricelist();
            let isValid = true
            for (let i = 0; i < this.orderlines.models.length; i++) {
                let l = this.orderlines.models[i]
                let uom_id = l.product.uom_id[0]
                if (l.uom_id) {
                    uom_id = l.uom_id
                }
                let pricelistItemHasMinMaxRule = l.product.get_pricelist_item_applied(pricelistOfOrder, l.quantity, uom_id)
                if (pricelistItemHasMinMaxRule && (pricelistItemHasMinMaxRule['min_price'] !== 0 && pricelistItemHasMinMaxRule['min_price'] !== 0) && (l.price < pricelistItemHasMinMaxRule['min_price'] || l.price > pricelistItemHasMinMaxRule['max_price'])) {
                    isValid = false
                    Gui.showPopup('ErrorPopup', {
                        title: l.product.display_name + _t(' Current Price: ') + self.pos.format_currency(l.price,false,currency) + _t(' Invalid !!!'),
                        body: _t('Price required Between: ') + self.pos.format_currency(pricelistItemHasMinMaxRule.min_price,false,currency) + _t(' to ') + self.pos.format_currency(pricelistItemHasMinMaxRule.max_price,false,currency),
                    })
                }
            }
            return isValid
        },
       
        async setBundlePackItems() {
            let order = this;
            let selectedLine = order.get_selected_orderline();
            if (selectedLine) {
                let combo_items = this.pos.combo_items.filter((c) => selectedLine.product.product_tmpl_id == c.product_combo_id[0])
                if (combo_items.length == 0) {
                    return this.pos.alert_message({
                        title: _t('Error'),
                        body: selectedLine.product.display_name + _t(' have not set Combo Items')
                    })
                } else {
                    if (!selectedLine.combo_items) {
                        selectedLine.combo_items = [];
                    }
                    let selectedComboItems = selectedLine.combo_items.map((c) => c.id)
                    combo_items.forEach(function (c) {
                        if (selectedComboItems.indexOf(c.id) != -1) {
                            c.selected = true
                        } else {
                            c.selected = false;
                        }
                        c.display_name = c.product_id[1];
                    })
                    let {confirmed, payload: result} = await Gui.showPopup('PopUpSelectionBox', {
                        title: _t('Select Bundle/Pack Items'),
                        items: combo_items
                    })
                    if (confirmed) {
                        if (result.items.length) {
                            selectedLine.set_combo_bundle_pack(result.items);
                        } else {
                            selectedLine.set_combo_bundle_pack([]);
                        }
                    }
                }

            } else {
                return this.pos.alert_message({
                    title: _t('Error'),
                    body: _t('Please selected 1 line')
                })
            }
        },
        async setProductPackaging() {
            let selectedOrder = this;
            if (!selectedOrder.get_selected_orderline()) {
                return this.pos.alert_message({
                    title: _t('Error'),
                    body: _t('This feature only active with Products has setup Cross Selling')
                })
            }
            let selectedLine = this.pos.get_order().get_selected_orderline();
            let product = selectedLine.product
        },
        async setMultiVariant() {
            let selectedOrder = this;
            let selectedLine = selectedOrder.get_selected_orderline();
            if (!selectedLine) {
                return this.pos.alert_message({
                    title: _t('Error'),
                    body: _t('Your order is blank cart')
                })
            }
            let product = selectedLine.product;
            let variants = this.pos.variant_by_product_tmpl_id[product.product_tmpl_id];
            if (!variants) {
                return this.pos.alert_message({
                    title: _t('Error'),
                    body: product.display_name + _t(' have not Active Multi Variant')
                })
            }
            let variantsSelectedIds = []
            if (selectedLine.variants) {
                variantsSelectedIds = selectedLine.variants.map((v) => (v.id))
            }
            variants.forEach(function (v) {
                if (variantsSelectedIds.indexOf(v.id) != -1) {
                    v.selected = true
                } else {
                    v.selected = false;
                }
            })

            let {confirmed, payload: results} = await Gui.showPopup('PopUpSelectionBox', {
                title: _t('Select Variants and Values for Product: ') + selectedLine.product.display_name,
                items: variants
            })
            if (confirmed) {
                let variantIds = results.items.map((i) => (i.id))
                selectedLine.set_variants(variantIds);
            }
        },

        async submitOrderToBackEnd(vals={}) {
            const selectedOrder = this;
            var currency = false
            if(selectedOrder){
                currency = selectedOrder.currency
            }
            let selectionList = this.pos.payment_methods.map((p) => ({
                id: p.id,
                item: p,
                name: p.name
            }))

            let return_payment_method_ids = vals['return_payment_method_ids'];
            if(return_payment_method_ids && return_payment_method_ids.length){
                selectionList = this.pos.payment_methods.map((p) => ({
                    id: p.id,
                    item: p,
                    name: p.name,
                    selected: return_payment_method_ids.includes(p.id),
                }))
            }
            let {confirmed, payload: selectedItems} = await Gui.showPopup(
                'PopUpSelectionBox',
                {
                    title: _t('If have not Exchange Products, Please select one Payment Method for full fill Amount of Order: ') + this.pos.format_currency(selectedOrder.get_total_with_tax(),false,currency),
                    items: selectionList,
                    onlySelectOne: true,
                }
            );
            if (confirmed && selectedItems['items'].length > 0) {
                const paymentMethod = selectedItems['items'][0]['item']
                selectedOrder.paymentlines.models.forEach(function (p) {
                    selectedOrder.remove_paymentline(p)
                })
                selectedOrder.add_paymentline(paymentMethod);
                const paymentLine = selectedOrder.selected_paymentline;
                paymentLine.set_amount(selectedOrder.get_total_with_tax());
                selectedOrder.trigger('change', selectedOrder);
                let order_ids = this.pos.push_single_order(selectedOrder, {})
                console.log('{submitOrderToBackEnd} pushed succeed order_ids: ' + order_ids)
                return this.pos.chrome.showScreen('ReceiptScreen');
            } else {
                selectedOrder.is_return = false
                selectedOrder.trigger('change', selectedOrder);
            }
        },

        client_use_coupon: async function (number) { 
            let self = this
            let tax_discount_policy = self.pos.company.tax_discount_policy;

            let coupon = false;
            let coupons = self.pos.db.get_pos_coupon_by_number(number);
            if(coupons.length){
                coupons = coupons.filter((o)=>o.no_of_usage > o.no_of_used || o.no_of_usage == 0);
                if(coupons.length){
                    coupon = coupons[0];
                }
            }
            if(!coupon){
                return Gui.showPopup('ErrorPopup', {
                    title: _t('Warning'),
                    body: _t('This coupon cannot be used'),
                });
            }


            let current_date = moment(moment().utc().format('YYYY-MM-DD HH:mm:ss'), 'YYYY-MM-DD HH:mm:ss');
            let start_date = moment(coupon.start_date, 'YYYY-MM-DD HH:mm:ss');
            let end_date = moment(coupon.end_date, 'YYYY-MM-DD HH:mm:ss');
            if(!(current_date.isAfter(start_date) && current_date.isBefore(end_date))){
                return Gui.showPopup('ErrorPopup', {
                    title: 'Error',
                    body: 'This coupon cannot be used because already expired'
                });
            }


            let is_product_in_cart = false;
            let product_in_cart = [];
            let product_in_cart_qty = 0;
            self.orderlines.models.forEach(l => {
                if (!l.is_product_coupon) {
                    if(coupon.product_ids.includes(l.product.id)){
                        is_product_in_cart = true;
                        product_in_cart.push(l.product.id);
                        product_in_cart_qty += l.get_quantity();
                    }
                }
            });
            if(product_in_cart_qty < coupon.minimum_purchase_quantity){
                return Gui.showPopup('ErrorPopup', {
                    title: 'Error',
                    body: 'This coupon cannot be used because it does not meet the minimum amount'
                });
            }

            if( coupon.no_of_usage != 0 &&  coupon.no_of_used >= coupon.no_of_usage ){
                return Gui.showPopup('ErrorPopup', {
                    title: 'Error',
                    body: 'This coupon cannot be used because already reached the max used'
                });
            }
            // TODO sync coupon
            let coupon_data = await self.pos.rpc({
                model: 'pos.coupon',
                method: 'get_data',
                args: [[coupon.id]],
                context: {}
            },{
                shadow: true,
                timeout: 2000,
            }).then(function (response) {
                return response;
            }, function (error) {
                if (error && error.message && error.message.code == -32098) {
                    console.error('[client_use_coupon] ~ Server Offline');
                } else {
                    console.error('[client_use_coupon] ~ Error 403');
                }
                Gui.showPopup('ErrorPopup', {
                    title: _t('Offline'),
                    body: _t('Your internet is slow /Offline'),
                });
                return Promise.reject(error);
            });
            if(!coupon_data){
                return;
            }
            if(coupon_data.length == 0){
                return Gui.showPopup('ErrorPopup', {
                    title: 'Error',
                    body: 'This coupon cannot be used because already Expired/Removed.'
                });
            }
            coupon = {...coupon, ...coupon_data[0]};
            self.pos.db.save_pos_coupon([coupon]);
            self.pos.db.set_last_write_date_by_model('pos.coupon', [coupon]);
            if( coupon.no_of_usage != 0 &&  coupon.no_of_used >= coupon.no_of_usage ){
                return Gui.showPopup('ErrorPopup', {
                    title: 'Error',
                    body: 'This coupon cannot be used because already reached the max used'
                });
            }
            if(!coupon.active || coupon.state!='active'){
                return Gui.showPopup('ErrorPopup', {
                    title: 'Error',
                    body: 'This coupon cannot be used because already Expired'
                });
            }

            // remove existing coupon
            self.reset_client_use_coupon();

            let total_product_in_cart_w_discount = 0;
            let total_withtax = self.get_total_with_tax();
            let total_without_tax = self.get_total_without_tax();
            self.orderlines.models.forEach(l => {
                if (!l.is_product_coupon) {
                    if(coupon.product_ids.includes(l.product.id)){
                        total_product_in_cart_w_discount += l.get_real_total_w_discount();
                    }
                }
            });

            let reward_type = false;
            let reward_amount = 0;
            let reward_product_name = false;
            let reward_product_ids = [];
            let reward_product_quantity = 1;

            if(coupon.type_apply == 'Specific Product' && is_product_in_cart){
                reward_type = coupon.reward_type;
                if(coupon.reward_type == 'Free Item'){
                    reward_product_ids = [...reward_product_ids, ...coupon.reward_product_ids];
                    reward_product_quantity = coupon.reward_quantity;
                }
                if(coupon.reward_type == 'Discount'){
                    if(coupon.reward_discount_type == 'Fixed'){
                        reward_amount = coupon.reward_discount_amount;
                        if( reward_amount > total_without_tax){
                            reward_amount = total_without_tax;
                        }
                    }else{
                        let discount = coupon.reward_discount_amount;
                        if (discount && total_without_tax){
                            reward_amount = (discount/100) * total_withtax;
                        }
                        if(coupon.reward_max_discount_amount){
                            if(reward_amount > coupon.reward_max_discount_amount){
                                reward_amount = coupon.reward_max_discount_amount;
                            }
                        }
                    }
                    if(reward_amount<=0){
                        return Gui.showPopup('ErrorPopup', {
                            title: _t('Error'),
                            body: _t('Please settle amount / percentage on this coupon correctly.')
                        });
                    }

                }
            }

            let format_amount = self.pos.format_currency(reward_amount);

            if(reward_type == 'Discount'){
                reward_product_name = 'Coupon';
                discount = ((reward_amount / total_product_in_cart_w_discount) * 100) / product_in_cart.length; // get discount each product in cart
                self.orderlines.models.forEach(line => {
                    if(!line.is_product_coupon && coupon.product_ids.includes(line.product.id)){
                        let coupon_vals = {
                            id: coupon.id,
                            name: coupon.name,
                            reward_amount: reward_amount,
                            reward_type: reward_type,
                        }
                        line.pos_coupon_id = coupon.id;
                        line.pos_coupon_reward_discount = 'Coupon';
                        if(line.discount_other_promotion){
                            line.discount_other_promotion['coupon']={'value':discount,'type':'percentage',coupon:coupon_vals}
                        }else{
                            line.discount_other_promotion={'coupon':{'value':discount,'type':'percentage',coupon:coupon_vals}} 
                        }
                        line.trigger('change', line);
                    }
                });
            }

            if(reward_type == 'Free Item'){
                let reward_products = [];
                for(let product_id of reward_product_ids){
                    let product = self.pos.db.get_product_by_id(product_id);
                    if(!product){
                        console.error('Product (ID:' + product_id + ') not available in POS');
                    }
                    if(product){
                        reward_products.push(product);
                    }
                }
                let reward_product_list = reward_products.map(product => ({
                    id: product.id,
                    label: product.display_name,
                    isSelected: false,
                    item: product
                }));
                let {confirmed, payload: product_gift} = await Gui.showPopup('SelectionPopup', {
                    title: _t('Please select one Product Gift'),
                    list: reward_product_list
                });
                if(confirmed){
                    self.add_product(product_gift, {
                        price: 0,
                        quantity: reward_product_quantity,
                        merge: false,
                        extras: {
                            is_product_coupon: true,  
                            is_product_coupon_reward: true,
                            pos_coupon_id: coupon.id,
                            pos_coupon_reward_description:  `${product_gift.name}`,
                        }
                    });
                    reward_product_name = product_gift.display_name;
                }
            }

            if(reward_type && reward_product_name){
                self.is_use_pos_coupon = true;
                self.pos_coupon_id = coupon.id; 
                self.trigger('change', self);
                if(reward_type == 'Free Item'){
                    self.pos.alert_message({
                        title: _t('Success!'),
                        body: 'Coupon Gift (' + reward_product_name + ') just set to Payment Order',
                    });
                }else{
                    self.pos.alert_message({
                        title: _t('Success!'),
                        body: 'Coupon just set to Payment Order',
                    });
                }
            }else{
                self.pos.alert_message({
                    title: _t('Success!'),
                    body: 'Conditions for apply this coupon code is not fulfilled',
                });
            }

        },

        reset_client_use_coupon: function(){
            let self = this;
            self.is_use_pos_coupon = false;
            self.pos_coupon_id = false;

            self.orderlines.models.forEach(l => {
                if(l.pos_coupon_id){
                    l.discount_other_promotion = {}
                    l.pos_coupon_id = false;
                    l.pos_coupon_reward_discount = '';
                    l.trigger('change', l);
                }
                if (l.is_product_coupon) {
                    self.remove_orderline(l);
                }
            });
            self.orderlines.models.forEach(l => {
                if(l.pos_coupon_id){
                    l.discount_other_promotion = {}
                    l.pos_coupon_id = false;
                    l.pos_coupon_reward_discount = '';
                    l.trigger('change', l);
                }
                if (l.is_product_coupon) {
                    self.remove_orderline(l);
                }
            });
            console.warn('[reset_client_use_coupon]');
        },

        validate_condition_client_use_coupon: function(){
            let self = this;
            let reset_coupon = false;
            let product_in_cart_qty = 0;
            let coupon = self.pos.db.get_pos_coupon_by_id(self.pos_coupon_id);
            if(coupon){
                self.orderlines.models.forEach(l => {
                    if (!l.is_product_coupon) {
                        if(coupon.product_ids.includes(l.product.id)){
                            product_in_cart_qty += l.get_quantity();
                        }
                    }
                });
            }
            if(product_in_cart_qty < coupon.minimum_purchase_quantity){
                reset_coupon = true;
            }
            if(reset_coupon){
                self.reset_client_use_coupon();
            }
        },

        get_savings_amount: function(){
            // Get amount of Discount/Promtion/voucher/Coupon
            let amount = 0;
            
            let discount_amount = this.get_total_discount();
            if(discount_amount){
                amount += Math.abs(discount_amount);
            }

            let voucher_amount = this.get_voucher_discount_amount();
            if(voucher_amount){
                amount += Math.abs(voucher_amount);
            }

            let coupon_amount = this.get_coupon_discount_amount();
            if(coupon_amount){
                amount += Math.abs(coupon_amount);
            }

            return amount;
        },

        client_use_voucher_new: function (voucher) { 
            let self = this
            let tax_discount_policy = self.pos.company.tax_discount_policy;
            let lines = self.orderlines.models;
            let voucher_amount = 0;
            let product = self.pos.config.product_voucher_service_id; 
            if(!product){
                return Gui.showPopup('ErrorPopup', {
                    title: _t('Error'),
                    body: _t('Product Voucher Service is not set in POS')
                });
            }
            if(product){
                product = self.pos.db.get_product_by_id(product[0]);
            }

            if(voucher.value<=0){
                return Gui.showPopup('ErrorPopup', {
                    title: 'Error',
                    body: 'Please settle amount / percentage on this voucher with correctly.'
                });
            }


            // remove existing voucher
            self.orderlines.models.forEach(l => {
                if (l.is_product_voucher) {
                    self.remove_orderline(l);
                }
            });
            self.orderlines.models.forEach(l => {
                if (l.is_product_voucher) {
                    self.remove_orderline(l);
                }
            });
            self.reset_client_use_voucher();


            let total_withtax = 0;
            let total_without_tax = 0;
            if(voucher.brand_ids && voucher.brand_ids.length){
                total_withtax = self.get_total_with_tax_in_brands(voucher.brand_ids);
                total_without_tax = self.get_total_without_tax_in_brands(voucher.brand_ids);
            }else {
                total_withtax = self.get_total_with_tax();
                total_without_tax = self.get_total_without_tax();
            }

            if( total_withtax >= voucher.minimum_purchase_amount){
                if (voucher['customer_id'] && voucher['customer_id'][0]) {
                    let client = self.pos.db.get_partner_by_id(voucher['customer_id'][0]);
                    if (client) {
                        self.set_client(client);
                    }
                }
                if (voucher['apply_type'] != 'fixed_amount') {
                    let discount = voucher.value;
                    if (voucher.maximum_discount_amount > 0){
                        var amount_disc = total_without_tax * (voucher.value/100);
                        if (amount_disc > voucher.maximum_discount_amount){
                            amount_disc = voucher.maximum_discount_amount;
                            discount = (amount_disc / total_without_tax) * 100;
                        }
                    }
                    if (discount && total_without_tax){
                        voucher_amount = (discount/100) * total_withtax;
                    }
                    
                } else {
                    voucher_amount =  voucher.value;
                    if( voucher_amount > total_without_tax){
                        voucher_amount = total_without_tax;
                    }
                }
            } else {
                return Gui.showPopup('ErrorPopup', {
                    title: 'Error',
                    body: 'This voucher cannot be used because it does not meet the minimum amount'
                });
            }

            //remove tax
            product['taxes_id'] = [];
            self.add_product(product, {
                price: -1 * voucher_amount,
                quantity: 1,
                merge: false, 
                extras: {
                    is_product_voucher: true,  
                }
            });

            self.voucher_id = voucher.id; 
            self.client_use_voucher = true;
            self.client_use_voucher_amount = voucher_amount;
            self.voucher_amount = voucher_amount;
            self.trigger('change', self);

            return self.pos.alert_message({
                title: _t('Success!'),
                body: 'Voucher just set to Payment Order',
            });
        },

        reset_client_use_voucher: function(){
            self.voucher_id = false; 
            self.client_use_voucher = false;
            self.voucher_expired_date = false;
            self.client_use_voucher_amount = 0;
        },
          
        client_use_voucher: function (voucher) {
            var self = this
            var company = self.pos.company
            var tax_discount_policy = company.tax_discount_policy
            let lines = this.orderlines.models;

            if(voucher.value<=0){
                return Gui.showPopup('ErrorPopup', {
                        title: 'Error',
                        body: 'Please settle amount / percentage on this voucher with correctly.'
                    });
            }
            if(this.get_total_with_tax() >= voucher.minimum_purchase_amount){
                this.voucher_id = voucher.id;
                let due = this.get_due();
                if (voucher['customer_id'] && voucher['customer_id'][0]) {
                    let client = this.pos.db.get_partner_by_id(voucher['customer_id'][0]);
                    if (client) {
                        this.set_client(client)
                    }
                }
                if (voucher['apply_type'] != 'fixed_amount') {
                    var discount = voucher.value
                    if (voucher.maximum_discount_amount > 0)
                        {
                            var amount_disc = this.get_total_without_tax() * (voucher.value/100);
                            if (amount_disc > voucher.maximum_discount_amount)
                            {
                                amount_disc = voucher.maximum_discount_amount;
                                discount = (amount_disc/ this.get_total_without_tax()) * 100
                            }

                        }
                    if(discount&&this.get_total_without_tax()){
                        this.voucher_amount = (discount/100) * this.get_total_without_tax()
                    }
                    for (let i = 0; i < lines.length; i++) {
                        let line = lines[i];
                        if(voucher.value && line.get_price_with_tax()){
                            if(discount!=0 ){
                                // line.discount = discount;
                                if(line.discount_other_promotion){
                                    line.discount_other_promotion['voucher']={'value':discount,'type':'percentage'}
                                }
                                else{
                                    line.discount_other_promotion={'voucher':{'value':discount,'type':'percentage'}} 
                                }
                                
                                line.trigger('change', line)
                            }
                        }
                    }
                    
                }
                else {
                    var discount_amount = 0
                    var fixed_amount = voucher.value  
                    this.voucher_amount =  fixed_amount
                    var disc = 0  
                    var real_total = 0
                    for(let line of lines){
                        if(line.is_product_coupon){
                            continue;
                        }
                        real_total+=line.get_real_total_w_discount();
                    }

                    if(fixed_amount) {
                        disc = fixed_amount
                        // if(tax_discount_policy != 'untax'){
                        //     disc=(disc/ this.get_total_without_tax()) * 100
                        // }
                        // else {
                            disc=(disc/ real_total) * 100
                        // }
                    }
                    for (let i = 0; i < lines.length; i++) {
                        var line = lines[i];
                        if(disc!=0 && line.get_price_with_tax()){
                            if(line.discount_other_promotion){
                                line.discount_other_promotion['voucher']={'value':disc,'type':'fixed'}
                            }
                            else{
                                line.discount_other_promotion={'voucher':{'value':disc,'type':'fixed'}} 
                            }
                            line.trigger('change', line)
                        }
                    }
                }
            }
            else{
                return Gui.showPopup('ErrorPopup', {
                        title: 'Error',
                        body: 'This voucher cannot be used because it does not meet the minimum amount'
                    });
            }
            this.pos.alert_message({
                title: _t('Success!'),
                body: 'Voucher just set to Payment Order',
            });
                

            // this.voucher_id = voucher.id;
            // let method = _.find(this.pos.payment_methods, function (method) {
            //     return method.pos_method_type == 'voucher';
            // });
            // if (method) {
            //     this.paymentlines.models.forEach(function (p) {
            //         if (p.payment_method.journal && p.payment_method.journal.pos_method_type == 'voucher') {
            //             self.remove_paymentline(p)
            //         }
            //     })
            //     let due = this.get_due();
            //     if (voucher['customer_id'] && voucher['customer_id'][0]) {
            //         let client = this.pos.db.get_partner_by_id(voucher['customer_id'][0]);
            //         if (client) {
            //             this.set_client(client)
            //         }
            //     }
            //     let amount = 0;
            //     if (voucher['apply_type'] == 'fixed_amount') {
            //         if(this.get_total_with_tax() >= voucher.minimum_purchase_amount )
            //         {
            //             amount = voucher.value;
            //         }

            //     } else {
            //         if(this.get_total_with_tax() >= voucher.minimum_purchase_amount)
            //         {
            //             if (voucher.maximum_discount_amount > 0)
            //             {
            //                 amount = this.get_total_with_tax() / 100 * voucher.value;
            //                 if (amount > voucher.maximum_discount_amount)
            //                 {
            //                     amount = voucher.maximum_discount_amount;
            //                 }

            //             }
            //             else{
            //                     amount = this.get_total_with_tax() / 100 * voucher.value;
            //                  }
            //     }
            //     }
            //     if (amount <= 0) {
            //         return Gui.showPopup('ConfirmPopup', {
            //             title: _t('Warning'),
            //             body: _t("Voucher's full amount already used / Check the minimum voucher purchase amount."),
            //             disableCancelButton: true,
            //         });
            //     }
            //     this.add_paymentline(method);
            //     let voucher_paymentline = this.selected_paymentline;
            //     voucher_paymentline['voucher_id'] = voucher['id'];
            //     voucher_paymentline['voucher_code'] = voucher['code'];
            //     let voucher_amount = 0;
            //     if (amount >= due) {
            //         voucher_amount = due;
            //     } else {
            //         voucher_amount = amount;
            //     }
            //     if (voucher_amount > 0) {
            //         voucher_paymentline.set_amount(voucher_amount);
            //         this.pos.alert_message({
            //             title: _t('Success! Voucher just set to Payment Order'),
            //             body: _t('Set ' + this.pos.format_currency(voucher_amount)) + ' to Payment Amount of Order ',
            //         });
            //     } else {
            //         this.pos.alert_message({
            //             title: _t('Warning'),
            //             body: _t('Selected Order Paid Full, Could not adding more Voucher Value'),
            //         });
            //     }
            // } else {
            //     this.pos.alert_message({
            //         title: _t('Warning'),
            //         body: _t('Your POS Payment Voucher removed, we could not add voucher to your Order'),
            //     });
            // }
        },
        set_picking_type: function (picking_type_id) {
            let picking_type = this.pos.stock_picking_type_by_id[picking_type_id];
            this.picking_type = picking_type;
            this.pos.trigger('set.picking.type')
        },
        remove_paymentline: function (line) {
            let res = _super_Order.remove_paymentline.apply(this, arguments);
            console.log('[remove_paymentline] deleted payment line')
        },
        set_pricelist: function (pricelist) {
            let self = this
            if (this.currency && pricelist.currency_id && this.currency.id != pricelist.currency_id[0]) {
                this.paymentlines.models.forEach(function (p) {
                    self.remove_paymentline(p)
                })
            }
            let lastPricelist = this.pricelist;
            // todo: we not call super odoo because
            let res = _super_Order.set_pricelist.apply(this, arguments);
            // todo: when change pricelist difference currency with POS, auto recompute price of cart
            if (!this.is_return && pricelist && pricelist.currency_id && lastPricelist && pricelist['id'] != lastPricelist['id']) {
                let selectedCurrency = this.pos.currency_by_id[pricelist.currency_id[0]];
                if (lastPricelist && lastPricelist.currency_id && pricelist.currency_id && lastPricelist.currency_id[0] != pricelist.currency_id[0]) {
                    let linesToReCompute = this.get_orderlines().filter((l) => !l.price_manually_set)
                    linesToReCompute.forEach(function (l) {
                        l.set_unit_price(l.product.get_price(pricelist, l.get_quantity()));
                        self.fix_tax_included_price(l);
                    })
                }
                this.currency = selectedCurrency;
                this.pricelist = pricelist;
                this.trigger('change', this);
            }
            return res;
        },

        get_differene_currency_change() {
            const baseChange= this.get_change()
            if (this.currency && this.currency.id != this.pos.base_currency.id) {
                return this.pos.format_currency_no_symbol(baseChange / this.currency['converted_currency']) + ' ' + this.pos.base_currency.symbol
            }
            return null
        },

        add_paymentline: function (payment_method) {
            // const linecheck = this.paymentlines.find((pline) => pline.payment_method.id === payment_method.id);
            // if (linecheck) {
            //     return this.pos.alert_message({
            //                 title: _t('Warning !'),
            //                 body: _t("Not allowed to have multiple payment method. ")
            //             })
            // }
            let newPaymentline = _super_Order.add_paymentline.apply(this, arguments);
            if (payment_method.fullfill_amount && this.get_due() != 0) {
                newPaymentline.set_amount(this.get_due())
            }
            this.pos.trigger('refresh.customer.facing.screen');
            return newPaymentline;
        },
        set_stock_location: function (location) {
            // todo: set location_id for order backend
            this.location = location;
            this.location_id = location.id;
            this.pos.config.stock_location_id = [location.id, location.name];
            this.trigger('change', this);
        },
        remove_selected_orderline: function () {
            let line = this.get_selected_orderline();
            if (line) {
                this.remove_orderline(line)
            }
        },
        set_currency: function (currency) {
            let rate = currency.rate;
            if (rate > 0) {
                let lines = this.orderlines.models;
                for (let n = 0; n < lines.length; n++) {
                    let line = lines[n];
                    line.set_unit_price_with_currency(line.price, currency)
                }
                this.currency = currency;
                this.pos.trigger('change:currency'); // TODO: update ticket and order cart
            } else {
                this.currency = null;
            }
            this.trigger('change', this);
        },
        add_barcode: function (element) {
            if (!this.element) {
                try {
                    JsBarcode('#' + element, this['ean13'], {
                        format: "EAN13",
                        displayValue: true,
                        fontSize: 14
                    });
                    this[element + '_bas64'] = document.getElementById(element).src
                } catch (ex) {
                    console.warn('Error set barcode to element: ' + ex)
                }
            }
        },
        zero_pad: function (num, size) {
            if (num == undefined) {
                console.error('Login number error: ' + num)
                num = '0123456789'
            }
            let s = "" + num;
            while (s.length < size) {
                s = s + Math.floor(Math.random() * 10).toString();
            }
            return s;
        },
        get_guest: function () {
            if (this.guest) {
                return this.guest
            } else {
                return null
            }
        },
        _get_client_content: function (client) {
            let content = '';
            if (client.mobile) {
                content += 'Mobile: ' + client.mobile + ' , ';
            }
            if (client.phone) {
                content += 'Mobile: ' + client.phone + ' , ';
            }
            if (client.email) {
                content += 'Email: ' + client.email + ' , ';
            }
            if (client.address) {
                content += 'Address: ' + client.address + ' , ';
            }
            return content
        },
        set_shipping_client: function (client) {
            this.assert_editable();
            this.set('client', client);
            this.shipping_client = client;
        },
        set_client: async function (client) {
            let self = this;
            if (!client && !this.pos.the_first_load && this.pos.chrome && this.pos.config.add_customer_before_products_already_in_shopping_cart) {
                return this.pos.alert_message({
                    title: _t('Warning'),
                    body: _t('You can not deselect and set null Customer. Because your POS active feature Required add Customer to cart')
                })
            }
            const res = _super_Order.set_client.apply(this, arguments);
            if (client && !this.pos.the_first_load) {
                if (client.group_ids.length > 0) {
                    let lists = [];
                    for (let i = 0; i < client.group_ids.length; i++) {
                        let group_id = client.group_ids[i];
                        let group = this.pos.membership_group_by_id[group_id];
                        if (group.pricelist_id) {
                            lists.push({
                                'id': group.id,
                                'label': group.name + this.pos.env._t(' with a pricelist: ') + group.pricelist_id[1],
                                'item': group
                            });
                        }
                    }
                    if (lists.length > 0) {
                        const {confirmed, payload: group} = await Gui.showPopup('SelectionPopup', {
                            title: this.pos.env._t('Choice one Group/MemberShip'),
                            list: lists
                        })
                        if (confirmed) {
                            if (!this.pos.pricelist_by_id[group.pricelist_id[0]]) {
                                this.pos.alert_message({
                                    title: _t('Error'),
                                    body: _t('Your POS not added pricelist: ') + group.pricelist_id[1],
                                })
                            } else {
                                let pricelist = this.pos.pricelist_by_id[group.pricelist_id[0]];
                                this.set_pricelist(pricelist);
                            }
                        }
                    }
                }
                if (this.pos.coupons_by_partner_id && this.pos.coupons_by_partner_id[client.id] && this.get_total_with_tax() > 0) {
                    let lists = this.pos.coupons_by_partner_id[client.id].map(c => ({
                        id: c.id,
                        label: c.code,
                        item: c
                    }))
                    const {confirmed, payload: coupon} = await Gui.showPopup('SelectionPopup', {
                        title: client.display_name + this.pos.env._t(' have some Coupons, please select one apply to Order'),
                        list: lists
                    })
                    if (confirmed) {
                        this.pos.getInformationCouponPromotionOfCode(coupon.code)
                    }
                }
            }
            if (client && this.pos.services_charge_ids && this.pos.services_charge_ids.length && this.pos.config.service_shipping_automatic && !this.pos.the_first_load) {
                this.pos.rpc({
                    model: 'pos.service.charge',
                    method: 'get_service_shipping_distance',
                    args: [[], client.id, this.pos.config.stock_location_id[0]],
                    context: {}
                }, {
                    shadow: true,
                    timeout: 6500,
                }).then(function (service) {
                    for (let i = 0; i < self.orderlines.models.length; i++) {
                        let line = self.orderlines.models[i];
                        if (line.is_shipping_cost) {
                            self.remove_orderline(line);
                        }
                    }
                    if (service && service['service_id']) {
                        self.delivery_address = service['to_address'];
                        let service_charge = self.pos.service_charge_by_id[service['service_id']];
                        let product = self.pos.db.get_product_by_id(service_charge['product_id'][0]);
                        if (product) {
                            self.add_shipping_cost(service_charge, product, true)
                        }
                    }
                }, function (err) {
                    return self.pos.query_backend_fail(err)
                })
            }
            let pricelistOfClient = null
            if (client) {
                pricelistOfClient = _.findWhere(this.pos.pricelists, {
                    id: client.property_product_pricelist[0],
                }) || this.pos.default_pricelist
                if (pricelistOfClient) {
                    this.set_pricelist(pricelistOfClient)
                }
            } else {
                this.set_pricelist(this.pos.default_pricelist)
            }
            this.pos.trigger('refresh.customer.facing.screen');
            if (client) {
                this.pos.alert_message({
                    title: _t('Successfully'),
                    body: client['name'] + _t(' Set to order !')
                })
            } else {
                this.pos.alert_message({
                    title: _t('Successfully'),
                    body: _t('Deselected Customer !')
                })
            }
            return res
        },
        add_shipping_cost: function (service, product, is_shipping_cost) {
            if (service['type'] == 'fixed') {
                this.add_product(product, {
                    price: service.amount,
                    quantity: 1,
                    merge: false,
                    extras: {
                        service_id: service.id,
                    }
                });
                this.pos.chrome.showNotification(_t('Add Service Charge Amount'), this.pos.format_currency(service.amount,false,this.currency))
            } else {
                let amount_total = 0
                if (this.pos.config.service_charge_type == 'tax_included') {
                    amount_total = this.get_total_with_tax();
                } else {
                    amount_total = this.get_total_without_tax();
                }
                if (amount_total > 0) {
                    product['taxes_id'] = []
                    let price = amount_total * service.amount / 100
                    this.add_product(product, {
                        price: price,
                        quantity: 1,
                        merge: false,
                        extras: {
                            service_id: service.id,
                        }
                    });
                    this.pos.chrome.showNotification(_t('Add Service Charge Amount'), this.pos.format_currency(amount_total,false,this.currency))
                }

            }
            let selected_line = this.get_selected_orderline();
            selected_line.is_shipping_cost = is_shipping_cost;
            selected_line.service_id = service.id;
            selected_line.trigger('change', selected_line)
        },
        validate_global_discount: function () {
            let self = this;
            let client = this && this.get_client();
            if (client && client['discount_id']) {
                this.pos.gui.show_screen('products');
                this.discount = this.pos.discount_by_id[client['discount_id'][0]];
                this.pos.gui.show_screen('products');
                let body = client['name'] + ' have discount ' + self.discount['name'] + '. Do you want to apply ?';
                return Gui.showPopup('ConfirmPopup', {
                    'title': _t('Customer special discount ?'),
                    'body': body,
                    confirm: function () {
                        self.add_global_discount(self.discount);
                        self.pos.gui.show_screen('payment');
                        self.validate_payment();
                    },
                    cancel: function () {
                        self.pos.gui.show_screen('payment');
                        self.validate_payment();
                    }
                });
            } else {
                this.validate_payment();
            }
        },
        validate_payment_order: function () {
            let self = this;
            let client = this.get_client();
            if (this && this.orderlines.models.length == 0) {
                this.pos.gui.show_screen('products');
                return this.pos.alert_message({
                    title: _t('Warning'),
                    body: _t('Your order is blank cart'),
                })
            } else {
                if (this.get_total_with_tax() == 0) {
                    this.pos.alert_message({
                        title: _t('Warning'),
                        body: _t('Your order have total paid is 0, please take careful')
                    })
                }
            }
            if (this.remaining_point && this.remaining_point < 0) {
                this.pos.gui.show_screen('products');
                return this.pos.alert_message({
                    title: _t('Warning'),
                    body: _t('You could not applied redeem point bigger than client point'),
                });
            }
            this.validate_order_return();
            if (!this.is_return) {
                this.validate_promotion();
            }
            if (this.is_to_invoice() && !this.get_client()) {
                this.pos.gui.show_screen('clientlist');
                this.pos.alert_message({
                    title: _t('Warning'),
                    body: _t('Please add client the first')
                });
                return false;
            }
            return true
        },
        validate_order_return: function () {
            if (this.pos.config.required_reason_return) {
                let line_missed_input_return_reason = _.find(this.orderlines.models, function (line) {
                    return line.get_price_with_tax() < 0 && !line.has_input_return_reason();
                });
                if (line_missed_input_return_reason) {
                    this.pos.gui.show_screen('products');
                    return this.pos.alert_message({
                        title: _t('Alert'),
                        body: _t('Please input return reason for each line'),
                    });
                } else {
                    return false
                }
            } else {
                return false
            }
        },
        get_total_discounts: function () {
            let total_discounts = 0
            var self = this
            var company = self.pos.company
            var tax_discount_policy = company.tax_discount_policy
            this.orderlines.forEach(l => {
                if (l.price_extra) {
                    if (l.price_extra <= 0) {
                        total_discounts += -l.price_extra
                    } else {
                        total_discounts += l.price_extra
                    }
                }
                if(l.promotion_stack){
                    let real_discount = 0;
                    if (tax_discount_policy!='untax'){
                        var base_price = l.get_all_prices().priceWithoutTaxWithoutDiscount/l.quantity;
                    }
                    else{
                        var base_price = l.price;
                    }
                    let total_discount = 0;
                    total_discount += base_price;
                    for(let i in l.promotion_stack){
                        let price_discount = total_discount * (l.promotion_stack[i].discount/100);
                        total_discount = total_discount - price_discount;
                        real_discount += price_discount/base_price;
                        total_discounts += price_discount * l.quantity;
                    }
                }
            })

            return total_discounts
        },
        set_discount_price: function (price_will_discount, tax) {
            if (tax.include_base_amount) {
                let line_subtotal = this.get_price_with_tax() / this.quantity;
                let tax_before_discount = (line_subtotal - line_subtotal / (1 + tax.amount / line_subtotal));
                let price_before_discount = line_subtotal - tax_before_discount; // b
                let tax_discount = price_will_discount - price_will_discount / (1 + tax.amount / price_will_discount);
                let price_discount = price_will_discount - tax_discount; // d
                let price_exincluded_discount = price_before_discount - price_discount;
                let new_tax_wihtin_discount = price_exincluded_discount - price_exincluded_discount / (1 + tax.amount / price_exincluded_discount);
                let new_price_wihtin_discount = line_subtotal - price_will_discount;
                let new_price_without_tax = new_price_wihtin_discount - new_tax_wihtin_discount;
                let new_price_within_tax = new_price_without_tax + new_tax_wihtin_discount;
                this.set_unit_price(new_price_within_tax);
            } else {
                let tax_discount = tax.amount / 100 * price_will_discount;
                let price_discount = price_will_discount - tax_discount;
                let new_price_within_tax = this.price - price_discount - (0.91 * (parseInt(price_will_discount / 100)));
                this.set_unit_price(new_price_within_tax);
            }
        },
        add_global_discount: function (discount) {
            const amount_withtax = this.get_total_with_tax();
            if (amount_withtax <= 0) {
                return this.pos.alert_message({
                    title: _t('Error'),
                    body: _t('Total Amount Order smaller than or equal 0, not possible add Discount'),
                })
            }
            let lines = this.orderlines.models;
            if (!lines.length) {
                return this.pos.alert_message({
                    title: _t('Warning'),
                    body: _t('Your order is blank cart'),
                })
            }

            if (discount.type == 'percent') {
                for (let i = 0; i < lines.length; i++) {
                    let line = lines[i];
                    if(line.promotion_stack){
                        return Gui.showPopup('ErrorPopup', {
                            title: this.pos.env._t('Warning'),
                            body: this.pos.env._t('Please cancel promotion discount first.')
                        })
                    }
                    if(discount.amount && line.get_price_with_tax()){
                        if(line.discount_other_promotion){
                            line.discount_other_promotion['pos.global.discount']=discount.amount
                        }
                        else{
                            line.discount_other_promotion={'pos.global.discount':discount.amount} 
                        }
                        line.trigger('change', line)
                    }
                }
            } else {
                var discount_amount = 0

                var fixed_amount = discount.amount   
                var disc = 0  
                var real_total = 0
                for(let line of lines){
                    if(line.is_product_coupon){
                        continue;
                    }
                    real_total+=line.get_real_total_w_discount();
                }
                if(fixed_amount && this.get_total_without_tax()) {
                    disc = fixed_amount
                    var company_pos = this.pos.company
                    var tax_discount_policy = company_pos.tax_discount_policy
                    // if(tax_discount_policy != 'untax'){
                    //     disc=(disc/ this.get_total_without_tax()) * 100
                    // }
                    // else {
                        disc=(disc/ real_total) * 100
                    // }

                }
                for (let i = 0; i < lines.length; i++) {
                    let line = lines[i];
                    if(line.promotion_stack){
                        return Gui.showPopup('ErrorPopup', {
                            title: this.pos.env._t('Warning'),
                            body: this.pos.env._t('Please cancel promotion discount first.')
                        })
                    }
                    if(disc!=0 && line.get_price_with_tax()){
                        if(line.discount_other_promotion){
                            line.discount_other_promotion['pos.global.discount']=disc
                        }
                        else{
                            line.discount_other_promotion={'pos.global.discount':disc} 
                        }
                        line.trigger('change', line)
                    }
                }
                // if (amount_withtax < discount) {
                //     discount = amount_withtax
                // }
                // const linesHasAmountSmallerThan0 = lines.filter(l => l.get_price_with_tax() < 0)
                // if (linesHasAmountSmallerThan0 && linesHasAmountSmallerThan0.length > 0) {
                //     return this.pos.alert_message({
                //         title: _t('Error'),
                //         body: _t('Could not applied Global Discount if have one Line have Amount smaller than 0'),
                //     })
                // }
                // for (let i = 0; i < lines.length; i++) {
                //     let line = lines[i];
                //     let percent_disc = line.get_price_with_tax() / amount_withtax
                //     line.price_extra = -percent_disc * discount['amount'];
                //     line.trigger('change', line)

                // }
            }
        },
        clear_discount_extra: function () {
            let lines = this.orderlines.models;
            lines.forEach(l => {
                l.discount_extra = 0
                l.price_extra = 0
                l.set_unit_price(l.product.get_price(l.order.pricelist, l.get_quantity()))
            })
        },
        async set_discount_value(discount) {
            // todo: will check discount bigger than limited discount or not? If bigger than, call admin confirm it
            if (!this.pos.config.discount_global_id) {
                return Gui.showPopup('ErrorPopup', {
                    title: this.pos.env._t('Warning'),
                    body: this.pos.env._t('Your POS Config not set Discount Product Value. Please go to Security and Discount [Tab] of POS Config and add it')
                });
            }
            if (!this.pos.db.get_product_by_id(this.pos.config.discount_global_id[0])) {
                return Gui.showPopup('ErrorPopup', {
                    title: this.pos.env._t('Warning'),
                    body: this.pos.config.discount_global_id[1] + this.pos.env._t(' not Available in POS or Sale Ok is uncheck')
                });
            }
            const discountProduct = this.pos.db.product_by_id[this.pos.config.discount_global_id[0]];
            const order = this;
            if (!discountProduct) {
                return Gui.showPopup('ErrorPopup', {
                    title: this.pos.env._t('Error'),
                    body: this.pos.config.discount_global_id[1] + this.pos.env._t(' not available in POS')
                });
            } else {
                order.orderlines.models.forEach(l => {
                    if (l.product && l.product.id == discountProduct['id']) {
                        order.remove_orderline(l)
                    }
                })
                order.orderlines.models.forEach(l => {
                    if (l.product && l.product.id == discountProduct['id']) {
                        order.remove_orderline(l)
                    }
                })
            }
            let lines = order.get_orderlines();
            let total_withtax = this.get_total_with_tax();
            let total_qty = 0
            lines.forEach(l => {
                total_qty += l.quantity
            })
            if (discount < 0) {
                return Gui.showPopup('ErrorPopup', {
                    title: _t('Error'),
                    body: _t('It not possible set Discount Value smaller than 0')
                })
            }
            if (discount > total_withtax) {
                discount = total_withtax
            }
            const amountWithTax = this.get_total_with_tax();
            lines = lines.filter(l => l.get_price_with_tax() > 0 && l.quantity > 0)
           
            if (this.pos.config.discount_limit) {
                let discount_limited = 0;
                let is_discount_limit = false;
                if (this.pos.config.discount_limit_type == 'percentage'){
                    let discount_percentage = (discount/amountWithTax) * 100;
                    if(discount_percentage > this.pos.config.discount_limit_amount){
                        is_discount_limit = true;
                        discount_limited = amountWithTax * (this.pos.config.discount_limit_amount/100);
                        console.warn('Discount limit by Percentage Amount Discount:', discount_limited)
                    }

                } else {
                    if(discount > this.pos.config.discount_limit_amount){
                        is_discount_limit = true;
                        discount_limited = this.pos.config.discount_limit_amount
                        console.warn('Discount limit by Fixed Amount Discount:', discount_limited)
                    }
                }

                if(this.pos.config.discount_unlock_by_manager){
                    if(is_discount_limit){
                        let confirm = await this.pos._validate_action(_t('Add Discount Value'));
                        if (!confirm) {
                            return Gui.showPopup('ErrorPopup', {
                                title: this.pos.env._t('Warning'),
                                body: this.pos.env._t('Required Manager Approved this Discount because this Discount bigger than Discount Value Limit on POS Setting')
                            });
                        }
                    }
                } else {
                    if(is_discount_limit){
                        discount = discount_limited;
                    }
                }

                this._appliedDiscountValue(lines, discount, amountWithTax);
            } else {
                this._appliedDiscountValue(lines, discount, amountWithTax);
            }
        },

        _appliedDiscountValue(lines, discount, amount_withtax) {
            let discountProduct = this.pos.db.product_by_id[this.pos.config.discount_global_id[0]];
            if (discountProduct) {
                this.add_product(discountProduct, {quantity: -1, merge: false});
                let selectedLine = this.get_selected_orderline();
                selectedLine.price_manually_set = true;
                selectedLine.set_unit_price(discount);
                this.pos.alert_message({
                    title: _t('Successfully'),
                    body: this.pos.format_currency(discount,false,this.currency) + _t(' Discount Amount, Just Added to Order')
                })
                return true
            } else {
                return false
            }
        },
        set_to_invoice: function (to_invoice) {
            if (to_invoice) {
                this.trigger('change');
            }
            return _super_Order.set_to_invoice.apply(this, arguments);
        },
        is_email_invoice: function () { // send email invoice or not
            return this.email_invoice;
        },
        set_email_invoice: function (email_invoice) {
            this.assert_editable();
            this.email_invoice = email_invoice;
            this.set_to_invoice(email_invoice);
        },
        get_root_category_by_category_id: function (category_id) { // get root of category, root is parent category is null
            let root_category_id = category_id;
            let category_parent_id = this.pos.db.category_parent[category_id];
            if (category_parent_id) {
                root_category_id = this.get_root_category_by_category_id(category_parent_id)
            }
            return root_category_id
        },
        // odoo wrong when compute price with tax have option price included
        // and now i fixing
        fix_tax_included_price: function (line) {
            this.syncing = true;
            _super_Order.fix_tax_included_price.apply(this, arguments);
            if (this.fiscal_position) {
                let unit_price = line.product['lst_price'];
                let taxes = line.get_taxes();
                let mapped_included_taxes = [];
                _(taxes).each(function (tax) {
                    let line_tax = line._map_tax_fiscal_position(tax);
                    if (tax.price_include && tax.id != line_tax.id) {
                        mapped_included_taxes.push(tax);
                    }
                });
                if (mapped_included_taxes.length > 0) {
                    unit_price = line.compute_all(mapped_included_taxes, unit_price, 1, this.pos.currency.rounding, true).total_excluded;
                    line.set_unit_price(unit_price);
                }
            }
            this.syncing = false;
        },
        set_signature: function (signature) {
            this.signature = signature;
            this.trigger('change', this);
        },
        get_signature: function () {
            if (this.signature) {
                return 'data:image/png;base64, ' + this.signature
            } else {
                return null
            }
        },
        set_note: function (note) {
            this.note = note;
            this.trigger('change', this);
        },
        get_note: function () {
            return this.note;
        },
        get_due_without_rounding: function (paymentline) {
            if (!paymentline) {
                let due = this.get_total_with_tax() - this.get_total_paid();
            } else {
                let due = this.get_total_with_tax();
                let lines = this.paymentlines.models;
                for (let i = 0; i < lines.length; i++) {
                    if (lines[i] === paymentline) {
                        break;
                    } else {
                        due -= lines[i].get_amount();
                    }
                }
            }
            return due;
        },
        generate_unique_ean13: function (array_code) {
            if (array_code.length != 12) {
                return -1
            }
            let evensum = 0;
            let oddsum = 0;
            for (let i = 0; i < array_code.length; i++) {
                if ((i % 2) == 0) {
                    evensum += parseInt(array_code[i])
                } else {
                    oddsum += parseInt(array_code[i])
                }
            }
            let total = oddsum * 3 + evensum;
            return parseInt((10 - total % 10) % 10)
        },
        get_product_image_url: function (product) {
            return window.location.origin + '/web/image?model=product.product&field=image_128&id=' + product.id;
        },
        _covert_pos_line_to_sale_line: function (line) {
            let product = this.pos.db.get_product_by_id(line.product_id);
            let line_val = {
                product_id: line.product_id,
                price_unit: line.price_unit,
                product_uom_qty: line.qty,
                discount: line.discount,
                product_uom: product.uom_id[0],
            };
            if (line.uom_id) {
                line_val['product_uom'] = line.uom_id
            }
            // if (line.variants) {
            //     line_val['variant_ids'] = [[6, false, []]];
            //     for (let j = 0; j < line.variants.length; j++) {
            //         let variant = line.variants[j];
            //         line_val['variant_ids'][0][2].push(variant.id)
            //     }
            // }
            if (line.tax_ids) {
                line_val['tax_id'] = line.tax_ids;
            }
            if (line.note) {
                line_val['pos_note'] = line.note;
            }
            return [0, 0, line_val];
        },
        _final_and_print_booking_order: function (result) {
            let order = this.pos.get_order();
            this.pos.set('order', order);
            this.pos.db.remove_unpaid_order(order);
            this.pos.db.remove_order(order['uid']);
            order.name = result['name'];
            order.uid = result['name']
            order.booking_uid = result['name']
            order.temporary = true;
            order.trigger('change', order);
            let booking_link = window.location.origin + "/web#id=" + result.id + "&view_type=form&model=sale.order";
            window.open(booking_link, '_blank');
        },
        remove_orderline: async function (line) {
            // ** Issue when remove all orderline
            // if (!this.syncing && !this.pos.the_first_load) {
            //     let validate = await this.pos._validate_action(this.pos.env._t('Remove Line'));
            //     if (!validate) {
            //         return false;
            //     }
            // }
            let res = _super_Order.remove_orderline.apply(this, arguments);
            if (line.coupon_ids && !this.pos.the_first_load) {
                this.pos.rpc({
                    model: 'coupon.generate.wizard',
                    method: 'remove_giftcards',
                    args: [[], line.coupon_ids],
                })
                this.pos.alert_message({
                    title: this.pos.env._t('Alert'),
                    body: this.pos.env._t('Gift cards created before just removed')
                })
            }
            return res
        },
        async getProductRecommendations(product) {
            const product_recommendation_number = this.pos.config.product_recommendation_number || 10
            const productRecommendationsIds = await rpc.query({
                model: 'pos.order.line',
                method: 'getProductRecommendations',
                args: [[], product.id, product_recommendation_number],
                context: {}
            }, {
                shadow: true,
                timeout: 10000,
            })
            this.pos.set('ProductRecommendations', productRecommendationsIds)
            if (productRecommendationsIds.length > 0) {
                console.log('[productRecommendationsIds] total products: ' + productRecommendationsIds.length)
            }
        },

        _is_exist_product_lot_in_cart: function (order, product, selectedLot) {
            let value = false;
            let lot_names = [];
            let orderlines = order.get_orderlines();
            for (var i = 0; i < orderlines.length; i++) {
                let orderline = order.get_orderlines().at(i);
                if(orderline.product.id == product.id){
                    let lot_lines = orderline.get_lot_lines();
                    for(let lot_line of lot_lines){
                        lot_names.push(lot_line.attributes.lot_name);
                    }
                }
            }

            if(lot_names.includes(selectedLot.name)){
                value = true;
            }
            return value;
        },

        increase_product_lot_quantity: function(order, product, selectedLot){
            let orderlines = order.get_orderlines();
            for (var i = 0; i < orderlines.length; i++) {
                let orderline = order.get_orderlines().at(i);
                if(orderline.product.id == product.id){
                    let lot_names = [];
                    let lot_lines = orderline.get_lot_lines();
                    for(let lot_line of lot_lines){
                        lot_names.push(lot_line.attributes.lot_name);
                    }
                    if(lot_names.includes(selectedLot.name)){
                        orderline.set_quantity(orderline.get_quantity() + 1);
                        break;
                    }
                }
            }
        },

        add_product_original: async function(product, options){
            if(this._printed){
                this.destroy();
                return this.pos.get_order().add_product(product, options);
            }
            this.assert_editable();
            options = options || {};
            var line = new models.Orderline({}, {pos: this.pos, order: this, product: product});
            this.fix_tax_included_price(line);

            if(options.quantity !== undefined){
                line.set_quantity(options.quantity);
            }

            if(options.price !== undefined){
                line.set_unit_price(options.price);
                this.fix_tax_included_price(line);
            }

            if (options.price_extra !== undefined){
                line.price_extra = options.price_extra;
                line.set_unit_price(line.product.get_price(this.pricelist, line.get_quantity(), options.price_extra));
                this.fix_tax_included_price(line);
            }

            if(options.lst_price !== undefined){
                line.set_lst_price(options.lst_price);
            }

            if(options.discount !== undefined){
                line.set_discount(options.discount);
            }
            if(options.uom_id !== undefined){
                line.set_unit(options.uom_id);
            }

            if (options.description !== undefined){
                line.description += options.description;
            }

            if(options.extras !== undefined){
                for (var prop in options.extras) {
                    line[prop] = options.extras[prop];
                }
            }
            if (options.is_tip) {
                this.is_tipped = true;
                this.tip_amount = options.price;
            }

            var to_merge_orderline;
            for (var i = 0; i < this.orderlines.length; i++) {
                if(this.orderlines.at(i).can_be_merged_with(line) && options.merge !== false){
                    to_merge_orderline = this.orderlines.at(i);
                }
            }
            if (to_merge_orderline){
                to_merge_orderline.merge(line);
                this.select_orderline(to_merge_orderline);
            } else {
                this.orderlines.add(line);
                this.select_orderline(this.get_last_orderline());
            }

            if (options.draftPackLotLines) {
                this.selected_orderline.setPackLotLines(options.draftPackLotLines);
            }
            if (this.pos.config.iface_customer_facing_display) {
                this.pos.send_current_order_to_customer_facing_display();
            }
        },


        check_condition_apply_sale_limit_time: function(pos, pos_category) {
            if (pos_category.submit_all_pos) {
                return true
            } else {
                if (pos_category.pos_branch_ids.length) {
                    if (!pos.config.pos_branch_id) {
                        return true
                    } else {
                        return (pos_category.pos_branch_ids.indexOf(pos.config.pos_branch_id[0]) != -1)
                    }
                } else {
                    if (pos_category.pos_config_ids) {
                        return (pos_category.pos_config_ids.indexOf(pos.config.id) != -1)
                    } else {
                        return false
                    }
                }
            }
        },

        add_product: async function (product, options) {
            // NUMBER
            let order = this.pos.get_order();

            if(this.pos.config){
                // Product Lots/Serial Numbers
                if (['serial', 'lot'].includes(product.tracking)) {
                    if(options && options['draftPackLotLines'] === undefined){
                        let draftPackLotLines = [];
                        let packLotLinesToEdit = product.get_lots_available();
                        if(typeof packLotLinesToEdit == 'undefined' || packLotLinesToEdit.length == 0){
                            Gui.showPopup('ErrorPopup', { 
                                title: _t('Warning'),
                                body: _t("Product don't have Lots/Serial Numbers"),
                                confirmText: 'OK',
                                cancelText: ''
                            })
                            return false;
                        }
                        if(packLotLinesToEdit && packLotLinesToEdit.length) {
                            const lotList = packLotLinesToEdit.map(l => ({
                                id: l.id,
                                item: l,
                                label: l.name + _t(' Stock : ') + l.lot_qty_available + _t(', Expired Date: ') + (l.expiration_date || 'N/A')
                            }));
                            if(this.pos.config.fullfill_lots_type == 'auto'){
                                let selectedLot = [lotList[0]['item']];
                                let newPackLotLines = selectedLot.filter(item=>item.id).map(item=>({lot_name:item.name}));
                                let modifiedPackLotLines = selectedLot.filter(item=>!item.id).map(item=>({lot_name:item.text})); 

                                draftPackLotLines = {modifiedPackLotLines, newPackLotLines};
                                options['draftPackLotLines'] = draftPackLotLines;
                                // selectedOrder.add_product(product, {
                                //     draftPackLotLines,
                                //     price_extra: 0,
                                //     quantity: 1,
                                // });
                            }
                            if(this.pos.config.fullfill_lots_type == 'manual'){
                                let _cancelText = 'Close';
                                if(this.pos.config.create_lots){
                                    _cancelText = 'Close, Manual Input Lot Serial';
                                }
                                let {confirmed, payload: selectedLot} = await Gui.showPopup('SelectionPopup', {
                                    title: _t('Assign Lot/Serial for: ') + product.display_name + _t('. If you need Manual input, please click Close button'),
                                    list: lotList,
                                    cancelText: _t(_cancelText)
                                })
                                if (confirmed && selectedLot) {
                                    const newPackLotLines = [selectedLot].filter(item=>item.id).map(item=>({lot_name:item.name}));
                                    const modifiedPackLotLines = [selectedLot].filter(item=>!item.id).map(item=>({lot_name:item.text}));

                                    if (newPackLotLines.length != 1) {
                                        return this.pos.alert_message({
                                            title: _t('Error'),
                                            body: _t('Please select only Lot, and remove another Lots')
                                        })
                                    }

                                    draftPackLotLines = {modifiedPackLotLines, newPackLotLines};
                                    options['draftPackLotLines'] = draftPackLotLines;

                                    /** TODO: check if serial number exist in the Cart
                                     * If true then increase quantity
                                     * If false then don't merge
                                     */ 
                                    let is_exist_product_lot = this._is_exist_product_lot_in_cart(order, product, selectedLot);
                                    if(is_exist_product_lot){
                                        this.increase_product_lot_quantity(order, product, selectedLot);
                                        return;
                                    }else{
                                        options['merge'] = false;
                                    }

                                    // selectedOrder.add_product(product, {
                                    //     draftPackLotLines,
                                    //     price_extra: 0,
                                    //     quantity: 1,
                                    // })
                                } else {
                                    if(this.pos.config.create_lots){
                                        const {confirmed, payload} = await Gui.showPopup('EditListPopup', {
                                            title: _t('Lot/Serial Number(s) Required'),
                                            isSingleItem: false,
                                            array: packLotLinesToEdit,
                                        });
                                        if (confirmed) {
                                            const newPackLotLines = payload.newArray
                                                .filter(item => item.id)
                                                .map(item => ({lot_name: item.name}));
                                            const modifiedPackLotLines = payload.newArray
                                                .filter(item => !item.id)
                                                .map(item => ({lot_name: item.text}));
                                            if (newPackLotLines.length != 1) {
                                                return this.pos.alert_message({
                                                    title: _t('Error'),
                                                    body: _t('Please select only Lot, and remove another Lots')
                                                })
                                            }
                                            draftPackLotLines = {modifiedPackLotLines, newPackLotLines};
                                            options['draftPackLotLines'] = draftPackLotLines;
                                            // selectedOrder.add_product(product, {
                                            //     draftPackLotLines,
                                            //     price_extra: 0,
                                            //     quantity: 1,
                                            // })
                                        }else{
                                            return false;
                                        }
                                    }
                                    else{
                                        return false
                                    }
                                }
                            }
                        }
                    }
                }
            }


            let res = await this.add_product_original(product, options);
            let number = false
            let selected_orderline = this.get_selected_orderline();
            
            if('extras' in options && 'scanned_barcode' in  options.extras){
                let last_orderline = this.get_last_orderline();
                let curr_barcode = options.extras.scanned_barcode;
                selected_orderline.scanned_barcode = false
                last_orderline.scanned_barcode = false
                
                if(!selected_orderline.scanned_barcode){
                    last_orderline.scanned_barcode = curr_barcode
                }
                var to_merge_orderline = false;
                if(order.get_orderlines().length > 1){
                    for (var i = 0; i < this.orderlines.length; i++) {
                        if(order.get_orderlines().at(i).scanned_barcode == curr_barcode && order.get_orderlines().at(i).id != last_orderline.id){
                            to_merge_orderline = order.get_orderlines().at(i);
                        }
                    }
                }
                if (to_merge_orderline){
                    to_merge_orderline.merge(selected_orderline);
                    this.select_orderline(to_merge_orderline);
                    let curr_lines = this.pos.get_order().get_orderlines()
                    if(curr_lines.length > 1){
                        this.orderlines.remove(curr_lines[curr_lines.length-1]);
                    }
                } else {
                    selected_orderline.set_line_note(number)
                }
            }

            if (this.pos.config.required_ask_seat && !this.pos.config.iface_floorplan && !options['no_seatnumber'] ){
                let {confirmed, payload: number} = await this.pos.chrome.showPopup('NumberPopup', {
                    'title': _t('Please Input Seat Number'),
                    'startingValue': 0,
                    'isPassword': true,
                });
                if (confirmed) {
                    if (number > 0) {
                        if (selected_orderline){
                            selected_orderline.set_required_ask_seat('S'+number)
                        }
                    } else {
                        return this.pos.alert_message({
                            title: this.pos.env._t('Warning'),
                            body: this.pos.env._t('Required number bigger than 0')
                        })
                    }
                }
            }

            if (!options) {
                options = {}
            }
            if (!this.pos.config.allow_add_product) {
                return this.pos.alert_message({
                    title: this.pos.env._t('Alert'),
                    body: this.pos.env._t('Your POS Setting not active add products to cart')
                })
            }

            if (product && product['pos_categ_id']) {
                let pos_category = this.pos.pos_category_by_id[product['pos_categ_id'][0]];
                if (pos_category && pos_category.sale_limit_time) {
                    let can_apply = this.check_condition_apply_sale_limit_time(this.pos, pos_category);
                    if (can_apply) {
                        let limit_sale_from_time = pos_category.from_time;
                        let limit_sale_to_time = pos_category.to_time;
                        let date_now = new Date();
                        let current_time = date_now.getHours() + date_now.getMinutes() / 600;
                        if (current_time >= limit_sale_from_time && current_time <= limit_sale_to_time) {
                            return this.pos.alert_message({
                                title: this.pos.env._t('Warning'),
                                body: pos_category.name + _(': Blocked Sale this time !!!')
                            })
                        }
                    }
                }
            }

            let newDescription = []
            if (product.model_id) {
                newDescription.push(product['model_id'][1])
            }
            let extendDescription = newDescription.join('/');
            if (extendDescription != "") {
                options['description'] = options['description'] + extendDescription
            }


            let combo_items = [];
            if (selected_orderline) {
                // TODO: auto set hardcode combo items
                for (let i = 0; i < this.pos.combo_items.length; i++) {
                    let combo_item = this.pos.combo_items[i];
                    if (combo_item.product_combo_id[0] == selected_orderline.product.product_tmpl_id && (combo_item.default == true || combo_item.required == true)) {
                        combo_items.push(combo_item);
                    }
                }
                if (combo_items.length) {
                    selected_orderline.set_combo_bundle_pack(combo_items)
                    // TODO: auto set dynamic combo items
                    if (selected_orderline.product.product_tmpl_id) {
                        let default_combo_items = this.pos.combo_limiteds_by_product_tmpl_id[selected_orderline.product.product_tmpl_id];
                        if (default_combo_items && default_combo_items.length) {
                            let selected_combo_items = {};
                            for (let i = 0; i < default_combo_items.length; i++) {
                                let default_combo_item = default_combo_items[i];
                                if (default_combo_item.default_product_ids.length) {
                                    for (let j = 0; j < default_combo_item.default_product_ids.length; j++) {
                                        selected_combo_items[default_combo_item.default_product_ids[j]] = 1
                                    }
                                }
                            }
                            selected_orderline.set_dynamic_combo_items(selected_combo_items);
                        }

                    }
                    if (product.note_ids) {
                        let notes = '';
                        for (let i = 0; i < product.note_ids.length; i++) {
                            let note = this.pos.note_by_id[product.note_ids[i]];
                            if (!notes) {
                                notes = note.name
                            } else {
                                notes += ', ' + note.name;
                            }
                        }
                        if (notes) {
                            selected_orderline.set_line_note(notes)
                        }
                    }
                    if (product.tag_ids) {
                        selected_orderline.set_tags(product.tag_ids)
                    }
                }
            }

            
            if (selected_orderline && selected_orderline.product && selected_orderline.product.pos_categ_id) {
                const posCategory = this.pos.pos_category_by_id[selected_orderline.product.pos_categ_id[0]]
                if (posCategory && posCategory['category_type'] == 'main') {
                    selected_orderline.mp_dbclk_time = new Date().getTime();
                    selected_orderline.set_skip(true);
                }
            }
            
            return res
        },
        update_product_price: function (pricelist) {
            let self = this;
            let products = this.pos.db.getAllProducts();
            if (!products) {
                return;
            }
            for (let i = 0; i < products.length; i++) {
                let product = products[i];
                let price = product.get_price(pricelist, 1);
                product['price'] = price;
            }
            self.pos.trigger('product:change_price_list', products)
        },
        get_total_items: function () {
            let total_items = 0;
            for (let i = 0; i < this.orderlines.models.length; i++) {
                total_items += this.orderlines.models[i].quantity;
            }
            return total_items;
        },
        set_tags: function () {
            if (this && this.selected_orderline) {
                let selected_orderline = this.selected_orderline;
                return Gui.showPopup('popup_selection_tags', {
                    selected_orderline: selected_orderline,
                    title: this.pos.env._t('Add Tags')
                });
            } else {
                return this.pos.alert_message({
                    title: this.pos.env._t('Warning'),
                    body: this.pos.env._t('Your shopping cart is empty'),
                })
            }
        },
        async create_voucher() {
            let number = await this.pos._getVoucherNumber()
            const {confirmed, payload} = await Gui.showPopup('PopUpPrintVoucher', {
                title: _t('Create Voucher'),
                number: number,
                value: 0,
                period_days: this.pos.config.expired_days_voucher,
            });
            if (confirmed) {
                let values = payload.values;
                let error = payload.error;
                if (!error) {
                    let voucher = await rpc.query({
                        model: 'pos.voucher',
                        method: 'create_from_ui',
                        args: [[], values],
                        context: {}
                    })
                    let url_location = window.location.origin + '/report/barcode/EAN13/';
                    voucher['url_barcode'] = url_location + voucher['code'];
                    let report_html = qweb.render('VoucherCard', this.pos._get_voucher_env(voucher));
                    this.pos.chrome.showScreen('ReportScreen', {
                        report_html: report_html
                    });
                } else {
                    this.pos.alert_message({
                        title: _t('Alert'),
                        body: error,
                    })
                }
            }
        },
        manual_set_promotions: function () {
            let order = this;
            let promotion_manual_select = this.pos.config.promotion_manual_select;
            if (!promotion_manual_select) {
                order.apply_promotion()
            } else {
                let promotion_datas = order.get_promotions_active();
                let promotions_active = promotion_datas['promotions_active'];
                if (promotions_active.length) {
                    return Gui.showPopup('popup_selection_promotions', {
                        title: _t('Alert'),
                        body: _t('Please choice promotions need to apply'),
                        promotions_active: promotions_active
                    })
                } else {
                    return this.pos.alert_message({
                        title: _t('Warning'),
                        body: _t('Nothing Promotions active'),
                    })
                }

            }
        }, 
        
        create_sale_order: function () {
            let order = this;
            let length = order.orderlines.length;
            if (!order.get_client()) {
                return this.pos.show_popup_clients('products');
            }
            if (length == 0) {
                return this.pos.alert_message({
                    title: _t('Warning'),
                    body: _t('Your order is blank cart'),
                });
            }
            if (order.get_total_with_tax() <= 0) {
                return this.pos.alert_message({
                    title: _t('Warning'),
                    body: _t("Amount total of order required bigger than 0"),
                });
            }
            return Gui.showPopup('popup_create_sale_order', {
                title: _t('Create Quotation/Sale Order'),
            });
        },

        // TODO: Promotion
        get_promotions_active: function () {
            if (this.is_return) {
                return {
                    can_apply: false,
                    promotions_active: []
                };
            }
            let can_apply = null;
            let promotions_active = [];
            if (!this.pos.promotions) {
                return {
                    can_apply: can_apply,
                    promotions_active: []
                };
            }

            let current_date = moment(moment().utc().format('YYYY-MM-DD HH:mm:ss'), 'YYYY-MM-DD HH:mm:ss');

            for (let i = 0; i < this.pos.promotions.length; i++) {
                let promotion = this.pos.promotions[i];
                if (!this._checking_period_times_condition(promotion)) {
                    continue
                }

                if (promotion.start_date && promotion.end_date) {
                    let start_date = moment(promotion.start_date, 'YYYY-MM-DD HH:mm:ss');
                    let end_date = moment(promotion.end_date, 'YYYY-MM-DD HH:mm:ss');
                    if (!current_date.isAfter(start_date) || !current_date.isBefore(end_date)){
                        continue
                    }
                }

                let is_card_payment = this.checking_card_payment(promotion);
                let is_special_customer = this.checking_special_client(promotion);
                let is_birthday_customer = this.checking_promotion_birthday_match_birthdayof_client(promotion);
                let is_mem_of_promotion_group = this.checking_promotion_has_groups(promotion);
                if (promotion['type'] == '1_discount_total_order' && this.checking_apply_total_order(promotion) && is_card_payment && is_special_customer && is_birthday_customer && is_mem_of_promotion_group) {
                    can_apply = true;
                    promotions_active.push(promotion);
                } else if (promotion['type'] == '2_discount_category' && this.checking_can_discount_by_categories(promotion) && is_card_payment && is_special_customer && is_birthday_customer && is_mem_of_promotion_group) {
                    can_apply = true;
                    promotions_active.push(promotion);
                } else if (promotion['type'] == '3_discount_by_quantity_of_product' && this.checking_apply_discount_filter_by_quantity_of_product(promotion) && is_card_payment && is_special_customer && is_birthday_customer && is_mem_of_promotion_group) {
                    can_apply = true;
                    promotions_active.push(promotion);
                } else if (promotion['type'] == '4_pack_discount' && is_card_payment && is_special_customer && is_birthday_customer && is_mem_of_promotion_group) {
                    let promotion_condition_items = this.pos.promotion_discount_condition_by_promotion_id[promotion.id];
                    if (!promotion_condition_items) {
                        console.warn(promotion.name + 'have not rules');
                        continue
                    }
                    let checking_pack_discount_and_pack_free = this.checking_pack_discount_and_pack_free_gift(promotion, promotion_condition_items);
                    if (checking_pack_discount_and_pack_free) {
                        can_apply = true;
                        promotions_active.push(promotion);
                    }
                } else if (promotion['type'] == '5_pack_free_gift' && is_card_payment && is_special_customer && is_birthday_customer && is_mem_of_promotion_group) {
                    let promotion_condition_items = this.pos.promotion_gift_condition_by_promotion_id[promotion.id];
                    if (!promotion_condition_items) {
                        console.warn(promotion.name + 'have not rules');
                        continue
                    }
                    let checking_pack_discount_and_pack_free = this.checking_pack_discount_and_pack_free_gift(promotion, promotion_condition_items);
                    if (checking_pack_discount_and_pack_free) {
                        can_apply = checking_pack_discount_and_pack_free;
                        promotions_active.push(promotion);
                    }
                } else if (promotion['type'] == '6_price_filter_quantity' && this.checking_apply_price_filter_by_quantity_of_product(promotion) && is_card_payment && is_special_customer && is_birthday_customer && is_mem_of_promotion_group) {
                    can_apply = true;
                    promotions_active.push(promotion);
                } 


                else if (promotion['type'] == '7_special_category' && this.checking_apply_specical_category(promotion) && is_card_payment && is_special_customer && is_birthday_customer && is_mem_of_promotion_group) {
                    can_apply = true;
                    promotions_active.push(promotion);
                } 

                else if (promotion['type'] == '16_free_item_brands' && this.checking_apply_promotion_selected_brand(promotion) && is_card_payment && is_special_customer && is_birthday_customer && is_mem_of_promotion_group) {
                    can_apply = true;
                    promotions_active.push(promotion);
                } 

                else if (promotion['type'] == '8_discount_lowest_price' && is_card_payment && is_special_customer && is_birthday_customer && is_mem_of_promotion_group) {
                    can_apply = true;
                    promotions_active.push(promotion);
                } else if (promotion['type'] == '9_multi_buy' && is_card_payment && is_special_customer && is_birthday_customer && is_mem_of_promotion_group) {
                    let check_multi_by = this.checking_multi_buy(promotion);
                    if (check_multi_by) {
                        can_apply = check_multi_by;
                        promotions_active.push(promotion);
                    }
                } else if (promotion['type'] == '10_buy_x_get_another_free' && is_card_payment && this.checking_special_client(promotion) && this.checking_promotion_birthday_match_birthdayof_client(promotion) && is_mem_of_promotion_group) {
                    let check_by_x_get_another_free = this.checking_buy_x_get_another_free(promotion);
                    if (check_by_x_get_another_free) {
                        can_apply = check_by_x_get_another_free;
                        promotions_active.push(promotion);
                    }
                } else if (promotion['type'] == '11_first_order' && is_card_payment && this.checking_special_client(promotion) && this.checking_promotion_birthday_match_birthdayof_client(promotion) && is_mem_of_promotion_group) {
                    let can_apply_promotion = this.checking_first_order_of_customer(promotion);
                    if (can_apply_promotion) {
                        can_apply = can_apply_promotion;
                        promotions_active.push(promotion);
                    }
                } else if (promotion['type'] == '12_buy_total_items_free_items' && is_card_payment && this.checking_special_client(promotion) && this.checking_promotion_birthday_match_birthdayof_client(promotion) && is_mem_of_promotion_group) {
                    let product_ids = promotion.product_ids;
                    if (!product_ids || product_ids.length == 0) {
                        console.warn(promotion.name + ' product_ids not set');
                        continue
                    }
                    let can_apply_promotion = this.checking_buy_total_items_free_items(promotion);
                    if (can_apply_promotion) {
                        can_apply = can_apply_promotion;
                        promotions_active.push(promotion);
                    }
                } else if (promotion['type'] == '13_gifts_filter_by_total_amount' && is_card_payment && this.checking_special_client(promotion) && this.checking_promotion_birthday_match_birthdayof_client(promotion) && is_mem_of_promotion_group) {
                    let can_apply_promotion = this.checking_gifts_filter_by_total_amount(promotion);
                    if (can_apply_promotion) {
                        can_apply = can_apply_promotion;
                        promotions_active.push(promotion);
                    }
                } else if (promotion['type'] == '14_tebus_murah_by_total_amount' && is_card_payment && this.checking_special_client(promotion) && this.checking_promotion_birthday_match_birthdayof_client(promotion) && is_mem_of_promotion_group) {
                    let can_apply_promotion = this.checking_tebus_murah_by_total_amount(promotion);
                    if (can_apply_promotion) {
                        can_apply = can_apply_promotion;
                        promotions_active.push(promotion);
                    }
                } else if (promotion['type'] == '15_tebus_murah_by_specific_product' && is_card_payment && this.checking_special_client(promotion) && this.checking_promotion_birthday_match_birthdayof_client(promotion) && is_mem_of_promotion_group) {
                    let can_apply_promotion = this.checking_tebus_murah_by_specific_product(promotion);
                    if (can_apply_promotion) {
                        can_apply = can_apply_promotion;
                        promotions_active.push(promotion);
                    }
                } else if (promotion['type'] == '17_tebus_murah_by_selected_brand' && is_card_payment && this.checking_special_client(promotion) && this.checking_promotion_birthday_match_birthdayof_client(promotion) && is_mem_of_promotion_group) {
                    let can_apply_promotion = this.checking_tebus_murah_by_selected_brand(promotion);
                    if (can_apply_promotion) {
                        can_apply = can_apply_promotion;
                        promotions_active.push(promotion);
                    }
                }

            }
            return {
                can_apply: can_apply,
                promotions_active: promotions_active
            };
        },
        apply_promotion: async function (promotions) {
            var self = this;
            this.promotionRunning = true;
            if (this.is_return) {
                return true
            }
            if (!promotions) {
                promotions = this.get_promotions_active()['promotions_active'];
            }
            if (promotions.length) {
//                this.remove_all_promotion_line();
                let promotion_names = [];
                for (let i = 0; i < promotions.length; i++) {
                    let promotion = promotions[i]
                    let type = promotions[i].type
                    let order = this;
                    if (order.orderlines.length) {
                        if (type == '1_discount_total_order') {
                            order.compute_discount_total_order(promotion);
                        }
                        if (type == '2_discount_category') {
                            order.compute_discount_category(promotion);
                        }
                        if (type == '3_discount_by_quantity_of_product') {
                            order.compute_discount_by_quantity_of_products(promotion);
                        }
                        if (type == '4_pack_discount') {
                            order.compute_pack_discount(promotion);
                        }
                        if (type == '5_pack_free_gift') {
                            order.compute_pack_free_gift(promotion);
                        }
                        if (type == '6_price_filter_quantity') {
                            order.compute_price_filter_quantity(promotion);
                        }
                        if (type == '7_special_category') {
                            order.compute_special_category(promotion);
                        }
                        if (type == '8_discount_lowest_price') {
                            order.compute_discount_lowest_price(promotion);
                        }
                        if (type == '9_multi_buy') {
                            order.compute_multi_buy(promotion);
                        }
                        if (type == '10_buy_x_get_another_free') {
                           await order.compute_buy_x_get_another_free(promotion);
                        }
                        if (type == '11_first_order') {
                            order.compute_first_order(promotion);
                        }
                        if (type == '12_buy_total_items_free_items') {
                            order.compute_buy_total_items_free_items(promotion);
                        }
                        if (type == '13_gifts_filter_by_total_amount') {
                            order.compute_gifts_filter_by_total_amount(promotion);
                        }
                        if (type == '15_tebus_murah_by_specific_product') {
                            order.compute_tebus_murah_specific_product(promotion);
                        }
                        if (type == '16_free_item_brands') {
                            order.compute_gifts_free_item_brand(promotion);
                        }
                        if (type == '17_tebus_murah_by_selected_brand') {
                            order.compute_tebus_murah_brand(promotion);
                        }
                    }
                }
                let applied_promotion = false;
                let total_promotion_line = 0;
                for (let i = 0; i < this.orderlines.models.length; i++) {
                    if (this.orderlines.models[i]['promotion'] == true) {
                        applied_promotion = true;
                        total_promotion_line += 1;
                    }
                }
                this.trigger('change', this);
                this.promotionRunning = false;
            } else {
                this.promotionRunning = false;
                return this.pos.alert_message({
                    title: _t('Warning'),
                    body: _t('Have not any Promotions Active'),
                });
            }
        },

        // TODO: 14_tebus_murah_by_total_amount, 15_tebus_murah_by_specific_product
        select_promotion_tebus_murah: async function (promotion) {
            let items = [];
            if(this.pos.promotion_tebus_murah_product_by_promotion_id){
                if(this.pos.promotion_tebus_murah_product_by_promotion_id[promotion.id]){
                    items = this.pos.promotion_tebus_murah_product_by_promotion_id[promotion.id];
                    if(items && promotion.tebus_murah_product_ids){
                        items = items.filter((o)=> promotion.tebus_murah_product_ids.includes(o.id) == true);
                    } else {
                        items = [];
                    }
                }
            }
            if(!items.length){
                Gui.showPopup('ErrorPopup', {
                    title: _t('Error'),
                    body: _t('Configuration "Applied: Tebus Murah Products" is not set'),
                })
                return Promise.resolve(false);
            }
            let list = items.map( (i) => ({ label: i.product_id[1], item: i, id: i.id }) );
            let {confirmed, payload: selected} = await Gui.showPopup('SelectionPopup', {
                title: _t('Tebus Murah Product'),
                list: list,
            });
            if(confirmed){
                let product = this.pos.db.get_product_by_id(selected.product_id[0]);
                if (!product) {
                    Gui.showPopup('ConfirmPopup', {
                        title: _t('Warning'),
                        body: selected.product_id[1] + _t(' not available in POS, please sync Data'),
                        disableCancelButton: true,
                    });
                } else {
                    this.set_tebus_murah_product(product, selected.price, selected.quantity, {
                        promotion: true,
                        promotion_id: promotion.id,
                        promotion_gift: true,
                        promotion_reason: promotion.name
                    });
                }
                Promise.resolve(true);
            }
            Promise.resolve(false);
        },

        set_tebus_murah_product: function (product, price, quantity, options) {
            let line = new models.Orderline({}, {pos: this.pos, order: this.pos.get_order(), product: product});
            line.promotion = true;
            line.promotion_tebus_murah = true;
            
            if (options.promotion_id) {
                line.promotion_ids.push[options.promotion_id];
                line.promotion_id = options.promotion_id
            }
            if (options.buyer_promotion) {
                line.promotion = options.buyer_promotion;
            }
            if (options.promotion_reason) {
                line.promotion_reason = options.promotion_reason;
            }
            line.product.taxes_id = false
            line.price_manually_set = true; //no need pricelist change, price of promotion change the same, i blocked
            line.set_quantity(quantity);
            line.set_unit_price(price);
            line.price_manually_set = true;
            this.orderlines.add(line);
            this.pos.trigger('auto_update:paymentlines');
        },


        get_amount_total_without_promotion: function () {
            let lines = _.filter(this.orderlines.models, function (line) {
//                return !line['is_return'] && !line['promotion']
                return !line['is_return'] && !line['promotion_gift']
            });
            let amount_total = 0;
            for (let i = 0; i < lines.length; i++) {
                let line = lines[i];
                // if (this.pos.config.iface_tax_included === 'total') {
                //     amount_total += line.get_price_with_tax();
                // } else {
                    amount_total += line.get_price_without_tax();
                // }
            }
            return amount_total;
        },
        remove_all_buyer_promotion_line: function () {
            let lines = this.orderlines.models;
            for (let n = 0; n < 2; n++) {
                for (let i = 0; i < lines.length; i++) {
                    let line = lines[i];
                    if (line['buyer_promotion']) {
                        this.orderlines.remove(line);
                    }
                }
            }
        },
        remove_all_promotion_line: function () {
            if (this.is_return) {
                return true
            }
            let lines = this.orderlines.models;
            this.voucher_amount = 0
            for (let i = 0; i < lines.length; i++) {
                lines[i].discount = 0;
                lines[i].voucher_id = false
                lines[i].discount_other_promotion = {}
                let line = lines[i];
                if (line['promotion']) {
                    if (line.promotion && line.promotion_id && (line.promotion_discount || line.promotion_amount)) {
                        line.promotion = false;
                        line.promotion_id = null;
                        line.promotion_ids = [];
                        line.promotion_discount = null;
                        line.promotion_stack = {};
                        line.promotion_amount = null;
                        line.promotion_reason = null;
                        line.trigger('change', line)
                    } else {
                        this.orderlines.remove(line);
                    }
                }
                // else if (line['promotion_gift']) {
                //    this.orderlines.remove(line);
                // }
            }
            this.trigger('change', this);
        },

        is_promotion_fulfil_card_payment_condition: function(){
            let applied_promotion_ids = [];
            let promotions_active_ids = [];
            this.orderlines.models.forEach(l => {
                if(l.promotion_id){
                    applied_promotion_ids.push(parseInt(l.promotion_id));
                }
                if(l.promotion_stack){
                    for(let promotion_id in l.promotion_stack){
                        applied_promotion_ids.push(parseInt(promotion_id));
                    }
                }
            });
            if(applied_promotion_ids.length != 0){
                applied_promotion_ids = [... new Set(applied_promotion_ids)];
                let promotion_datas = this.get_promotions_active();
                if(promotion_datas && promotion_datas['promotions_active']){
                    promotions_active_ids = promotion_datas['promotions_active'].map(o=>parseInt(o.id));
                }
            }
            if(applied_promotion_ids.length != 0 && promotions_active_ids.length != 0){
                return applied_promotion_ids.every(id=>promotions_active_ids.includes(id));
            }
            return true;
        },

        product_quantity_by_product_id: function () {
            let lines_list = {};
            let lines = this.orderlines.models;
            let i = 0;
            while (i < lines.length) {
                let line = lines[i];
//                if (line.promotion) {
//                    i++;
//                    continue
//                }
                if(line.promotion_tebus_murah){
                    i++;
                    continue
                }
                if (!lines_list[line.product.id]) {
                    lines_list[line.product.id] = line.quantity;
                } else {
                    lines_list[line.product.id] += line.quantity;
                }
                i++;
            }
            return lines_list
        },
        total_quantity_only: function () {
            let lines_list = {};
            let lines = this.orderlines.models;
            let i = 0;
            var count = 0
            while (i < lines.length) {
                let line = lines[i];
                if(line.promotion_tebus_murah){
                    i++;
                    continue
                }
                count += line.quantity;
                i++;
            }
            return count
        },
        total_price_by_product_id: function () {
            let total_price_by_product = {};
            for (let i = 0; i < this.orderlines.models.length; i++) {
                let line = this.orderlines.models[i];
                // if (this.pos.config.iface_tax_included === 'total') {
                //     if (!total_price_by_product[line.product.id]) {
                //         total_price_by_product[line.product.id] = line.get_price_with_tax();
                //     } else {
                //         total_price_by_product[line.product.id] += line.get_price_with_tax();
                //     }
                // } else {
                    if (!total_price_by_product[line.product.id]) {
                        total_price_by_product[line.product.id] = line.get_price_without_tax();
                    } else {
                        total_price_by_product[line.product.id] += line.get_price_without_tax();
                    }
                // }
            }
            return total_price_by_product;
        },
        getCardPayment(){
            let order = this;
            if(order){
                if(order.selected_card_payment_id){
                    return this.pos.db.get_card_payment_by_id(order.selected_card_payment_id);
                }
            }
            return false;
        },
        checking_card_payment: function(promotion) {
            /* Checking card payment selected, if it applied in the promotion scheme */
            let card_payment = this.getCardPayment();
            if(promotion.card_payment_ids && promotion.card_payment_ids.length > 0){
                if(!card_payment){
                    return false;
                }
                if(!promotion.card_payment_ids.includes(card_payment.id)){
                    return false;
                }else{
                    return true
                }
            }
            return true;
        },
        checking_special_client: function (promotion) {
            /*
                Checking client selected have inside special customers of promotion
             */
            if (!promotion.special_customer_ids || promotion.special_customer_ids.length == 0) {
                return true
            } else {
                let order = this.pos.get_order();
                if (!order) {
                    return true
                } else {
                    let client = order.get_client();
                    if (!client && promotion.special_customer_ids.length) {
                        return false
                    } else {
                        let client_id = client.id;
                        if (promotion.special_customer_ids.indexOf(client_id) == -1) {
                            return false
                        } else {
                            return true
                        }
                    }
                }
            }
        },
        checking_promotion_birthday_match_birthdayof_client: function (promotion) {
            /*
                We checking 2 condition
                1. Promotion is promotion birthday
                2. Birthday of client isnide period time of promotion allow
             */
            if (!promotion.promotion_birthday) {
                return true
            } else {
                let client = this.get_client();
                let passed = false;
                if (client && client['birthday_date']) {
                    let today = moment(moment().utc().format('YYYY-MM-DD HH:mm:ss'));
                    let parts = client['birthday_date'].split('-');
                    let birthday_date = moment(new Date().getFullYear()+'-'+parts[1]+'-'+parts[0] +' 00:00:00', 'YYYY-MM-DD HH:mm:ss');
                    if (promotion['promotion_birthday_type'] == 'day') {
                        if ((birthday_date.date() == today.date()) && (birthday_date.month() == today.month())) {
                            passed = true;
                        }
                    }
                    if (promotion['promotion_birthday_type'] == 'week') {
                        let st_time = moment(moment().utc().subtract(7,'days').format('YYYY-MM-DD 00:00:00'));
                        let et_time = moment(moment().utc().add(7,'days').format('YYYY-MM-DD 00:00:00'));
                        if(birthday_date.isSameOrAfter(st_time) && birthday_date.isSameOrBefore(et_time)){
                            passed = true;
                        }
                    }
                    if (promotion['promotion_birthday_type'] == 'month') {
                        if (birthday_date.month() == today.month()) {
                            passed = true;
                        }
                    }
                }
                return passed;
            }
        },
        checking_promotion_has_groups: function (promotion) {
            /*
                Check If Customer is inside the membership type,
                If module (module: equip3_pos_membership) not installed then always return True
             */
            return true;
        },
        order_has_promotion_applied: function () {
            let promotion_line = _.find(this.orderlines.models, function (line) {
                return line.promotion == true;
            });
            if (promotion_line) {
                return true
            } else {
                return false
            }
        },

        checking_disc_apply_and_or: function (promotion,total_order,total_qty) {
            var can_apply = false
            let discount_apply_and_or = promotion.discount_apply_and_or
            if(total_order >= promotion.discount_apply_min_amount && total_qty >= promotion.discount_apply_min_qty && discount_apply_and_or=='And'){
                can_apply = true;
            }
            if((total_order >= promotion.discount_apply_min_amount || total_qty >= promotion.discount_apply_min_qty) && discount_apply_and_or=='Or'){
                can_apply = true;
            }


            return can_apply
        },

        checking_free_item_apply_and_or: function (promotion,total_order,total_qty) {
            var can_apply = false
            let free_item_apply_and_or = promotion.free_item_apply_and_or
            if(total_order >= promotion.free_item_apply_min_amount && total_qty >= promotion.free_item_apply_min_qty && free_item_apply_and_or=='And'){
                can_apply = true;
            }
            if((total_order >= promotion.free_item_apply_min_amount || total_qty >= promotion.free_item_apply_min_qty) && free_item_apply_and_or=='Or'){
                can_apply = true;
            }


            return can_apply
        },


        checking_tebus_murah_apply_and_or: function (promotion,total_order,total_qty) {
            var can_apply = false
            let tebus_murah_apply_and_or = promotion.tebus_murah_apply_and_or
            if(total_order >= promotion.tebus_murah_apply_min_amount && total_qty >= promotion.tebus_murah_apply_min_qty && tebus_murah_apply_and_or=='And'){
                can_apply = true;
            }
            if((total_order >= promotion.tebus_murah_apply_min_amount || total_qty >= promotion.tebus_murah_apply_min_qty) && tebus_murah_apply_and_or=='Or'){
                can_apply = true;
            }


            return can_apply
        },

        // 1) check current order can apply discount by total order
        checking_apply_total_order: function (promotion) {


            let can_apply = false;
            let total_order = this.get_amount_total_without_promotion();
            let total_qty = this.total_quantity_only()
            can_apply = this.checking_disc_apply_and_or(promotion,total_order,total_qty)
            return can_apply && this.checking_special_client(promotion);
            

        },
        // 2) check current order can apply discount by categories
        checking_can_discount_by_categories: function (promotion) {
            let can_apply = false;
            let product = this.pos.db.get_product_by_id(promotion.product_id[0]);
            if (!product || !this.pos.promotion_by_category_id) {
                return false;
            }


            var categ_with_qty = {}
            var categ_with_total= {}
            for (let order_line of this.orderlines.models) {
                let poscateg_id = order_line.product.pos_categ_id[0];
                if(poscateg_id in categ_with_qty){
                    categ_with_qty[poscateg_id]+=order_line.quantity
                    categ_with_total[poscateg_id]+=order_line.get_price_without_tax();
                }
                else{
                    categ_with_qty[poscateg_id] = order_line.quantity
                    categ_with_total[poscateg_id]=order_line.get_price_without_tax();
                }
            }
            for (let category_id in this.pos.promotion_by_category_id) {
                let promotion_line = this.pos.promotion_by_category_id[category_id];
                let amount_total_by_category = 0;
                let lines = _.filter(this.orderlines.models, function (line) {
                    return !line['is_return'] && !line['promotion_gift']
                });
                for(let line of lines){
                    let product = line.product;
                    if(product.pos_categ_id){
                        if(!categ_with_qty[product.pos_categ_id[0]]) {
                            continue
                        }
                        if (promotion_line.category_ids.includes(product.pos_categ_id[0])) {
                            amount_total_by_category += line.get_price_without_tax();
                        }
                    }
                }


                can_apply = this.checking_disc_apply_and_or(promotion,categ_with_total[category_id],categ_with_qty[category_id])
                if (can_apply){
                    break
                }
                
            }
            return can_apply && this.checking_special_client(promotion)
            
            
        },
        // 3_discount_by_quantity_of_product
        checking_apply_discount_filter_by_quantity_of_product: function (promotion) {
            let can_apply = false;
            let rules = this.pos.promotion_quantity_by_product_id;
            let product_quantity_by_product_id = this.product_quantity_by_product_id();
            let total_price_by_product_id = this.total_price_by_product_id()
            if (!product_quantity_by_product_id) {
                return false;
            }
            
            for (let product_id in product_quantity_by_product_id) {
                let rules_by_product_id = rules[product_id];
                if (rules_by_product_id) {
                    for (let i = 0; i < rules_by_product_id.length; i++) {
                        let rule = rules_by_product_id[i];
                        var condition = this.checking_disc_apply_and_or(promotion,total_price_by_product_id[product_id],product_quantity_by_product_id[product_id])
                        if(condition){
                            can_apply = true
                            break
                        }
                    
                            
                    }
                }
            }

            return can_apply && this.checking_special_client(promotion);
            
        },
        // 4. & 5. : check pack free gift and pack discount product
        // 5_pack_free_gift && 4_pack_discount
        checking_pack_discount_and_pack_free_gift: function (promotion, rules) {
            let method = promotion.method;
            let active_one = false;
            let can_apply = true;
            let product_quantity_by_product_id = this.product_quantity_by_product_id();
            for (let i = 0; i < rules.length; i++) {
                let rule = rules[i];
                let product_id = rule.product_id[0];
                let minimum_quantity = rule.minimum_quantity;
                let total_qty_by_product = product_quantity_by_product_id[product_id];
                if ((total_qty_by_product && total_qty_by_product < minimum_quantity) || !total_qty_by_product) {
                    can_apply = false;
                }
                if (total_qty_by_product && total_qty_by_product >= minimum_quantity) {
                    active_one = true;
                }
            }
            if (active_one && method == 'only_one') {
                return active_one && this.checking_special_client(promotion)
            } else {
                return can_apply && this.checking_special_client(promotion)
            }
        },
        // 6. check condition for apply price filter by quantity of product
        checking_apply_price_filter_by_quantity_of_product: function (promotion) {
            let condition = false;
            let rules = this.pos.promotion_price_by_promotion_id[promotion.id];
            let product_quantity_by_product_id = this.product_quantity_by_product_id();
            for (let i = 0; i < rules.length; i++) {
                let rule = rules[i];
                if (rule && product_quantity_by_product_id[rule.product_id[0]] && product_quantity_by_product_id[rule.product_id[0]] >= rule.minimum_quantity) {
                    condition = true;
                }
            }
            return condition && this.checking_special_client(promotion);
        },
        // TODO: 7_special_category
        checking_apply_specical_category: function (promotion) {
            let condition = false;
            
            let promotion_lines = this.pos.promotion_special_category_by_promotion_id[promotion['id']];
            if(promotion_lines && promotion.special_category_ids){
                promotion_lines = promotion_lines.filter((o)=> promotion.special_category_ids.includes(o.id) == true);
            } else {
                promotion_lines = [];
            }

            this.lines_by_category_id = {};
            var categ_with_qty = {}
            var categ_with_total= {}

            for (let i = 0; i < this.orderlines.models.length; i++) {
                let line = this.orderlines.models[i];
                let pos_categ_id = line['product']['pos_categ_id'][0];
                if (pos_categ_id) {
                    if (!this.lines_by_category_id[pos_categ_id]) {
                        this.lines_by_category_id[pos_categ_id] = [line]
                    } else {
                        this.lines_by_category_id[pos_categ_id].push(line)
                    }
                    if(pos_categ_id in categ_with_qty){
                        categ_with_qty[pos_categ_id]+=line.quantity
                        categ_with_total[pos_categ_id]+=line.get_price_without_tax();
                    }
                    else{
                        categ_with_qty[pos_categ_id] = line.quantity
                        categ_with_total[pos_categ_id]=line.get_price_without_tax();
                    }
                }
            }
            for (let i = 0; i < promotion_lines.length; i++) {
                let promotion_line = promotion_lines[i];
                let categ_id = promotion_line['category_id'][0];
                let total_quantity = 0;

                if (this.lines_by_category_id[categ_id] && this.checking_free_item_apply_and_or(promotion,categ_with_total[categ_id],categ_with_qty[categ_id])) {
                    condition = true;
                    break
                }
            }
            return condition && this.checking_special_client(promotion);
        },
        // TODO: 16_free_item_brands
        checking_apply_promotion_selected_brand: function (promotion) {
            let condition = false;
            let product_quantity_by_product_id = this.product_quantity_by_product_id();
            let total_price_by_product_id = this.total_price_by_product_id();
            if(!this.pos.promotion_selected_brands){
                return true
            }

            let promotion_lines = this.pos.promotion_selected_brands[promotion['id']];
            if(promotion_lines && promotion.promotion_based_on_brand_ids){
                promotion_lines = promotion_lines.filter((o)=> promotion.promotion_based_on_brand_ids.includes(o.id) == true);
            } else {
                promotion_lines = [];
            }
            if(!promotion_lines){
                return true
            }

            this.lines_by_brand_id = {};
            for (let i = 0; i < this.orderlines.models.length; i++) {
                let line = this.orderlines.models[i];
                var brand_ids = line['product']['product_brand_ids'];
                if (brand_ids) {
                    for (let o = 0; o < brand_ids.length; o++) {
                        var brand_id = brand_ids[o]
                        if (!this.lines_by_brand_id[brand_id]) {
                            this.lines_by_brand_id[brand_id] = [line]
                        } else {
                            if(this.lines_by_brand_id[brand_id].filter((a) => a.cid == line.cid).length==0){
                                this.lines_by_brand_id[brand_id].push(line)
                            }
                        }
                    }
                }
            }
            for (let i = 0; i < promotion_lines.length; i++) {
                let promotion_line = promotion_lines[i];
                var brand_ids = promotion_line['brand_ids'];
                var gift_based_on = promotion_line['gift_based_on'];
                var min_amount_qty = promotion_line['min_amount_qty'];
                for (let o = 0; o < brand_ids.length; o++) {
                    var brand_id = brand_ids[o]
                    if(! this.lines_by_brand_id[brand_id]){
                        continue
                    }
                    var qty_product = 0
                    var subtotal = 0
                    for (let l = 0; l < this.lines_by_brand_id[brand_id].length; l++) {
                        var line = this.lines_by_brand_id[brand_id][l]
                        var product = line.product
                        qty_product += product_quantity_by_product_id[product.id]
                        subtotal += total_price_by_product_id[product.id]
                    }
                    if(this.checking_free_item_apply_and_or(promotion,subtotal,qty_product)) {
                        condition = true;
                        break
                    }
                }
            }
            return condition && this.checking_special_client(promotion);
        },
        // TODO: 9_multi_buy
        checking_multi_buy: function (promotion) {
            let can_apply = false;
            if(this.pos.multi_buy_by_promotion_id){
                const rules = this.pos.multi_buy_by_promotion_id[promotion.id];
                const total_qty_by_product = this.product_quantity_by_product_id();
                if (rules) {
                    for (let i = 0; i < rules.length; i++) {
                        let rule = rules[i];
                        let product_ids = rule.product_ids;
                        let total_qty_exist = 0;
                        for (let index in product_ids) {
                            let product_id = product_ids[index];
                            if (total_qty_by_product[product_id]) {
                                total_qty_exist += total_qty_by_product[product_id]
                            }
                        }
                        if (total_qty_exist >= rule['qty_apply']) {
                            can_apply = true;
                            break
                        }
                    }
                }
            }
            return can_apply && this.checking_special_client(promotion);
        },
        // TODO: 10_buy_x_get_another_free
        checking_buy_x_get_another_free: function (promotion) {
            let can_apply = false;
            if(!promotion.is_multi_level_promotion){
                let minimum_items = promotion['minimum_items'];
                let total_quantity = this.product_quantity_by_product_id();
                let total_price_by_product_id = this.total_price_by_product_id();
                if(this.pos.promotion_specific_product_by_promotion_id){
                    let promotion_lines = this.pos.promotion_specific_product_by_promotion_id[promotion['id']];
                    if(promotion_lines && promotion.promotion_specific_product_ids){
                        promotion_lines = promotion_lines.filter((o)=> promotion.promotion_specific_product_ids.includes(o.id) == true);
                    } else {
                        promotion_lines = [];
                    }
                    if(promotion_lines){
                        for (let i = 0; i < promotion_lines.length; i++) {
                            let line = promotion_lines[i]
                            let product_id = line.product_id[0];
                            if (total_quantity[product_id] && this.checking_free_item_apply_and_or(promotion,total_price_by_product_id[product_id],total_quantity[product_id])) {
                                let product = this.pos.db.product_by_id[product_id];
                                if (product) {
                                    can_apply = true;
                                    break
                                }
                            }
                        }
                    }
                }
            }else{
                if(this.pos.promotion_multilevel_condition_by_promotion_id){
                    let total_order = this.get_amount_total_without_promotion();
                    let total_qty = this.total_quantity_only();
                    can_apply = this.checking_free_item_apply_and_or(promotion,total_order,total_qty);
                    if(can_apply){
                        let conditions = this.pos.promotion_multilevel_condition_by_promotion_id[promotion['id']];
                        if(conditions && promotion.multilevel_condition_ids){
                            conditions = conditions.filter((o)=> promotion.multilevel_condition_ids.includes(o.id) == true);
                        } else {
                            conditions = [];
                        }
                        if(conditions){
                            let condition_fulfilled = []; 
                            let lines = _.filter(this.orderlines.models, function (line) {
                                return !line['is_return'] && !line['promotion_gift']
                            });
                            if(lines.length == 0){
                                condition_fulfilled.push(false);
                            }
                            for(let c of conditions){
                                let check_line = lines.filter(o=>o.quantity >= c.minimum_quantity && o.product.id == c.product_id[0]);
                                if(check_line.length){
                                    condition_fulfilled.push(true);
                                }else{
                                    condition_fulfilled.push(false);
                                }
                            }
                            can_apply = condition_fulfilled.length?condition_fulfilled.every(o=>o===true):false;
                        }
                    }
                }
            }
            return can_apply && this.checking_special_client(promotion);
        },
        // TODO: 11_first_order
        checking_first_order_of_customer: function (promotion) {
            let order;
            if (this.get_client()) {
                let client = this.get_client();
                order = _.filter(this.pos.db.get_pos_orders(), function (order) {
                    return order.partner_id && order.partner_id[0] == client['id']
                });
                if (order.length == 0) {
                    return true && this.checking_special_client(promotion)
                } else {
                    return false && this.checking_special_client(promotion)
                }
            } else {
                return false && this.checking_special_client(promotion)
            }
        },
         // TODO: 1_discount_total_order
        compute_discount_total_order: function (promotion) {
            let lines = _.filter(this.orderlines.models, function (line) {
                        return !line['is_return'] && !line['promotion_gift']
                    });
            let promotion_reason = promotion.name;
            if (promotion.new_type!='Discount Fixed Amount') {

                let discount_lines = this.pos.promotion_discount_order_by_promotion_id[promotion.id];
                if(discount_lines && promotion.discount_order_ids){
                    discount_lines = discount_lines.filter((o)=> promotion.discount_order_ids.includes(o.id) == true);
                } else {
                    discount_lines = [];
                }

                let total_order = this.get_amount_total_without_promotion();
                var discount_line = false
                for (let i = 0; i < discount_lines.length; i++) {
                    discount_line = discount_lines[i];
                    break
                }
                if(discount_line){

                    var disc = discount_line.discount
                    var real_total = 0
                    for(let line of lines){
                        if(line.is_product_coupon){
                            continue;
                        }
                        real_total+=line.get_real_total_w_discount();
                    }
                    var amount_disc = real_total * (disc/100);
                    var total_discount = amount_disc


                    if (total_discount > discount_line.max_discount_amount && discount_line.max_discount_amount) {
                        amount_disc = discount_line.max_discount_amount ;
                        disc = (amount_disc/ real_total) * 100
                    }
                    else{
                        disc = (total_discount/ real_total) * 100
                    }


                    for (let i = 0; i < lines.length; i++) {
                        let line = lines[i];
                        if(disc>100) {
                            disc=100
                        } 
                        this._apply_promotion_to_orderlines([line], promotion.id, promotion_reason, 0, disc)
                    }
                }
            }
            else{
                var fixed_amount = promotion.discount_fix_amount_all_product 
                var disc = fixed_amount
                var real_total = 0
                for(let line of lines){
                    if(line.is_product_coupon){
                        continue;
                    }
                    real_total+=line.get_real_total_w_discount();
                }
                if(fixed_amount) {
                    disc = fixed_amount
                    disc=(disc/ real_total) * 100

                }
                for (let i = 0; i < lines.length; i++) {
                    let line = lines[i];
                    if(disc>100) {
                        disc=100
                    } 
                    this._apply_promotion_to_orderlines([line], promotion.id, promotion_reason, 0, disc)
                }
            }
            this.pos.chrome.showNotification(_t('Promotion Program: ') + promotion['name'], _t(' Applied to Order!!!'))
        },
        //TODO: 12_buy_total_items_free_items
        checking_buy_total_items_free_items: function (promotion) {
            let total_items_ofRules_inCart = 0;
            let product_quantity_by_product_id = this.product_quantity_by_product_id();
            for (let i = 0; i < promotion.product_ids.length; i++) {
                let product_id = promotion.product_ids[i];
                let total_qty_by_product = product_quantity_by_product_id[product_id];
                if (total_qty_by_product) {
                    total_items_ofRules_inCart += total_qty_by_product
                }
            }
            if (total_items_ofRules_inCart && total_items_ofRules_inCart >= promotion.minimum_items) {
                return true && this.checking_special_client(promotion)
            } else {
                return false && this.checking_special_client(promotion)
            }
        },
        //TODO: 13_gifts_filter_by_total_amount
        checking_gifts_filter_by_total_amount: function (promotion) {
            let total_order = this.get_amount_total_without_promotion();
            let total_qty = this.total_quantity_only()
            let can_apply = this.checking_free_item_apply_and_or(promotion,total_order,total_qty);
            return can_apply && this.checking_special_client(promotion)
            
        },
        //TODO: 14_tebus_murah_by_total_amount
        checking_tebus_murah_by_total_amount: function (promotion) {
            let tebus_murah_total_order_apply_and_or = promotion.tebus_murah_total_order_apply_and_or
            let total_order = this.get_amount_total_without_promotion();
            let total_qty = this.total_quantity_only()
            let can_apply = false;
            if(total_order >= promotion.amount_total && total_qty >= promotion.tebus_murah_total_order_min_qty && tebus_murah_total_order_apply_and_or=='And'){
                can_apply = true;
            }
            if((total_order >= promotion.amount_total || total_qty >= promotion.tebus_murah_total_order_min_qty) && tebus_murah_total_order_apply_and_or=='Or'){
                can_apply = true;
            }
            return can_apply && this.checking_special_client(promotion);
        },
        //TODO: 15_tebus_murah_by_specific_product
        checking_tebus_murah_by_specific_product: function (promotion) { 
            let can_apply = false;
            let product_quantity_by_product_id = this.product_quantity_by_product_id();
            let total_price_by_product_id = this.total_price_by_product_id();
            if(this.pos.promotion_tebus_murah_product_by_promotion_id){

                let items = this.pos.promotion_tebus_murah_product_by_promotion_id[promotion.id];
                if(items && promotion.tebus_murah_product_ids){
                    items = items.filter((o)=> promotion.tebus_murah_product_ids.includes(o.id) == true);
                } else {
                    items = [];
                }

                if(items){
                    for (let item of items) {
                        var t_qty = 0
                        var t_price = 0
                        var fulfill_condition_product = false;
                        for (let order_line of this.orderlines.models) {
                            if(item.product_ids.includes(order_line.product.id)){
                                t_qty+=product_quantity_by_product_id[order_line.product.id]
                                t_price+=total_price_by_product_id[order_line.product.id]
                                fulfill_condition_product = true
                            }
                        }
                        if(fulfill_condition_product){
                            can_apply = this.checking_tebus_murah_apply_and_or(promotion,t_price,t_qty)
                            if(can_apply){
                                break;
                            }
                        }
                    }
                }
            }
            return can_apply && this.checking_special_client(promotion);
        },
        //TODO: 17_tebus_murah_by_selected_brand
        checking_tebus_murah_by_selected_brand: function (promotion) { 
            let can_apply = false;
            let tebus_murah_brand_ids = promotion.tebus_murah_brand_ids
            let min_amount = promotion.tebus_murah_brand_min_amount
            let min_qty = promotion.tebus_murah_brand_min_qty
            let tebus_murah_selected_brand_apply_and_or = promotion.tebus_murah_selected_brand_apply_and_or
            var promotion_tebus_murah_selected_brands = this.pos.promotion_tebus_murah_selected_brands;
            if(!promotion_tebus_murah_selected_brands){
                return false;
            }

            if(!tebus_murah_brand_ids || ! promotion.id in promotion_tebus_murah_selected_brands){
                return false
            }

            let product_quantity_by_product_id = this.product_quantity_by_product_id();
            let total_price_by_product_id = this.total_price_by_product_id();
            var t_qty = 0
            var t_price = 0
            for (let order_line of this.orderlines.models) {
                var brand_ids = order_line['product']['product_brand_ids'];
                if (brand_ids) {
                    for (let o = 0; o < brand_ids.length; o++) {
                        var brand_id = brand_ids[o]
                        if(tebus_murah_brand_ids.includes(brand_id)){
                            t_qty+=product_quantity_by_product_id[order_line['product']['id']]
                            t_price+=total_price_by_product_id[order_line['product']['id']]
                            break
                        }
                    }
                }
            }
            var min_amount_success = false
            var min_qty_success = false
            if(t_price >= min_amount){
                min_amount_success = true
            }
            if(t_qty >= min_qty){
                min_qty_success = true
            }
            if(tebus_murah_selected_brand_apply_and_or=='And' && min_qty_success && min_amount_success ){
                can_apply = true
            }
            if(tebus_murah_selected_brand_apply_and_or=='Or' && (min_qty_success || min_amount_success) ){
                can_apply = true
            }
            return can_apply && this.checking_special_client(promotion);
        },

        // TODO: 2_discount_category
        compute_discount_category: function (promotion) {
            let product = this.pos.db.get_product_by_id(promotion.product_id[0]);
            if (!product || !this.pos.promotion_by_category_id || !this.pos.pos_disc_categ_new[promotion.id]) {
                return false;
            }
            var categ_with_qty = {}
            var categ_with_total = {}
            for (let order_line of this.orderlines.models) {
                if(!order_line.product.pos_categ_id){
                    continue
                }
                let poscateg_id = order_line.product.pos_categ_id[0];
                if(poscateg_id in categ_with_qty){
                    categ_with_qty[poscateg_id]+=order_line.quantity
                    categ_with_total[poscateg_id]+=order_line.get_price_without_tax();
                }
                else{
                    categ_with_qty[poscateg_id] = order_line.quantity
                    categ_with_total[poscateg_id] =order_line.get_price_without_tax();
                }
            }
            var already_promo_fixed = []

            let lines = _.filter(this.orderlines.models, function (line) {
                return !line['is_return'] && !line['promotion_gift']
            });
            
            let discount_categs = this.pos.pos_disc_categ_new[promotion.id];
            if(discount_categs){
                discount_categs = discount_categs.filter((o)=> promotion.discount_category_ids.includes(o.id) == true);
            } else {
                discount_categs = [];
            }
            
            for (let categ_child of discount_categs) {
                let rule = categ_child;
                if (promotion.new_type!='Discount Fixed Amount') {
                    var disc = 0
                    var real_total = 0
                    for (var il = 0; il < lines.length; il++) {
                        let line = lines[il];
                        let pos_categ_id = line.product.pos_categ_id;
                        if(!rule.category_ids.includes(pos_categ_id[0])){
                            continue
                        }
                        if(already_promo_fixed.includes(pos_categ_id[0])){
                            continue
                        }
                        if(!categ_with_qty[pos_categ_id[0]] || categ_with_qty[pos_categ_id[0]] < rule.min_qty) {
                            continue
                        }
                        var line1 = lines[il];
                        real_total+=line1.get_real_total_w_discount()
                    }
                }

                for (let line of this.orderlines.models) {
                    let pos_categ_id = line.product.pos_categ_id;

                    var can_apply = this.checking_disc_apply_and_or(promotion,categ_with_total[pos_categ_id[0]],categ_with_qty[pos_categ_id[0]])
                    if(!can_apply){
                        continue
                    }
                    
                    if(!rule.category_ids.includes(pos_categ_id[0])){
                        continue
                    }
                    if(already_promo_fixed.includes(pos_categ_id[0])){
                        continue
                    }
                    if(!categ_with_qty[pos_categ_id[0]]) {
                        continue
                    }
                    let promotion_reason = 'Category: ' + pos_categ_id[1];
                    let promotion_discount = rule.discount;
                    if (promotion.new_type=='Discount Fixed Amount') {
                        var disc = 0
                        var fixed_amount = rule.discount_fixed_amount      
                        if(fixed_amount) {
                            disc = fixed_amount
                            var company_pos = this.pos.company
                            var tax_discount_policy = company_pos.tax_discount_policy
                            // if(tax_discount_policy != 'untax'){
                            //     disc=((disc * line.quantity)/ line.get_price_without_tax()) * 100
                            // }
                            // else {
                                disc=(disc /line.get_real_total_w_discount()) * 100
                            // }

                        }
                        if(disc>100) {
                            disc=100
                        } 
                        this._apply_promotion_to_orderlines([line], promotion.id, promotion_reason, 0, disc)
                        already_promo_fixed.push(pos_categ_id[0])
                        break
                    }
                    else{
                        var discount_line = rule
                        var disc = discount_line.discount
                        var amount_disc = real_total * (disc/100);
                        var total_discount = amount_disc
             
                        if (total_discount > discount_line.max_discount_amount && discount_line.max_discount_amount) {
                            amount_disc = discount_line.max_discount_amount ;
                            disc = (amount_disc/ real_total) * 100
                        }
                        else{
                            disc = (total_discount/ real_total) * 100
                        }

                        this._apply_promotion_to_orderlines([line], promotion.id, promotion_reason, 0, disc)
                    }
                    
                }
            }
        
            this.pos.chrome.showNotification(_t('Promotion Program: ') + promotion['name'], _t(' Applied to Order!!!'))
        },
        // TODO: 3_discount_by_quantity_of_product
        compute_discount_by_quantity_of_products: function (promotion) {
            let quantity_by_product_id = this.product_quantity_by_product_id();
            let total_price_by_product_id = this.total_price_by_product_id()
            let orderlines = this.orderlines.models;
            for (let product_id in quantity_by_product_id) {

                let promotion_lines = this.pos.promotion_quantity_by_product_id[product_id];
                if(!promotion_lines){
                    continue;
                }
                if(promotion_lines && promotion.discount_quantity_ids){
                    promotion_lines = promotion_lines.filter((o)=> promotion.discount_quantity_ids.includes(o.id) == true);
                } else {
                    promotion_lines = [];
                }
                if(!promotion_lines.length){
                    continue;
                }

                let quantity_tmp = 0;
                let apply_promotion_line = null;
                for (let index in promotion_lines) {
                    let promotion_line = promotion_lines[index]

                    var condition = this.checking_disc_apply_and_or(promotion,total_price_by_product_id[product_id],quantity_by_product_id[product_id])
                    
                    var condition2 = promotion_line['product_ids'].includes(parseInt(product_id)) && promotion_line['promotion_id'][0] == promotion['id'];
                    if (condition && condition2) {
                        apply_promotion_line = promotion_line;
                        quantity_tmp = promotion_line.quantity
                    }
                }

                if (apply_promotion_line) {
                    let orderlines_promotion = _.filter(orderlines, function (orderline) {
                        return apply_promotion_line.product_ids.includes(orderline.product.id);
                    });
                    if (promotion.new_type!='Discount Fixed Amount' && orderlines_promotion) {
                        var disc = 0
                        var real_total = 0
                        for(let line of orderlines_promotion){
                            if(line.is_product_coupon){
                                continue;
                            }
                            real_total+=line.get_real_total_w_discount();
                        }

                        disc = apply_promotion_line.discount
                        var amount_disc = real_total * (disc/100);
                        var total_discount = amount_disc

                        if (total_discount > apply_promotion_line.max_discount_amount && apply_promotion_line.max_discount_amount) {
                            amount_disc = apply_promotion_line.max_discount_amount ;
                            disc = (amount_disc/ real_total) * 100
                        }
                        else{
                            disc = (total_discount/ real_total) * 100
                        }
                    }
                    if (orderlines_promotion) {
                        let promotion_reason = apply_promotion_line.name ;
                        let promotion_discount = apply_promotion_line.discount;
                        for (let i = 0; i < orderlines_promotion.length; i++) {
                            let line = orderlines_promotion[i];

                            if (promotion.new_type=='Discount Fixed Amount') {
                                var disc = 0
                                var fixed_amount = apply_promotion_line.discount_fixed_amount        
                                if(fixed_amount) {
                                    disc = fixed_amount
                                    var company_pos = this.pos.company
                                    var tax_discount_policy = company_pos.tax_discount_policy
                                    disc=(disc /line.get_real_total_w_discount()) * 100

                                }
                                if(disc>100) {
                                    disc=100
                                } 
                                this._apply_promotion_to_orderlines([line], promotion.id, promotion_reason, 0, disc)
                                break
                            }
                            else{
                                this._apply_promotion_to_orderlines([line], promotion.id, promotion_reason, 0, disc)
                            }
                                

                            
                        }
                    }
                }
            }
            this.pos.chrome.showNotification(_t('Promotion Program: ') + promotion['name'], _t(' Applied to Order!!!'))
        },
        count_quantity_by_product: function (product) {
            /*
                Function return total qty filter by product of order
            */
            let qty = 0;
            for (let i = 0; i < this.orderlines.models.length; i++) {
                let line = this.orderlines.models[i];
                if (line.product['id'] == product['id']) {
                    qty += line['quantity'];
                }
            }
            return qty;
        },
        // TODO: 4_pack_discount
        compute_pack_discount: function (promotion) {
            let discount_items = this.pos.promotion_discount_apply_by_promotion_id[promotion.id];
            if (!discount_items) {
                return;
            }
            let lines = _.filter(this.orderlines.models, function (line) {
//                return !line['is_return'] && !line['promotion']
                return !line['is_return'] && !line['promotion_gift']
            });
            for (let n = 0; n < discount_items.length; n++) {
                let discount_item = discount_items[n];
                for (let i = 0; i < lines.length; i++) {
                    let line = lines[i];
                    if (line.product.id == discount_item.product_id[0]) {
                        let promotion_reason = promotion.name;
                        let promotion_discount = discount_item.discount;

                        if (promotion.new_type=='Discount Fixed Amount') {
                            var disc = 0
                            var fixed_amount = discount_item.discount_fixed_amount       
                            if(fixed_amount) {
                                disc = fixed_amount
                                var company_pos = this.pos.company
                                var tax_discount_policy = company_pos.tax_discount_policy
                                // if(tax_discount_policy != 'untax'){
                                //     disc=((disc * line.quantity)/ line.get_price_without_tax()) * 100
                                // }
                                // else {
                                    disc=(disc/line.get_real_total_w_discount()) * 100
                                // }

                            }
                            if(disc>100) {
                                disc=100
                            } 
                            this._apply_promotion_to_orderlines([line], promotion.id, promotion_reason, 0, disc)
                        }
                        else{
                            this._apply_promotion_to_orderlines([line], promotion.id, promotion_reason, 0, promotion_discount);
                        }
                    }
                }
            }
            this.pos.chrome.showNotification(_t('Promotion Program: ') + promotion['name'], _t(' Applied to Order!!!'))
        },
        // TODO: 5_pack_free_gift
        compute_pack_free_gift: async function (promotion) {
            let gifts = this.pos.promotion_gift_free_by_promotion_id[promotion.id];
            if (!gifts) {
                console.warn('gifts not found');
                return;
            }
            let condition_items = this.pos.promotion_gift_condition_by_promotion_id[promotion.id];
            let max_qty_of_gift = null;
            let min_qty_of_condition = null;
            let current_qty = null;
            var product = false
            for (let i = 0; i < condition_items.length; i++) {
                let condition_item = condition_items[i];
                if (!min_qty_of_condition) {
                    min_qty_of_condition = condition_item.minimum_quantity;
                }
                if (min_qty_of_condition && min_qty_of_condition >= condition_item.minimum_quantity) {
                    min_qty_of_condition = condition_item.minimum_quantity
                }
                product = this.pos.db.get_product_by_id(condition_item.product_id[0]);
                if (product) {
                    let total_qty = this.count_quantity_by_product(product);
                    if (total_qty) {
                        if (!current_qty) {
                            current_qty = total_qty
                        }
                        if (promotion.method == 'only_one') {
                            if (current_qty && total_qty >= current_qty) {
                                current_qty = total_qty
                            }
                        } else {
                            if (current_qty && total_qty <= current_qty) {
                                current_qty = total_qty
                            }
                        }

                    }
                }
            }
            if (min_qty_of_condition == 0) {
                min_qty_of_condition = 1
            }

            // TODO: buy min_qty_of_condition (A) will have max_qty_of_gift (B)
            // TODO: buy current_qty (C) will have X (qty): x = C / A * B
            let temp = parseInt(current_qty / min_qty_of_condition);
            if (temp == 0) {
                temp = 1;
            }
            await this.set_product_free_gift(promotion,product,1)

        },
        // TODO: 6_price_filter_quantity
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
                for (i in quantity_by_product_id) {
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
//                                return !line['is_return'] && !line['promotion'] && line.product.id == price_item_tmp.product_id[0];
                                return !line['is_return'] && !line['promotion_gift'] && line.product.id == price_item_tmp.product_id[0];
                            });
                            let promotion_reason = promotion.name;
                            let promotion_amount = promotion_amount || 0.0;
                            promotion_amount += price_item_tmp.price_down;
                            this._apply_promotion_to_orderlines(lines, promotion.id, promotion_reason, promotion_amount, 0);
                        }
                    }
                }
            }
            this.pos.chrome.showNotification(_t('Promotion Program: ') + promotion['name'], _t(' Applied to Order!!!'))
        },



        // TODO: 16_free_item_brands
        compute_gifts_free_item_brand: async function (promotion) {
            let product_quantity_by_product_id = this.product_quantity_by_product_id();
            let total_price_by_product_id = this.total_price_by_product_id();

            let promotion_lines = this.pos.promotion_selected_brands[promotion['id']];
            if(promotion_lines && promotion.promotion_based_on_brand_ids){
                promotion_lines = promotion_lines.filter((o)=> promotion.promotion_based_on_brand_ids.includes(o.id) == true);
            } else {
                promotion_lines = [];
            }

            this.lines_by_brand_id = {};
            for (let i = 0; i < this.orderlines.models.length; i++) {
                let line = this.orderlines.models[i];
                var brand_ids = line['product']['product_brand_ids'];
                if (brand_ids) {
                    for (let o = 0; o < brand_ids.length; o++) {
                        var brand_id = brand_ids[o]
                        if (!this.lines_by_brand_id[brand_id]) {
                            this.lines_by_brand_id[brand_id] = [line]
                        } else {
                            if(this.lines_by_brand_id[brand_id].filter((a) => a.cid == line.cid).length==0){
                                this.lines_by_brand_id[brand_id].push(line)
                            }
                        }
                    }
                }
            }
            for (let i = 0; i < promotion_lines.length; i++) {
                let promotion_line = promotion_lines[i];
                var brand_ids = promotion_line['brand_ids'];
                var gift_based_on = promotion_line['gift_based_on'];
                var min_amount_qty = promotion_line['min_amount_qty'];
                for (let o = 0; o < brand_ids.length; o++) {
                    var brand_id = brand_ids[o]
                    if(! this.lines_by_brand_id[brand_id]){
                        continue
                    }
                    var qty_product = 0
                    var subtotal = 0
                    var line = false
                    for (let l = 0; l < this.lines_by_brand_id[brand_id].length; l++) {
                        line = this.lines_by_brand_id[brand_id][l]
                        var product = line.product
                        qty_product += product_quantity_by_product_id[product.id]
                        subtotal += total_price_by_product_id[product.id]
                    }
                    if(line){
                        if(this.checking_free_item_apply_and_or(promotion,subtotal,qty_product)) {
                            await this.set_brand_product_free_gift(promotion,promotion_line,line) 
                            break
                        }
                    }
                }
            }

        },

        // TODO: 7_special_category
        compute_special_category: async function (promotion) {
            let promotion_lines = this.pos.promotion_special_category_by_promotion_id[promotion['id']];
            if(promotion_lines && promotion.special_category_ids){
                promotion_lines = promotion_lines.filter((o)=> promotion.special_category_ids.includes(o.id) == true);
            } else {
                promotion_lines = [];
            }

            this.lines_by_category_id = {};
            var categ_with_qty = {}
            var categ_with_total= {}
            for (let i = 0; i < this.orderlines.models.length; i++) {
                let line = this.orderlines.models[i];
                let pos_categ_id = line['product']['pos_categ_id'][0]
                if (pos_categ_id) {
                    if (!this.lines_by_category_id[pos_categ_id]) {
                        this.lines_by_category_id[pos_categ_id] = [line]
                    } else {
                        this.lines_by_category_id[pos_categ_id].push(line)
                    }
                    if(pos_categ_id in categ_with_qty){
                        categ_with_qty[pos_categ_id]+=line.quantity
                        categ_with_total[pos_categ_id]+=line.get_price_without_tax();
                    }
                    else{
                        categ_with_qty[pos_categ_id] = line.quantity
                        categ_with_total[pos_categ_id]=line.get_price_without_tax();
                    }
                }
            }
            let promotion_line_active = null
            for (let i = 0; i < promotion_lines.length; i++) {
                let promotion_line = promotion_lines[i];
                let categ_id = promotion_line['category_id'][0];
                if (this.lines_by_category_id[categ_id] && this.checking_free_item_apply_and_or(promotion,categ_with_total[categ_id],categ_with_qty[categ_id])) {
                    var len_line = this.lines_by_category_id[categ_id].length
                    var last_line = this.lines_by_category_id[categ_id][len_line-1]
                    let product = this.pos.db.get_product_by_id(last_line.product.id);
                    await this.set_category_product_free_gift(promotion,promotion_line,product,1) 
                }
            }

        },
        // TODO: 8_discount_lowest_price
        compute_discount_lowest_price: function (promotion) {
            let orderlines = this.orderlines.models;
            let line_apply = null;
            for (let i = 0; i < orderlines.length; i++) {
                let line = orderlines[i];
                if (!line_apply) {
                    line_apply = line
                } else {
                    if (line.get_price_with_tax() < line_apply.get_price_with_tax()) {
                        line_apply = line;
                    }
                }
            }
            let product_discount = this.pos.db.product_by_id[promotion.product_id[0]];
            if (line_apply && product_discount) {
                let promotion_reason = promotion.name;
                let promotion_discount = promotion.discount_lowest_price;
                if (promotion.new_type=='Discount Fixed Amount') {
                    var disc = 0

                    var fixed_amount = promotion.discount_fixed_amount_lp 
                    if(fixed_amount) {
                        disc = fixed_amount
                        var company_pos = this.pos.company
                        var tax_discount_policy = company_pos.tax_discount_policy
                        // if(tax_discount_policy != 'untax'){
                        //     disc=((disc * line_apply.quantity)/ line_apply.get_price_without_tax()) * 100
                        // }
                        // else {
                            disc=(disc /line_apply.get_real_total_w_discount()) * 100
                        // }
                    }
                    if(disc>100) {
                        disc=100
                    } 
                    this._apply_promotion_to_orderlines([line_apply], promotion.id, promotion_reason, 0, disc)
                }
                else{
                    var real_total = line_apply.get_real_total_w_discount()
                    var amount_disc = real_total * (promotion_discount/100);
                    if (amount_disc > promotion.max_discount_amount_lowest_price && promotion.max_discount_amount_lowest_price)
                    {
                        amount_disc = promotion.max_discount_amount_lowest_price ;
                        promotion_discount = (amount_disc/ real_total) * 100
                    }
                    
                    this._apply_promotion_to_orderlines([line_apply], promotion.id, promotion_reason, 0, promotion_discount);
                }
            }
            this.pos.chrome.showNotification(_t('Promotion Program: ') + promotion['name'], _t(' Applied to Order!!!'))
        },
        _get_rules_apply_multi_buy: function (promotion) {
            let rules_apply = [];
            let rules = this.pos.multi_buy_by_promotion_id[promotion.id];
            let total_qty_by_product = this.product_quantity_by_product_id();
            if (rules) {
                for (let i = 0; i < rules.length; i++) {
                    let rule = rules[i];
                    let product_ids = rule.product_ids;
                    let total_qty_exist = 0;
                    for (let index in product_ids) {
                        let product_id = product_ids[index];
                        if (total_qty_by_product[product_id]) {
                            total_qty_exist += total_qty_by_product[product_id]
                        }
                    }
                    if (total_qty_exist >= rule['qty_apply']) {
                        rules_apply.push(rule)
                    }
                }
            }
            return rules_apply
        },

        // TODO: 9_multi_buy
        compute_multi_buy: function (promotion) {
            let rules_apply = this._get_rules_apply_multi_buy(promotion)
            let total_qty_by_product = this.product_quantity_by_product_id()
            let product_discount = this.pos.db.product_by_id[promotion.product_id[0]]
            let product_promotion = {};
            if (rules_apply && product_discount) {
                for (let n = 0; n < rules_apply.length; n++) {
                    let rule = rules_apply[n];
                    let qty_remain = rule['qty_apply'];
                    for (let index in rule.product_ids) {
                        let product_id = rule.product_ids[index];
                        if (total_qty_by_product[product_id]) {
                            let qty_of_product_in_cart = total_qty_by_product[product_id];
                            if (qty_remain >= qty_of_product_in_cart) {
                                product_promotion[product_id] = qty_of_product_in_cart;
                                qty_remain -= qty_of_product_in_cart
                            } else if (qty_remain < qty_of_product_in_cart) {
                                if (qty_remain == 0) {
                                    break
                                }
                                if ((qty_remain - qty_of_product_in_cart) <= 0) {
                                    product_promotion[product_id] = qty_remain
                                    break
                                } else {
                                    product_promotion[product_id] = qty_of_product_in_cart
                                }
                            }
                        }
                    }
                    let promotion_amount = 0;
                    let promotion_reason = _t('Buy ');
                    for (let product_id in product_promotion) {
                        let product = this.pos.db.get_product_by_id(product_id);
                        let differencePrice = product.get_price(this.pos._get_active_pricelist(), 1, product.uom_id[0]) - rule.list_price
                        promotion_amount += differencePrice * total_qty_by_product[product_id];
                        promotion_reason += product_promotion[product_id] + ' ' + product.display_name;
                        promotion_reason += ' , '
                    }
                    promotion_reason += ' Set price each item ' + this.pos.format_currency(rule.list_price,false,this.currency);
                    product_discount.display_name = promotion_reason
                    this.add_promotion_gift(product_discount, promotion_amount, -1, {
                        promotion: true,
                        promotion_id: promotion.id,
                        promotion_reason: promotion_reason
                    })
                }
            }
            this.pos.chrome.showNotification(_t('Promotion Program: ') + promotion['name'], _t(' Applied to Order!!!'))
        },

        // TODO: 10_buy_x_get_another_free
        compute_buy_x_get_another_free: async function (promotion) {
            if(!promotion.is_multi_level_promotion){
                let minimum_items = promotion['minimum_items'];
                let total_quantity = this.product_quantity_by_product_id();
                let total_price_by_product_id = this.total_price_by_product_id();
                let promotion_line = false;
                let product = false;

                let promotion_lines = this.pos.promotion_specific_product_by_promotion_id[promotion['id']];
                if(promotion_lines && promotion.promotion_specific_product_ids){
                    promotion_lines = promotion_lines.filter((o)=> promotion.promotion_specific_product_ids.includes(o.id) == true);
                } else {
                    promotion_lines = [];
                }

                if(promotion_lines){
                    for(let line of promotion_lines){
                        let product_id = line.product_id[0];
                        if (total_quantity[product_id]  && this.checking_free_item_apply_and_or(promotion,total_price_by_product_id[product_id],total_quantity[product_id])) {
                            product = this.pos.db.product_by_id[product_id];
                            if (!product) {
                                return this.pos.alert_message({
                                    title: _t('Error'),
                                    body: 'Product id ' + product_id + ' not available in pos'
                                })
                            }else{
                                promotion_line = line;
                            }
                        }
                    }
                }

                if(product && promotion_line){
                    await this.set_product_free_gift_specific_product(promotion,promotion_line,product,1);
                }
            }else{
                if(!this.pos.promotion_multilevel_condition_by_promotion_id || !this.pos.promotion_multilevel_gift_by_promotion_id){
                    return false;
                }
                let gifts = this.pos.promotion_multilevel_gift_by_promotion_id[promotion['id']];
                if(gifts && promotion.multilevel_gift_ids){
                    gifts = gifts.filter((o)=> promotion.multilevel_gift_ids.includes(o.id) == true);
                } else {
                    gifts = [];
                }

                let conditions = this.pos.promotion_multilevel_condition_by_promotion_id[promotion['id']];
                if(conditions && promotion.multilevel_condition_ids){
                    conditions = conditions.filter((o)=> promotion.multilevel_condition_ids.includes(o.id) == true);
                } else {
                    conditions = [];
                }
                if(conditions.length && gifts.length){
                    let condition_fulfilled = []; 
                    let lines = _.filter(this.orderlines.models, function (line) {
                        return !line['is_return'] && !line['promotion_gift']
                    });
                    if(lines.length == 0){
                        condition_fulfilled.push(false);
                    }
                    for(let c of conditions){
                        let check_line = lines.filter(o=>o.quantity >= c.minimum_quantity && o.product.id == c.product_id[0]);
                        if(check_line.length){
                            condition_fulfilled.push(true);
                        }else{
                            condition_fulfilled.push(false);
                        }
                    }
                    let can_apply = condition_fulfilled.length?condition_fulfilled.every(o=>o===true):false
                    if(!can_apply){
                        return this.pos.alert_message({
                            title: _t('Error'),
                            body: 'Condition for Promotion "'+promotion.name+'" is not fulfilled',
                        });
                    }else{
                        await this.set_product_free_gift_multilevel_specific_product(promotion, gifts);
                    }
                }
            }

        },

        // TODO: 11_first_order
        compute_first_order: function (promotion) {
            let total_order = this.get_amount_total_without_promotion();
            if (total_order > 0 && promotion['type']=="11_first_order") {
                let promotion_reason = promotion.name;
                let lines = _.filter(this.orderlines.models, function (line) {
//                    return !line['is_return'] && !line['promotion']
                    return !line['is_return'] && !line['promotion_gift']
                });
                if (promotion.new_type=='Discount Fixed Amount') {
                    var fixed_amount = promotion.discount_fixed_amount_fo    
                    var disc = fixed_amount
                    var real_total = 0
                    for(let line of lines){
                        if(line.is_product_coupon){
                            continue;
                        }
                        real_total+=line.get_real_total_w_discount();
                    }
                    if(fixed_amount) {
                        disc = fixed_amount
                        var company_pos = this.pos.company
                        var tax_discount_policy = company_pos.tax_discount_policy
                        // if(tax_discount_policy != 'untax'){
                        //     disc=(disc / this.get_total_without_tax()) * 100
                        // }
                        // else {
                            disc=(disc / real_total) * 100
                        // }
                    }

                    for (let i = 0; i < lines.length; i++) {
                        let line = lines[i];
                        if(disc>100) {
                            disc=100
                        } 
                        this._apply_promotion_to_orderlines([line], promotion.id, promotion_reason, 0, disc)
                    }
                }
                else{
                    for (let i = 0; i < lines.length; i++) {
                        let line = lines[i];
                        this._apply_promotion_to_orderlines([line], promotion.id, promotion_reason, 0, promotion.discount_first_order)
                    }
                    
                }
            }
        },

        // TODO: 12_buy_total_items_free_items
        compute_buy_total_items_free_items: function (promotion) {
            let gifts = this.pos.promotion_gift_free_by_promotion_id[promotion.id];
            if (!gifts) {
                console.warn('gifts not found');
                return false;
            }
            let total_items_ofRules_inCart = 0;
            let product_quantity_by_product_id = this.product_quantity_by_product_id();
            for (let i = 0; i < promotion.product_ids.length; i++) {
                let product_id = promotion.product_ids[i];
                let total_qty_by_product = product_quantity_by_product_id[product_id];
                if (total_qty_by_product) {
                    total_items_ofRules_inCart += total_qty_by_product
                }
            }
            let minimum_items = promotion.minimum_items;
            for (let i = 0; i < gifts.length; i++) {
                let gift = gifts[i];
                let product = this.pos.db.get_product_by_id(gift.product_id[0]);
                let qty_free = gift.quantity_free;
                if (!product) {
                    Gui.showPopup('ConfirmPopup', {
                        title: _t('Warning'),
                        body: gift.product_id[1] + _t(' not available in POS, please contact your admin'),
                        disableCancelButton: true,
                    })
                } else {
                    if (gift.type == 'only_one') {
                        qty_free = qty_free
                    } else {
                        qty_free = parseInt(this.get_total_items() / minimum_items) * qty_free
                    }
                    let product = this.pos.db.get_product_by_id(gift.product_id[0]);
                    if (product) {
                        this.add_promotion_gift(product, 0, qty_free, {
                            promotion: true,
                            promotion_id: promotion.id,
                            promotion_gift: true,
                            promotion_reason: promotion.name
                        })
                    } else {
                        Gui.showPopup('ConfirmPopup', {
                            title: _t('Alert'),
                            body: _t('Product' + gift.product_id[1] + ' not found on YOUR POS'),
                            disableCancelButton: true,
                        })
                    }
                }
            }
        },

        // TODO: 13_buy_total_items_free_items
        compute_gifts_filter_by_total_amount: async function (promotion) {
            let lines = _.filter(this.orderlines.models, function (line) {
                    return !line['is_return'] && !line['promotion_gift']
                });
            var last_line = lines[lines.length-1]
            let selected_product = this.pos.db.get_product_by_id(last_line.product.id);

            if(!selected_product) {
                Gui.showPopup('ConfirmPopup', {
                    title: _t('Alert'),
                    body: _t('Product' + selected_product.name + ' not found on YOUR POS'),
                    disableCancelButton: true,
                })
                return false
            }

            let gifts = this.pos.promotion_gift_free_by_promotion_id[promotion.id];
            if(gifts && promotion.gift_free_ids){
                gifts = gifts.filter((o)=> promotion.gift_free_ids.includes(o.id) == true);
            }else{
                gifts = [];
            }
            if (!gifts) {
                console.warn('gifts not found');
                return false;
            }

            let total_order = this.get_amount_total_without_promotion();
            let lowest_price = null;
            this.orderlines.models.forEach((l)=>{
                let product = this.pos.db.product_by_id[l.product.id];
                if(product && ['service','asset'].includes(product.type) == false){
                    if(lowest_price === null || product.get_price() < lowest_price){
                        lowest_price = product.get_price();
                        selected_product = product;
                    }
                }
            });
            await this.set_product_free_gift(promotion,selected_product,1);
        },

        // TODO: 15_tebus_murah_by_specific_product
        compute_tebus_murah_specific_product: async function (promotion) {
            let can_apply = false;
            let product_quantity_by_product_id = this.product_quantity_by_product_id();
            let total_price_by_product_id = this.total_price_by_product_id();
            if(this.pos.promotion_tebus_murah_product_by_promotion_id){

                let items = this.pos.promotion_tebus_murah_product_by_promotion_id[promotion.id];
                if(items && promotion.tebus_murah_product_ids){
                    items = items.filter((o)=> promotion.tebus_murah_product_ids.includes(o.id) == true);
                } else {
                    items = [];
                }

                if(items){
                    for (let item of items) {
                        var t_qty = 0
                        var t_price = 0
                        for (let order_line of this.orderlines.models) {
                            if(item.product_ids.includes(order_line.product.id)){
                                t_qty+=product_quantity_by_product_id[order_line.product.id]
                                t_price+=total_price_by_product_id[order_line.product.id]
                            }
                        }
                        can_apply = this.checking_tebus_murah_apply_and_or(promotion,t_price,t_qty)
                        if(can_apply){
                            let product = this.pos.db.get_product_by_id(item.product_id[0]);
                            if(product){
                                this.set_tebus_murah_product(product, item.price, item.quantity, {
                                    promotion: true,
                                    promotion_id: promotion.id,
                                    promotion_gift: true,
                                    promotion_reason: promotion.name
                                });
                            } else{
                                Gui.showPopup('ConfirmPopup', {
                                    title: _t('Warning'),
                                    body: item.product_id[1] + _t(' not available in POS, please sync Data'),
                                    disableCancelButton: true,
                                });
                            }
                        }
                    }
                }
            }
        },


        // TODO: 17_tebus_murah_by_selected_brand
        compute_tebus_murah_brand: async function (promotion) {
            let can_apply = false;
            let tebus_murah_brand_ids = promotion.tebus_murah_brand_ids
            let gift_based_on = promotion.tebus_murah_brand_gift_based_on
            let min_amount = promotion.tebus_murah_brand_min_amount
            let min_qty = promotion.tebus_murah_brand_min_qty
            var promotion_tebus_murah_selected_brands = this.pos.promotion_tebus_murah_selected_brands
            if(!promotion_tebus_murah_selected_brands){
                return false;
            }
            let tebus_murah_selected_brand_apply_and_or = promotion.tebus_murah_selected_brand_apply_and_or
            if(!tebus_murah_brand_ids || ! promotion.id in promotion_tebus_murah_selected_brands){
                return false
            }

            promotion_tebus_murah_selected_brands = promotion_tebus_murah_selected_brands[promotion.id]
            if(!promotion_tebus_murah_selected_brands){
                return false;
            }
            if(promotion_tebus_murah_selected_brands && promotion.tebus_murah_selected_brand_ids){
                promotion_tebus_murah_selected_brands = promotion_tebus_murah_selected_brands.filter((o)=> promotion.tebus_murah_selected_brand_ids.includes(o.id) == true);
            } else {
                promotion_tebus_murah_selected_brands = [];
            }

            let product_quantity_by_product_id = this.product_quantity_by_product_id();
            let total_price_by_product_id = this.total_price_by_product_id();
            var t_qty = 0
            var t_price = 0
            var arr_product_same_brand = []
            for (let order_line of this.orderlines.models) {
                var brand_ids = order_line['product']['product_brand_ids'];
                if (brand_ids) {
                    for (let o = 0; o < brand_ids.length; o++) {
                        var brand_id = brand_ids[o]
                        if(tebus_murah_brand_ids.includes(brand_id)){
                            t_qty+=product_quantity_by_product_id[order_line['product']['id']]
                            t_price+=total_price_by_product_id[order_line['product']['id']]
                            arr_product_same_brand.push(order_line['product'])
                            break
                        }
                    }
                }
            }

            var min_amount_success = false
            var min_qty_success = false
            if(t_price >= min_amount){
                min_amount_success = true
            }
            if(t_qty >= min_qty){
                min_qty_success = true
            }

            if(tebus_murah_selected_brand_apply_and_or=='And' && min_qty_success && min_amount_success ){
                can_apply = true
            }
            if(tebus_murah_selected_brand_apply_and_or=='Or' && (min_qty_success || min_amount_success) ){
                can_apply = true
            }

            if (can_apply) {

                    var arr_type_apply = promotion_tebus_murah_selected_brands.map( (i) => ({ label: i.display_name, item: i, id: i.id }) );
                    let {confirmed, payload: selected} = await Gui.showPopup('SelectionPopup', {
                        title: _t('Tebus Murah Selection Brand'),
                        list: arr_type_apply,
                    });
                    if(confirmed){
                        if(selected.type_apply == 'same_brand') {
                            if(arr_product_same_brand.length == 1) {
                                this.set_tebus_murah_product(arr_product_same_brand[0], selected.tebus_murah_price, selected.qty_qift, {
                                    promotion: true,
                                    promotion_id: promotion.id,
                                    promotion_gift: true,
                                    promotion_reason: promotion.name
                                });
                            }
                            else{
                                var arr_selection_same_brand = arr_product_same_brand.map( (i) => ({ label: i.name, item: i, id: i.id }) );
                                let {confirmed, payload: selected_product} = await Gui.showPopup('SelectionPopup', {
                                    title: _t('Selection Product'),
                                    list: arr_selection_same_brand,
                                });
                                if(confirmed){
                                    this.set_tebus_murah_product(selected_product, selected.tebus_murah_price, selected.qty_qift, {
                                        promotion: true,
                                        promotion_id: promotion.id,
                                        promotion_gift: true,
                                        promotion_reason: promotion.name
                                    });
                                }
                            }
                        }

                        if(selected.type_apply == 'selected_product') {
                            var arr_select_product = []
                            for (var ii = 0; ii < selected.product_ids.length; ii++) {
                                let select_product = this.pos.db.get_product_by_id(selected.product_ids[ii]);
                                if (!select_product) {
                                    Gui.showPopup('ConfirmPopup', {
                                        title: _t('Warning'),
                                        body: selected.product_ids[ii] + _t(' not available in POS, please sync Data'),
                                        disableCancelButton: true,
                                    });
                                }
                                else{
                                    arr_select_product.push(select_product)
                                }
                            }
                            var arr_selection_product = arr_select_product.map( (i) => ({ label: i.name, item: i, id: i.id }) );
                            let {confirmed, payload: selected_product} = await Gui.showPopup('SelectionPopup', {
                                    title: _t('Selection Product'),
                                    list: arr_selection_product,
                                });
                            if(confirmed){
                                this.set_tebus_murah_product(selected_product, selected.tebus_murah_price, selected.qty_qift, {
                                    promotion: true,
                                    promotion_id: promotion.id,
                                    promotion_gift: true,
                                    promotion_reason: promotion.name
                                });
                            }
                        }

                    }
                
            }

        },

        set_product_free_gift_multilevel_specific_product: async function (promotion, gifts) { 
            let gift = false;
            let product_gift = false;
            let quantity_free = 1; 

            if(gifts.length == 1){
                gift = gifts[0];
                quantity_free = gift.quantity_free;
                product_gift = this.pos.db.product_by_id[gift.product_id[0]];
                if(!product_gift){
                    Gui.showPopup('ErrorPopup', {
                        title: _t('Warning'),
                        body: gift.product_id[1] + _t(' not available in POS'),
                    })
                    return;
                }
            }
            if(gifts.length > 1){
                let item_selected = [];
                let {confirmed, payload: selected} = await Gui.showPopup('PopUpSelectionBox',{
                    title: _t('Select: ' + promotion.name),
                    items: gifts.map((i)=>({name: i.product_id[1], item:i, id: i.id})),
                    onlySelectOne: true,
                });
                if(confirmed && selected.items.length){
                    item_selected = selected.items;
                }
                if(!confirmed){
                    return;
                }
                if(!item_selected.length){
                    let {confirmed: confirmed_mistake, payload: payload1} = await Gui.showPopup('ConfirmPopup', {
                        title: _t('Warning'),
                        body: _t('You have to choose the free gift.'),
                        disableCancelButton: true,
                    });
                    if(confirmed_mistake){
                        let {confirmed: confirmed2, payload: selected2} = await Gui.showPopup('PopUpSelectionBox',{
                            title: _t('Select: ' + promotion.name),
                            items: gifts.map((i)=>({name: i.product_id[1], item:i, id: i.id})),
                            onlySelectOne: true,
                        });
                        if(confirmed2 && selected2.items.length){
                            item_selected = selected2.items;
                        }
                        if(!confirmed2){
                            return Gui.showPopup('ErrorPopup', {
                                title: _t('Warning'),
                                body: _t('You have to choose the free gift.'),
                            });
                        }
                    }
                }

                if(item_selected.length){
                    gift = item_selected[0].item;
                    quantity_free = gift.quantity_free;
                    product_gift = this.pos.db.product_by_id[gift.product_id[0]];
                    if(!product_gift){
                        Gui.showPopup('ErrorPopup', {
                            title: _t('Warning'),
                            body: gift.product_id[1] + _t(' not available in POS'),
                        })
                        return;
                    }
                } else {
                    return this.pos.alert_message({
                        title: _t('Warning'),
                        body: _t('No Gift selected')
                    });
                }
            }
            if(product_gift){
                this.add_promotion_gift(product_gift, 0, quantity_free, {
                    promotion: true,
                    promotion_id: promotion.id,
                    promotion_reason: promotion.name
                })
                this.pos.chrome.showNotification(_t('Promotion Program: ') + promotion['name'], _t(' Applied to Order!!!'))
            }
        },

        set_product_free_gift_specific_product: async function (promotion,promotion_line,product,qty_free) {
            var products_gift_free = []
            var selected_products_gift_free = []
            var same_product = false
            var directly = false

            var error = false
            var one_gift_free_type_apply = false
            var need_popup = false

            if(promotion_line.type_apply=='selected_product'){
                for (var ii = 0; ii < promotion_line.product_ids.length; ii++) {
                    var product_gift_free_id = promotion_line.product_ids[ii]
                    var product_gift_free = this.pos.db.product_by_id[product_gift_free_id];
                    if(product_gift_free){
                        products_gift_free.push(product_gift_free)
                        selected_products_gift_free.push(product_gift_free)
                        var last_qty_free = promotion_line.qty_free
                        directly = promotion_line
                        directly.quantity_free = directly.qty_free
                    }
                }
            }


            if(promotion_line.type_apply=='same_product'){
                same_product = promotion_line
                products_gift_free.push(product)
                var last_qty_free = promotion_line.qty_free
            }


            if(products_gift_free.length==1){
                one_gift_free_type_apply = true
                product_gift = products_gift_free[0]
                var get_qty_free = qty_free*last_qty_free
            }
            if(products_gift_free.length > 1){
                need_popup = true
            }

            if(need_popup){
                let {confirmed, payload: number} = await Gui.showPopup('PopupProductSelectionGiftFree', {
                    'product': product,
                    'selected_products_gift_free':selected_products_gift_free,
                    'name':promotion.name,
                    'directly':directly,
                    'name_variant':product.get_name_variant(),
                    'promotion':promotion,
                    'order':this,
                    'list_products':products_gift_free,
                    'qty_free':qty_free,
                    'error':error,
                    'price':this.pos.format_currency(product.get_price(),false,this.currency)
                });
                if(confirmed){
                    this.pos.chrome.showNotification(_t('Promotion Program: ') + promotion['name'], _t(' Applied to Order!!!'))
                }
                
            }
            if(one_gift_free_type_apply && !need_popup){
                this.add_promotion_gift(product_gift, 0, get_qty_free, {
                    promotion: true,
                    promotion_id: promotion.id,
                    promotion_reason: promotion.name
                })
                this.pos.chrome.showNotification(_t('Promotion Program: ') + promotion['name'], _t(' Applied to Order!!!'))
            }
        },

        set_brand_product_free_gift: async function (promotion,promotion_line,lines) {
            var product = lines.product
            var products_gift_free = []
            var selected_products_gift_free = []
            var same_brand_products = []
            var selected_brand_products = []
            var list_brand_n_products = {}
            var selected_product_brand = false
            var same_brand = false
            var selected_brand = false
            var directly = false

            var error = false
            var one_gift_free_type_apply = false
            var need_popup = false

            var qty_free = promotion_line.qty_qift

            if(promotion_line.type_apply == 'selected_product'){
                promotion_line.product_ids.forEach((product_gift_id)=>{
                    let product_gift = this.pos.db.product_by_id[product_gift_id];
                    if(product_gift){
                        products_gift_free.push(product_gift);
                        selected_products_gift_free.push(product_gift);
                        selected_product_brand = promotion_line;
                        directly = promotion_line;
                    }
                });
            }

            if(promotion_line.type_apply == 'same_brand'){
                let lowest_price = null;
                this.orderlines.models.forEach((l)=>{
                    let product = this.pos.db.product_by_id[l.product.id];
                    if(product && ['service','asset'].includes(product.type) == false && typeof product.product_brand_ids !== undefined){
                        let is_has_brand = product.product_brand_ids.length!=0?true:false;
                        var is_same_brand = product.product_brand_ids.some((v) => promotion_line.brand_ids.includes(v) == true);
                        if(is_has_brand && is_same_brand && (lowest_price === null || product.get_price() < lowest_price)){
                            lowest_price = product.get_price();
                            same_brand = promotion_line;
                            products_gift_free = [product];
                            same_brand_products = [product];
                            directly = promotion_line;
                        }
                    }
                });
            }

            if(promotion_line.type_apply=='selected_brand'){
                var all_product_ids = this.pos.db.product_ids
                var count = 0
                for (var iii = 0; iii < all_product_ids.length; iii++) {
                    var check_product = this.pos.db.product_by_id[all_product_ids[iii]]
                    if(check_product){
                        if(check_product.type == 'service' || check_product.type == 'asset'){
                            continue
                        }
                        if(check_product.product_brand_ids && $(check_product.product_brand_ids).not(promotion_line.brand_gift_ids).length != check_product.product_brand_ids.length ){
                            var selected_brand = promotion_line
                            products_gift_free.push(check_product)
                            selected_brand_products.push(check_product)
                            count+=1
                            directly = promotion_line
                            for (var iiio = 0; iiio < check_product.product_brand_ids.length; iiio++) {
                                var brand_id_tab = check_product.product_brand_ids[iiio]
                                if(!promotion_line.brand_gift_ids.includes(brand_id_tab)){
                                    continue
                                }
                                var brand_name = ''
                                if(this.pos.pos_product_brands.filter((c) => c.id==brand_id_tab)){
                                    brand_name = this.pos.pos_product_brands.filter((c) => c.id==brand_id_tab)[0].brand_name
                                }
                                
                                if(!list_brand_n_products[brand_name]){
                                    list_brand_n_products[brand_name] = [check_product]
                                }
                                else{
                                    list_brand_n_products[brand_name].push(check_product)
                                }
                            }
                        }
                            
                    }
                    if (count >= 100){
                        break
                    }
                }
            }
            if(products_gift_free.length==1){
                one_gift_free_type_apply = true
                product_gift = products_gift_free[0]
            }
            if(products_gift_free.length > 1){
                need_popup = true
            }
            if( (selected_product_brand && same_brand)  || (selected_product_brand && selected_brand) || (same_brand && selected_brand) ){
                need_popup = true
            }

            if(need_popup){
                let {confirmed, payload: number} = await Gui.showPopup('PopupProductSelectionGiftFree', {
                    'product': product,
                    'selected_product_brand':selected_product_brand,
                    'same_brand':same_brand,
                    'selected_brand':selected_brand,
                    'selected_products_gift_free':selected_products_gift_free,
                    'same_brand_products':same_brand_products,
                    'selected_brand_products':selected_brand_products,
                    'list_brand_n_products':list_brand_n_products,
                    'name':promotion.name,
                    'directly':directly,
                    'name_variant':product.get_name_variant(),
                    'promotion':promotion,
                    'order':this,
                    'list_products':products_gift_free,
                    'qty_free':qty_free,
                    'error':error,
                    'price':this.pos.format_currency(product.get_price(),false,this.currency)
                });
                if(confirmed){
                    this.pos.chrome.showNotification(_t('Promotion Program: ') + promotion['name'], _t(' Applied to Order!!!'))
                }
                
            }
            if(one_gift_free_type_apply && !need_popup){
                this.add_promotion_gift(product_gift, 0, qty_free, {
                    promotion: true,
                    promotion_id: promotion.id,
                    promotion_reason: promotion.name
                })
                this.pos.chrome.showNotification(_t('Promotion Program: ') + promotion['name'], _t(' Applied to Order!!!'))
            }
        },

        set_category_product_free_gift: async function (promotion,promotion_line,product,qty_free) {
            var products_gift_free = []
            var selected_products_gift_free = []
            var same_category_products = []
            var selected_category_products = []
            var list_categ_n_products = {}
            var selected_product_category = false
            var same_category = false
            var selected_category = false
            var directly = false

            var error = false
            var one_gift_free_type_apply = false
            var need_popup = false

            if(promotion_line.type_apply=='selected_product'){
                for (var ii = 0; ii < promotion_line.product_ids.length; ii++) {
                    var product_gift_free_id = promotion_line.product_ids[ii]
                    var product_gift_free = this.pos.db.product_by_id[product_gift_free_id];
                    if(product_gift_free){
                        products_gift_free.push(product_gift_free)
                        selected_products_gift_free.push(product_gift_free)
                        var last_qty_free = promotion_line.qty_free
                        selected_product_category = promotion_line
                        directly = promotion_line
                    }
                }
            }


            if(promotion_line.type_apply=='same_category'){
                var all_product_ids = this.pos.db.product_ids
                var count = 0
                for (var iii = 0; iii < all_product_ids.length; iii++) {
                    var check_product = this.pos.db.product_by_id[all_product_ids[iii]]
                    if(check_product){
                        if(check_product.type == 'service' || check_product.type == 'asset'){
                            continue
                        }
                        if(check_product.pos_categ_id && check_product.pos_categ_id[0] ==  promotion_line.category_id[0]){
                            var last_qty_free = promotion_line.qty_free
                            var same_category = promotion_line
                            products_gift_free.push(check_product)
                            same_category_products.push(check_product)
                            count+=1
                            directly = promotion_line
                        }
                            
                    }
                    if (count >= 100){
                        break
                    }
                }
            }

            if(promotion_line.type_apply=='selected_category'){
                var all_product_ids = this.pos.db.product_ids
                var count = 0
                for (var iii = 0; iii < all_product_ids.length; iii++) {
                    var check_product = this.pos.db.product_by_id[all_product_ids[iii]]
                    if(check_product){
                        if(check_product.type == 'service' || check_product.type == 'asset'){
                            continue
                        }
                        if(check_product.pos_categ_id && jQuery.inArray( check_product.pos_categ_id[0],  promotion_line.category_ids ) != -1 ){
                            var last_qty_free = promotion_line.qty_free
                            var selected_category = promotion_line
                            products_gift_free.push(check_product)
                            selected_category_products.push(check_product)
                            count+=1
                            directly = promotion_line

                            if(!list_categ_n_products[check_product.pos_categ_id[1]]){
                                list_categ_n_products[check_product.pos_categ_id[1]] = [check_product]
                            }
                            else{
                                list_categ_n_products[check_product.pos_categ_id[1]].push(check_product)
                            }
                        }
                            
                    }
                    if (count >= 100){
                        break
                    }
                }
            }

            if(products_gift_free.length==1){
                one_gift_free_type_apply = true
                product_gift = products_gift_free[0]
                var get_qty_free = qty_free*last_qty_free
            }
            if(products_gift_free.length > 1){
                need_popup = true
            }
            if( (selected_product_category && same_category)  || (selected_product_category && selected_category) || (same_category && selected_category) ){
                need_popup = true
            }

            if(need_popup){
                let {confirmed, payload: number} = await Gui.showPopup('PopupProductSelectionGiftFree', {
                    'product': product,
                    'selected_product_category':selected_product_category,
                    'same_category':same_category,
                    'selected_category':selected_category,
                    'selected_products_gift_free':selected_products_gift_free,
                    'same_category_products':same_category_products,
                    'selected_category_products':selected_category_products,
                    'list_categ_n_products':list_categ_n_products,
                    'name':promotion.name,
                    'directly':directly,
                    'name_variant':product.get_name_variant(),
                    'promotion':promotion,
                    'order':this,
                    'list_products':products_gift_free,
                    'qty_free':qty_free,
                    'error':error,
                    'price':this.pos.format_currency(product.get_price(),false,this.currency)
                });
                if(confirmed){
                    this.pos.chrome.showNotification(_t('Promotion Program: ') + promotion['name']+ _t(', Category: ')+ promotion_line.category_id[1], _t(' Applied to Order!!!'))
                }
                
            }
            if(one_gift_free_type_apply && !need_popup){
                this.add_promotion_gift(product_gift, 0, get_qty_free, {
                    promotion: true,
                    promotion_id: promotion.id,
                    promotion_reason: promotion.name
                })
                this.pos.chrome.showNotification(_t('Promotion Program: ') + promotion['name']+ _t(', Category: ')+ promotion_line.category_id[1], _t(' Applied to Order!!!'))
            }
        },

        set_product_free_gift: async function (promotion,product,qty_free) {
            var products_gift_free = []
            var selected_products_gift_free = []
            var same_lower_price_gift_free = []
            var selected_product = false
            var same_product = false
            var same_lower_price = false
            var directly = false
            var type_apply_opts = {
                'selected_product': 'Selected Product',
                'same_product': 'Same Product',
                'same_lower_price': 'Same / Lower Price',
            }
            let product_gift = false;
            let get_qty_free = 0;
            let last_qty_free = 0;
            var error = false
            var one_gift_free_type_apply = false
            var need_popup = false
            if(!promotion.gift_free_ids || promotion.gift_free_ids.length == 0){
                error = 'Not have list apply free products.'
                need_popup = true
            }
            if(promotion.gift_free_ids && promotion.gift_free_ids.length != 0){

                let gift_free = false;
                var gifts = this.pos.promotion_gift_free_by_promotion_id[promotion.id];
                if(gifts && promotion.gift_free_ids){
                    gifts = gifts.filter((o)=> promotion.gift_free_ids.includes(o.id) == true);
                }else{
                    gifts = [];
                }

                if(!gifts){
                    error = 'Not have list apply free products.'
                    need_popup = true
                } else { 
                    if(gifts.length == 1 ){
                        gift_free = gifts[0];
                        directly = gift_free;
                    } else {
                        let {confirmed: confirmed_gift, payload: selected_gift_free} = await Gui.showPopup('PopUpSelectionBox',{
                            title: _t('Select: ' + promotion.name),
                            items: gifts.map((i)=>({name: type_apply_opts[i.type_apply], item:i, id:i.id})),
                            onlySelectOne: true,
                        });
                        if(confirmed_gift){
                            gift_free = selected_gift_free.items[0].item;
                        } else {
                            return this.pos.alert_message({
                                title: _t('Warning'),
                                body: _t('No Gift type selected')
                            });
                        }
                    }
                    if(gift_free.type_apply == 'same_product'){
                        product_gift = product;
                        get_qty_free = qty_free * gift_free.quantity_free;
                        one_gift_free_type_apply = true;
                    }
                    directly = gift_free;

                    if(gift_free.type_apply=='selected_product'){
                        // selected_product = false
                        for(let product_id of gift_free.product_ids){
                            var product_gift_free = this.pos.db.product_by_id[product_id];
                            if(product_gift_free){
                                products_gift_free.push(product_gift_free);
                                selected_products_gift_free.push(product_gift_free);
                                last_qty_free = gift_free.quantity_free;
                            }
                        }
                    }

                    if(gift_free.type_apply=='same_lower_price'){
                        for(let [index, product_id] of this.pos.db.product_ids.entries()){
                            var check_product = this.pos.db.product_by_id[product_id];
                            if(check_product && ['service','asset'].includes(check_product.type) == false){
                                if(check_product.get_price()<=product.get_price()){
                                    last_qty_free = gift_free.quantity_free;
                                    products_gift_free.push(check_product);
                                    same_lower_price_gift_free.push(check_product);
                                } 
                            }
                            if (index >= 100){
                                need_popup = true
                                break
                            }
                        }
                        // same_lower_price = false;
                    }
                }
            }

            if(products_gift_free.length==1){
                one_gift_free_type_apply = true
                product_gift = products_gift_free[0]
                get_qty_free = qty_free*last_qty_free
            }
            if(products_gift_free.length > 1){
                need_popup = true
            }
            if( (selected_product && same_product)  || (selected_product && same_lower_price) || (same_product && same_lower_price) ){
                need_popup = true
            }
            if(need_popup){
                let {confirmed, payload: number} = await Gui.showPopup('PopupProductSelectionGiftFree', {
                    'product': product,
                    'selected_product':selected_product,
                    'same_product':same_product,
                    'same_lower_price':same_lower_price,
                    'selected_products_gift_free':selected_products_gift_free,
                    'same_lower_price_gift_free':same_lower_price_gift_free,
                    'name':promotion.name,
                    'directly':directly,
                    'name_variant':product.get_name_variant(),
                    'promotion':promotion,
                    'order':this,
                    'list_products':products_gift_free,
                    'qty_free':qty_free,
                    'error':error,
                    'price':this.pos.format_currency(product.get_price(),false,this.currency)
                });
                if(confirmed){
                    this.pos.chrome.showNotification(_t('Promotion Program: ') + promotion['name'], _t(' Applied to Order!!!'))
                }
                
            }
            if(one_gift_free_type_apply && !need_popup){
                this.add_promotion_gift(product_gift, 0, get_qty_free, {
                    promotion: true,
                    promotion_id: promotion.id,
                    promotion_reason: promotion.name
                })
                this.pos.chrome.showNotification(_t('Promotion Program: ') + promotion['name'], _t(' Applied to Order!!!'))
            }

        },


        _apply_promotion_to_orderlines: function (lines, promotion_id, promotion_reason, promotion_amount, promotion_discount) {
            let self = this;
            for (let n = 0; n < lines.length; n++) {
                let line = lines[n];
                if(line.is_product_coupon){
                    continue;
                }
                 // Validate brand settings
                let promotion = self.pos.promotion_by_id[promotion_id];
                let promotion_brand_id = promotion.product_brand_id && promotion.product_brand_id[0] || 0;
                let product_brand_ids = line.product.product_brand_ids || [];
                let BrandValidate = !promotion_brand_id || product_brand_ids.includes(promotion_brand_id);
                if (!BrandValidate) continue;
                line.promotion = true;
                line.promotion_type = promotion.new_type;
                line.promotion_name = promotion.name;
                line.promotion_ids.push(promotion_id);
                line.promotion_id = promotion_id;
                line.promotion_reason = promotion_reason;
                line.promotion_amount = line.promotion_amount || 0.0;
                if (promotion_amount > 0) {
                    line.promotion_amount += promotion_amount;
                }
                line.promotion_discount = line.promotion_discount || 0.0;
                if (promotion_discount > 0) {
                    line.promotion_discount += promotion_discount;
                }
                line.promotion_stack = line.promotion_stack || {};
                if (line.promotion_stack) {
                    line.promotion_stack[promotion_id] = {'id': promotion_id, 'discount': promotion_discount, 'promotion_reason': promotion_reason,'sequence':promotion.sequence};
                }
                line.trigger('change', line)
            }
            this.pos.trigger('auto_update:paymentlines');
        },
        add_promotion_gift: function (product, price, quantity, options) {
            let line = new models.Orderline({}, {pos: this.pos, order: this.pos.get_order(), product: product});
            line.promotion = true;
            line.promotion_gift = true;
            
            if (options.promotion_id) {
                line.promotion_ids.push[options.promotion_id];
                line.promotion_id = options.promotion_id
            }
            if (options.buyer_promotion) {
                line.promotion = options.buyer_promotion;
            }
            if (options.frequent_buyer_id) {
                line.frequent_buyer_id = options.frequent_buyer_id;
            }
            if (options.promotion_reason) {
                line.promotion_reason = options.promotion_reason;
            }
            if (options.promotion_price_by_quantity) {
                line.promotion_price_by_quantity = options.promotion_price_by_quantity;
            }
            line.product.taxes_id = false
            line.price_manually_set = true; //no need pricelist change, price of promotion change the same, i blocked
            line.set_quantity(quantity);
            line.set_unit_price(price);
            line.price_manually_set = true;
            this.orderlines.add(line);
            this.pos.trigger('auto_update:paymentlines');
        },
        async _open_pop_up_home_delivery_order() {
            let self = this;
            let order = this.pos.get_order();
            if (order.get_total_with_tax() < 0 || order.orderlines.models.length == 0) {
                return Gui.showPopup('ConfirmPopup', {
                    title: _t('Alert'),
                    body: _t('Your shopping cart is empty or Amount total order smaller than 0'),
                })
            }
            if (!order.get_client()) {
                Gui.showPopup('ConfirmPopup', {
                    title: _t('Alert'),
                    body: _t('Shipping Order required select a Customer. Please select one Customer'),
                    disableCancelButton: true,
                })
                const {confirmed, payload: newClient} = await Gui.showTempScreen(
                    'ClientListScreen',
                    {client: null}
                );
                if (confirmed) {
                    order.set_client(newClient);
                } else {
                    return this.pos.alert_message({
                        title: _t('Alert'),
                        body: _t('Required choice Customer')
                    })
                }
            }
            const {confirmed, payload: values} = await Gui.showPopup('PopUpCreateShippingOrder', {
                title: _t('Create Home Delivery Order'),
                order: order,
                delivery_address:(order.get_client().street || '') + (order.get_client().street2 || ''),
                delivery_phone:(order.get_client().phone || order.get_client().mobile) ,
                client: order.get_client()
            })
            if (confirmed) {
                let client = order.get_client()
                var result = values.values;
                if (values.error) {
                    order.note = result['note'];
                    order.delivery_name = result['name'];
                    order.delivery_address = result['delivery_address'];
                    order.delivery_phone = result['delivery_phone'];
                    order.delivery_date = result['delivery_date'];
                    order.new_shipping_address = result['new_shipping_address'];
                    order.trigger('change', order);
                    this.pos.alert_message({
                        title: _t('Alert'),
                        body: values.error
                    })
                    
                    return this._open_pop_up_home_delivery_order()
                    
                }
                let client_val = {
                    name: result['name'],
                    phone: result['delivery_phone'],
                    property_product_pricelist: order.pricelist.id,
                    street: result['delivery_address'],
                };
                if (result.new_shipping_address) {
                    client_val['parent_id'] = client.id;
                    client_val['type'] = 'delivery';
                    client_val['id'] = null;
                } else {
                    client_val['id'] = client.id
                }
                if (result['note']) {
                    order.set_note(result['note']);
                }
                if (result['signature']) {
                    order.set_signature(result['signature']);
                }
                order.delivery_address = result.delivery_address;
                order.delivery_phone = result.delivery_phone;
                order.delivery_date = result.delivery_date;
                order.is_home_delivery = true
                let client_id = await this.pos.rpc({ // todo: template rpc
                    model: 'res.partner',
                    method: 'create_from_ui',
                    args: [client_val]
                }).then(function (client_id) {
                    return client_id
                }, function (err) {
                    return self.env.pos.query_backend_fail(err);
                })
                if (client_id) {
                    order.shipping_id = client_id;
                    order.trigger('change', order);
                    // let order_ids = await this.pos.push_single_order(order, {
                    //     draft: true
                    // })
                    // Gui.showPopup('ConfirmPopup', {
                    //     title: _t('New POS Shipping Order ID: ' + order_ids[0]),
                    //     body: _t('Order saved to Draft State and waiting Delivery Shipping Order, When your Delivery Man Shipping succeed and come back, please Full Fill Payment Order: ') + order.name,
                    //     disableCancelButton: true,
                    // })
                    // return this.pos.showScreen('ReceiptScreen');
                }
            }
        },

        _checking_period_times_condition: function (promotion) {
            let days = {
                1: 'monday',
                2: 'tuesday',
                3: 'wednesday',
                4: 'thursday',
                5: 'friday',
                6: 'saturday',
                7: 'sunday',
            };
            let pass_condition = false;
            if (!promotion.special_days && !promotion.special_times) {
                pass_condition = true
            } else {
                let date_now = new Date();
                let day_now = date_now.getDay();
                if (promotion.special_days) {
                    if (promotion[days[day_now]] == true) {
                        pass_condition = true
                    } else {
                        return pass_condition
                    }
                }
                if (promotion.special_times) {
                    let _st_time = field_utils.format.float_time(promotion.from_time);
                    let _et_time = field_utils.format.float_time(promotion.to_time);
                    let st_time = moment(moment().format('YYYY-MM-DD ' + _st_time + ':00'));
                    let et_time = moment(moment().format('YYYY-MM-DD ' + _et_time + ':00'));
                    let current_time = moment();
                    if(current_time.isSameOrAfter(st_time) && current_time.isSameOrBefore(et_time)){
                        pass_condition = true;
                    } else {
                        pass_condition = false;
                    }
                }
            }
            return pass_condition;
        },

        get_voucher_discount_amount: function(){
            let amount = 0;
            this.orderlines.models.forEach((l)=>{
                if(l.is_product_voucher){
                    amount += Math.abs(l.get_price_with_tax());
                }
            });
            return amount;
        },

        get_coupon_discount_amount: function(){
            let amount = 0;
            this.orderlines.models.forEach((l)=>{
                if(l.is_product_coupon){
                    amount += Math.abs(l.get_price_with_tax());
                }
            });
            return amount;
        },

    });

    let _super_Orderline = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
        initialize: function (attributes, options) {
            let res = _super_Orderline.initialize.apply(this, arguments);
            if (!options.json) {
                if (this.pos.config.sync_multi_session && this.pos.config.user_id) {
                }
                this.selected_combo_items = {};
                this.plus_point = 0;
                this.redeem_point = 0;
                this.reward_id = null;
                this.order_time = new Date().toLocaleTimeString()
                this.product_attribute_values = {}
                this.default_time = this.product.default_time
                this.promotion_ids = [];
                this.all_total_discount = 0
                this.unit_price_pricelist = 0
                this.discount_other_promotion = {}
                this.discount_from_pricelist = 0
                this.all_discount_except_pricelist = 0

                this.pos_coupon_id = false;
                this.pos_coupon_reward_discount = '';
                this.is_product_coupon = false;
                this.is_product_coupon_reward = false;
                this.pos_coupon_reward_description = '';
            }
            return res;
        },

        init_from_JSON: function (json) {
            this.restoring = true
            _super_Orderline.init_from_JSON.apply(this, arguments);
            this.default_time = this.product.default_time
            this.restoring = false
            if (json.product_attribute_values) {
                this.product_attribute_values = json.product_attribute_values;
            }
            if (json.promotion) {
                this.promotion = json.promotion;
            }
            if (json.promotion_gift) {
                this.promotion_gift = json.promotion_gift;
            }
            if (json.promotion_tebus_murah) {
                this.promotion_tebus_murah = json.promotion_tebus_murah;
            }
            if (json.promotion_id) {
                this.promotion_id = json.promotion_id;
            }
            if (json.promotion_ids) {
                this.promotion_ids = json.promotion_ids;
            } else {
                this.promotion_ids = [];
            }
            if (json.promotion_discount) {
                this.promotion_discount = json.promotion_discount;
            }
            if (json.promotion_stack) {
                this.promotion_stack = json.promotion_stack;
            }
            if (json.promotion_amount) {
                this.promotion_amount = json.promotion_amount;
            }
            if (json.promotion_reason) {
                this.promotion_reason = json.promotion_reason;
            }
            if (json.plus_point) {
                this.plus_point = json.plus_point;
            }
            if (json.redeem_point) {
                this.redeem_point = json.redeem_point;
            }
            if (json.reward_id) {
                this.reward_id = json.reward_id;
            }
            if (json.price_extra) {
                this.price_extra = json.price_extra;
            }
            if (json.discount_extra) {
                this.discount_extra = json.discount_extra
            }
            if (json.tag_ids && json.tag_ids.length) {
                let tag_ids = json.tag_ids[0][2];
                if (tag_ids) {
                    this.set_tags(tag_ids)
                }
            }
            if (json.is_return) {
                this.is_return = json.is_return;
            }
            if (json.combo_item_ids && json.combo_item_ids.length) {
                this.set_combo_bundle_pack(json.combo_item_ids);
            }
            if (json.uom_id) {
                this.uom_id = json.uom_id;
                let unit = this.pos.units_by_id[json.uom_id];
                if (unit) {
                    this.product.uom_id = [unit['id'], unit['name']];
                }
                this.set_unit(this.uom_id)
            }
            if (json.note) {
                this.note = json.note;
            }
            if (json.discount_reason) {
                this.discount_reason = json.discount_reason
            }
            if (json.frequent_buyer_id) {
                this.frequent_buyer_id = json.frequent_buyer_id;
            }
            if (json.lot_ids) {
                this.lot_ids = json.lot_ids;
            }
            if (json.manager_user_id && this.pos.user_by_id && this.pos.user_by_id[json.manager_user_id]) {
                this.manager_user = this.pos.user_by_id[json.manager_user_id]
            }
            if (json.base_price) {
                this.set_unit_price(json.base_price);
                this.base_price = null;
            }
            if (json.selected_combo_items) {
                this.set_dynamic_combo_items(json.selected_combo_items)
            }
            if (json.returned_order_line_id) {
                this.returned_order_line_id = json.returned_order_line_id
            }

            if (json.is_shipping_cost) {
                this.is_shipping_cost = json.is_shipping_cost
            }
            if (json.order_time) {
                this.order_time = json.order_time
            }
            if (json.coupon_program_id) {
                this.coupon_program_id = json.coupon_program_id
            }
            if (json.coupon_id) {
                this.coupon_id = json.coupon_id
            }
            if (json.coupon_ids) {
                this.coupon_ids = json.coupon_ids
            }
            if (json.coupon_program_name) {
                this.coupon_program_name = json.coupon_program_name
            }
            if (json.coupon_code) {
                this.coupon_code = json.coupon_code
            }
            if (json.combo_items) {
                this.combo_items = json.combo_items
            }
            if (json.modifiers) {
                this.modifiers = json.modifiers
            }
            if (json.all_total_discount) {
                this.all_total_discount = json.all_total_discount
            }
            if (json.discount_from_pricelist) {
                this.discount_from_pricelist = json.discount_from_pricelist
            }
            if (json.all_discount_except_pricelist) {
                this.all_discount_except_pricelist = json.all_discount_except_pricelist
            }
            if (json.unit_price_pricelist) {
                this.unit_price_pricelist = json.unit_price_pricelist
            }
            if (json.discount_other_promotion) {
                this.discount_other_promotion = json.discount_other_promotion
            }


            if (json.pos_coupon_id) {
                this.pos_coupon_id = json.pos_coupon_id
            }
            if (json.pos_coupon_reward_discount) {
                this.pos_coupon_reward_discount = json.pos_coupon_reward_discount
            }
            if (json.is_product_coupon) {
                this.is_product_coupon = json.is_product_coupon
            }
            if (json.is_product_coupon_reward) {
                this.is_product_coupon_reward = json.is_product_coupon_reward
            }
            if (json.pos_coupon_reward_description) {
                this.pos_coupon_reward_description = json.pos_coupon_reward_description
            }


        },

        export_as_JSON: function () {
            let json = _super_Orderline.export_as_JSON.apply(this, arguments);
            if (this.promotion) {
                json.promotion = this.promotion;
            }
            if (this.product_attribute_values) {
                json.product_attribute_values = this.product_attribute_values;
            }
            if (this.promotion_gift) {
                json.promotion_gift = this.promotion_gift;
            }
            if (this.promotion_tebus_murah) {
                json.promotion_tebus_murah = this.promotion_tebus_murah;
            }
            if (this.promotion_id) {
                json.promotion_id = this.promotion_id;
            }
            if (this.promotion_ids) {
                json.promotion_ids = this.promotion_ids;
            } else {
                json.promotion_ids = [];
            }
            if (this.promotion_reason) {
                json.promotion_reason = this.promotion_reason;
            }
            if (this.promotion_discount) {
                json.promotion_discount = this.promotion_discount;
            }
            if (this.promotion_stack) {
                json.promotion_stack = this.promotion_stack;
            }
            if (this.promotion_amount) {
                json.promotion_amount = this.promotion_amount;
            }
            if (this.plus_point) {
                json.plus_point = this.plus_point;
            }
            if (this.redeem_point) {
                json.redeem_point = this.redeem_point;
            }
            if (this.reward_id) {
                json.reward_id = json.reward_id;
            }
            if (this.price_extra) {
                json.price_extra = this.price_extra;
            }
            if (this.discount_extra) {
                json.discount_extra = this.discount_extra;
            }
            if (this.base_price) {
                json.base_price = this.base_price;
            }
            if (this.tags && this.tags.length) {
                json.tag_ids = [[6, false, _.map(this.tags, function (tag) {
                    return tag.id;
                })]];
            }
            if (this.get_line_note()) {
                json.note = this.get_line_note();
            }
            if (this.is_return) {
                json.is_return = this.is_return;
            }
            if (this.combo_items && this.combo_items.length) {
                json.combo_item_ids = [];
                for (let n = 0; n < this.combo_items.length; n++) {
                    json.combo_item_ids.push({
                        id: this.combo_items[n].id,
                        quantity: this.combo_items[n].quantity
                    })
                }
            }
            if (this.uom_id) {
                json.uom_id = this.uom_id
            }
            if (this.discount_reason) {
                json.discount_reason = this.discount_reason
            }
            if (this.frequent_buyer_id) {
                json.frequent_buyer_id = this.frequent_buyer_id
            }
            if (this.lot_ids) {
                let pack_lot_ids = json.pack_lot_ids;
                for (let i = 0; i < this.lot_ids.length; i++) {
                    let lot = this.lot_ids[i];
                    pack_lot_ids.push([0, 0, {
                        lot_name: lot['name'],
                        quantity: lot['quantity'],
                        lot_id: lot['id']
                    }]);
                }
                json.pack_lot_ids = pack_lot_ids;
            }
            if (this.manager_user) {
                json.manager_user_id = this.manager_user.id
            }
            if (this.selected_combo_items) {
                json.selected_combo_items = this.selected_combo_items;
            }
            if (this.returned_order_line_id) {
                json.returned_order_line_id = this.returned_order_line_id;
            }
            
            if (this.is_shipping_cost) {
                json.is_shipping_cost = this.is_shipping_cost
            }
            if (this.order_time) {
                json.order_time = this.order_time
            }
            if (this.coupon_program_id) {
                json.coupon_program_id = this.coupon_program_id
            }
            if (this.coupon_id) {
                json.coupon_id = this.coupon_id
            }
            if (this.coupon_ids) {
                json.coupon_ids = this.coupon_ids
            }
            if (this.coupon_program_name) {
                json.coupon_program_name = this.coupon_program_name
            }
            if (this.coupon_code) {
                json.coupon_code = this.coupon_code
            }
            if (this.combo_items) {
                json.combo_items = this.combo_items
            }
            if (this.modifiers) {
                json.modifiers = this.modifiers
            }
            if (this.all_total_discount) {
                json.all_total_discount = this.all_total_discount
            }
            if (this.discount_from_pricelist) {
                json.discount_from_pricelist = this.discount_from_pricelist
            }
            if (this.all_discount_except_pricelist) {
                json.all_discount_except_pricelist = this.all_discount_except_pricelist
            }
            if (this.unit_price_pricelist) {
                json.unit_price_pricelist = this.unit_price_pricelist
            }
            if (this.discount_other_promotion) {
                json.discount_other_promotion = this.discount_other_promotion
            }

            if (this.pos_coupon_id) {
                json.pos_coupon_id = this.pos_coupon_id
            }
            if (this.pos_coupon_reward_discount) {
                json.pos_coupon_reward_discount = this.pos_coupon_reward_discount
            }
            if (this.is_product_coupon) {
                json.is_product_coupon = this.is_product_coupon
            }
            if (this.is_product_coupon_reward) {
                json.is_product_coupon_reward = this.is_product_coupon_reward
            }
            if (this.pos_coupon_reward_description) {
                json.pos_coupon_reward_description = this.pos_coupon_reward_description
            }


            return json;
        },

        clone: function () {
            let orderline = _super_Orderline.clone.call(this);
            orderline.note = this.note;
            orderline.discount_reason = this.discount_reason;
            orderline.uom_id = this.uom_id;
            if (this.combo_item_ids && this.combo_item_ids.length) {
                orderline.set_combo_bundle_pack(this.combo_item_ids);
            }
            orderline.mp_dirty = this.mp_dirty;
            orderline.mp_skip = this.mp_skip;
            orderline.discountStr = this.discountStr;
            orderline.price_extra = this.price_extra;
            orderline.discount_extra = this.discount_extra;
            orderline.discount_reason = this.discount_reason;
            orderline.plus_point = this.plus_point;
            orderline.redeem_point = this.redeem_point;
            orderline.user_id = this.user_id;
            return orderline;
        },

        export_for_printing: function () {
            let receipt_line = _super_Orderline.export_for_printing.apply(this, arguments);
            receipt_line['promotion'] = null;
            receipt_line['promotion_reason'] = null;
            if (this.promotion) {
                receipt_line.promotion = this.promotion;
                receipt_line.promotion_reason = this.promotion_reason;
            }
            if (this.coupon_program_name) {
                receipt_line.coupon_program_name = this.coupon_program_name
            }
            receipt_line['combo_items'] = [];
            receipt_line['variants'] = [];
            receipt_line['tags'] = [];
            receipt_line['addons'] = [];
            receipt_line['note'] = this.note || '';
            receipt_line['combo_items'] = [];
            if (this.modifiers) {
                receipt_line['modifiers'] = this.modifiers;
            }
            if (this.combo_items) {
                receipt_line['combo_items'] = this.combo_items;
            }
            if (this.variants) {
                receipt_line['variants'] = this.variants;
            }
            if (this.tags) {
                receipt_line['tags'] = this.tags;
            }
            if (this.discount_reason) {
                receipt_line['discount_reason'] = this.discount_reason;
            }
            receipt_line['tax_amount'] = this.get_tax() || 0.00;
            if (this.variants) {
                receipt_line['variants'] = this.variants;
            }
            if (this.packaging) {
                receipt_line['packaging'] = this.packaging;
            }
            if (this.product.name_second) {
                receipt_line['name_second'] = this.product.name_second
            }
            if (this.selected_combo_items) {
                receipt_line['selected_combo_items'] = this.selected_combo_items;
            }
            if (this.generic_options) {
                receipt_line['generic_options'] = this.generic_options;
            }

            return receipt_line;
        },

        setProductAttributeValues(valuesSelected) {
            const self = this
            this.product_attribute_values = valuesSelected
            let description = ''
            for (let attribute_id in valuesSelected) {
                let attribute = this.pos.product_attribute_by_id[attribute_id]
                let sub_description = ''
                sub_description += attribute['name'] + ' : '
                let values = []
                valuesSelected[attribute_id].forEach(v_id => {
                    values.push(self.pos.product_attribute_value_by_id[v_id]['name'])
                })
                sub_description += values.join(', ');
                if (description) {
                    description += ` - ${sub_description} `
                } else {
                    description += ` ${sub_description} `
                }

            }
            this.merge = false
            this.full_product_name = null
            this.description = description
            this.trigger('change', this)
        },

        /**
         * Mirror JS method of:
         * compute_all in addons/account/models/account.py
         *
         * Read comments in the python side method for more details about each sub-methods.
         */
        compute_all_without_rounding: function(taxes, price_unit, quantity, currency_rounding, handle_price_include=true) {
            var self = this;

            // 1) Flatten the taxes.

            var _collect_taxes = function(taxes, all_taxes){
                taxes.sort(function (tax1, tax2) {
                    return tax1.sequence - tax2.sequence;
                });
                _(taxes).each(function(tax){
                    if(tax.amount_type === 'group')
                        all_taxes = _collect_taxes(tax.children_tax_ids, all_taxes);
                    else
                        all_taxes.push(tax);
                });
                return all_taxes;
            }
            var collect_taxes = function(taxes){
                return _collect_taxes(taxes, []);
            }

            taxes = collect_taxes(taxes);

            // 2) Deal with the rounding methods

            var round_tax = this.pos.company.tax_calculation_rounding_method != 'round_globally';

            var initial_currency_rounding = currency_rounding;
            if(!round_tax)
                currency_rounding = currency_rounding * 0.00001;

            // 3) Iterate the taxes in the reversed sequence order to retrieve the initial base of the computation.
            var recompute_base = function(base_amount, fixed_amount, percent_amount, division_amount){
                 return (base_amount - fixed_amount) / (1.0 + percent_amount / 100.0) * (100 - division_amount) / 100;
            }

            var base = round_pr(price_unit * quantity, initial_currency_rounding);

            var sign = 1;
            if(base < 0){
                base = -base;
                sign = -1;
            }

            var total_included_checkpoints = {};
            var i = taxes.length - 1;
            var store_included_tax_total = true;

            var incl_fixed_amount = 0.0;
            var incl_percent_amount = 0.0;
            var incl_division_amount = 0.0;

            var cached_tax_amounts = {};
            if (handle_price_include){
                _(taxes.reverse()).each(function(tax){
                    if(tax.include_base_amount){
                        base = recompute_base(base, incl_fixed_amount, incl_percent_amount, incl_division_amount);
                        incl_fixed_amount = 0.0;
                        incl_percent_amount = 0.0;
                        incl_division_amount = 0.0;
                        store_included_tax_total = true;
                    }
                    if(tax.price_include){
                        if(tax.amount_type === 'percent')
                            incl_percent_amount += tax.amount;
                        else if(tax.amount_type === 'division')
                            incl_division_amount += tax.amount;
                        else if(tax.amount_type === 'fixed')
                            incl_fixed_amount += quantity * tax.amount
                        else{
                            var tax_amount = self._compute_all(tax, base, quantity);
                            incl_fixed_amount += tax_amount;
                            cached_tax_amounts[i] = tax_amount;
                        }
                        if(store_included_tax_total){
                            total_included_checkpoints[i] = base;
                            store_included_tax_total = false;
                        }
                    }
                    i -= 1;
                });
            }

            var total_excluded = round_pr(recompute_base(base, incl_fixed_amount, incl_percent_amount, incl_division_amount), initial_currency_rounding);
            var total_included = total_excluded;

            // 4) Iterate the taxes in the sequence order to fill missing base/amount values.

            base = total_excluded;

            var skip_checkpoint = false;

            var taxes_vals = [];
            i = 0;
            var cumulated_tax_included_amount = 0;
            _(taxes.reverse()).each(function(tax){
                if(!skip_checkpoint && tax.price_include && total_included_checkpoints[i] !== undefined){
                    var tax_amount = total_included_checkpoints[i] - (base + cumulated_tax_included_amount);
                    cumulated_tax_included_amount = 0;
                }else
                    var tax_amount = self._compute_all(tax, base, quantity, true);

                tax_amount = round_pr(tax_amount, currency_rounding);

                if(tax.price_include && total_included_checkpoints[i] === undefined)
                    cumulated_tax_included_amount += tax_amount;

                taxes_vals.push({
                    'id': tax.id,
                    'name': tax.name,
                    'amount': sign * tax_amount,
                    'base': sign * round_pr(base, currency_rounding),
                });

                if(tax.include_base_amount){
                    base += tax_amount;
                    if(!tax.price_include)
                        skip_checkpoint = true;
                }

                total_included += tax_amount;
                i += 1;
            });

            return {
                'taxes': taxes_vals,
                'total_excluded': sign * total_excluded,
                'total_included': sign * total_included,
            }
        },

        set_price_by_pricelist() {
            this.price_by_pricelist = {}
            const pricelists = this.pos.pricelists
            for (let i = 0; i < pricelists.length; i++) {
                let pricelist = pricelists[i]
                this.price_by_pricelist[pricelist.id] = this.product.get_price(pricelist, this.quantity, 0, this.uom_id || this.product.uom_id[0])
            }
        },

        get_lot_lines: function () {
            return this.pack_lot_lines.models;
        },

        get_display_price: function () {
            const price = _super_Orderline.get_display_price.apply(this, arguments);
            return this.get_price_with_tax();
            // if (this.pos.config.display_sale_price_within_tax) {
            //     return this.get_price_with_tax();
            // } else {
            //     return price
            // }
        },

        getPackLotLinesToEdit: function (isAllowOnlyOneLot) {
            let lotAdded = _super_Orderline.getPackLotLinesToEdit.apply(this, arguments);
            return lotAdded
        },

        set_price_extra: function (price_extra) {
            _super_Orderline.set_price_extra.apply(this, arguments);
        },

        get_pricelist_max_price: function (pricelist, quantity, product_price) {
            let self = this;
            let price = product_price;
            let pricelist_items = [];
            let category_ids = [];
            let category = this.product.categ;
            while (category) {
                category_ids.push(category.id);
                category = category.parent;
            }
            for (let i = 0; i < pricelist.items.length; i++) {
                let item = pricelist.items[i];
                if ((item.compute_price == 'formula') &&
                    (!item.product_tmpl_id || item.product_tmpl_id[0] === self.product_tmpl_id) &&
                    (!item.product_id || item.product_id[0] === self.id) &&
                    (!item.categ_id || _.contains(category_ids, item.categ_id[0])) &&
                    (!item.pos_category_id || _.contains(pos_category_ids, item.pos_category_id[0])) &&
                    (!item.date_start || moment(item.date_start).isSameOrBefore(date)) &&
                    (!item.date_end || moment(item.date_end).isSameOrAfter(date))) {
                    pricelist_items.push(item)
                }
            }
            if (pricelist_items.length == 0) {
                return 0.0;
            }
            _.find(pricelist_items, function (rule) {
                if (rule.min_quantity && quantity < rule.min_quantity) {
                    return 0.0;
                }
                if (rule.base === 'pricelist') {
                    price = self.product.get_price(rule.base_pricelist, quantity);
                } else if (rule.base === 'standard_price') {
                    price = self.standard_price;
                }
                if (rule.compute_price === 'fixed') {
                    return rule.fixed_price;
                } else if (rule.compute_price === 'percentage') {
                    price = price - (price * (rule.percent_price / 100));
                    return price;
                } else {
                    let price_limit = price;
                    price = price - (price * (rule.price_discount / 100));
                    if (rule.price_round) {
                        price = round_pr(price, rule.price_round);
                    }
                    if (rule.price_surcharge) {
                        price += rule.price_surcharge;
                    }
                    if (rule.price_max_margin) {
                        let margin_amount = price_limit * rule.price_max_margin/100.0;
                        price = Math.max(price, price_limit + margin_amount);
                    } else if (rule.price_min_margin) {
                        let margin_amount = price_limit * rule.price_min_margin/100.0;
                        price = Math.max(price, price_limit + margin_amount);
                    }
                    return price;
                }
                return price;
            });
            return price;
        },

        set_unit_price: function (price) {
            let pricelist_price = this.product.get_price(this.order.pricelist, this.quantity);
            let product_max_price = this.get_pricelist_max_price(this.order.pricelist, this.quantity, pricelist_price);
            if (product_max_price !== 0.0 && price > product_max_price){
                this.pos.alert_message({
                    title: _t('Error'),
                    body: this.product.display_name + _t(' : Product price is exceeding the pricelist max margin! Hence we change the price to pricelist price again.')
                });
                price = pricelist_price;
                NumberBuffer.reset();
            }
            if (this.pos.the_first_load == false && this.product.refundable == false && parseFloat(price) < 0) {
                return this.pos.alert_message({
                    title: _t('Error'),
                    body: this.product.display_name + _t(' Refundable is Unactive, not possible Discount it')
                });
            }
            _super_Orderline.set_unit_price.apply(this, arguments);
            if (this.coupon_ids && !this.pos.the_first_load) {
                this.pos.rpc({
                    model: 'coupon.generate.wizard',
                    method: 'remove_giftcards',
                    args: [[], this.coupon_ids],
                })
                this.coupon_ids = null;
                this.pos.alert_message({
                    title: this.pos.env._t('Alert'),
                    body: this.pos.env._t('Gift cards created before just removed')
                })
            }
        },
        display_discount_policy: function () {
            if (this.order.pricelist) {
                return _super_Orderline.display_discount_policy.apply(this, arguments);
            } else {
                return null
            }
        },
        get_margin: function () {
            if (this.product.standard_price <= 0) {
                return 100
            } else {
                return (this.price - this.product.standard_price) / this.product.standard_price * 100
            }
        },
        set_multi_lot: function (lot_ids) {
            let lot_selected = [];
            for (let i = 0; i < lot_ids.length; i++) {
                let lot = lot_ids[i];
                let lot_record = this.pos.lot_by_id[lot['id']];
                if (lot_record && lot['quantity'] && lot['quantity'] > 0) {
                    lot['name'] = lot_record['name'];
                    lot_selected.push(lot)
                } else {
                    return Gui.showPopup('ConfirmPopup', {
                        title: _t('Warning'),
                        body: _t('Lot ' + lot_record.id + ' does not exist. Backend system have removed it, it not possible made return with Lots'),
                        disableCancelButton: true,
                    })
                }
            }
            this.lot_ids = lot_selected;
            this.trigger('change', this);
            this.trigger('trigger_update_line');
        },
        set_line_note: function (note) {
            this.note = note;
            this.trigger('change', this);
        },
        get_line_note: function () {
            return this.note
        },
        // TODO: this is combo bundle pack
        set_combo_bundle_pack: function (combo_item_ids) {
            // TODO: combo_item_ids is dict value have id is id of combo item, and quantity if quantity of combo item
            let price_extra = 0;
            this.combo_items = [];
            for (let n = 0; n < combo_item_ids.length; n++) {
                let combo_item_id = combo_item_ids[n].id;
                let quantity = combo_item_ids[n].quantity;
                let combo_item = this.pos.combo_item_by_id[combo_item_id];
                if (combo_item) {
                    this.combo_items.push({
                        id: combo_item['id'],
                        quantity: quantity,
                        price_extra: combo_item.price_extra,
                        product_id: combo_item.product_id,
                    });
                    price_extra += combo_item.price_extra * quantity;
                }
            }
            if (price_extra) {
                this.price_extra = price_extra;
            }
            this.trigger('change', this);
        },
        set_tags: function (tag_ids) {
            this.tags = [];
            for (let index in tag_ids) {
                let tag_id = tag_ids[index];
                let tag = this.pos.tag_by_id[tag_id];
                if (tag) {
                    this.tags.push(tag)
                }
            }
            if (this.tags.length) {
                this.trigger('change', this);
            }
        },
        get_price_included_tax_by_price_of_item: function (price_unit, quantity) {
            let taxtotal = 0;
            let product = this.get_product();
            let taxes_ids = product.taxes_id;
            let taxes = this.pos.taxes;
            let taxdetail = {};
            let product_taxes = [];

            _(taxes_ids).each(function (el) {
                product_taxes.push(_.detect(taxes, function (t) {
                    return t.id === el;
                }));
            });

            let all_taxes = this.compute_all(product_taxes, price_unit, quantity, this.pos.currency.rounding);
            _(all_taxes.taxes).each(function (tax) {
                taxtotal += tax.amount;
                taxdetail[tax.id] = tax.amount;
            });

            return {
                "priceWithTax": all_taxes.total_included,
                "priceWithoutTax": all_taxes.total_excluded,
                "tax": taxtotal,
                "taxDetails": taxdetail,
            };
        },
        set_unit_price_with_currency: function (price, currency) {
            if (currency.id != this.pos.currency.id) {
                if (!this.base_price) {
                    this.base_price = this.price;
                    this.price = price * 1 / currency.rate;
                } else {
                    this.price = this.base_price * 1 / currency.rate;
                }
            } else {
                if (this.base_price) {
                    this.price = this.base_price;
                }
            }
            this.currency = currency;
            this.trigger('change', this);

        },
        has_dynamic_combo_active: function () {
            let pos_categories_combo = _.filter(this.pos.pos_categories, function (categ) {
                return categ.is_category_combo
            });
            if (pos_categories_combo.length > 0) {
                return true
            } else {
                return false
            }
        },
        has_bundle_pack: function () {
            if (this.combo_items && this.combo_items.length) {
                return true
            } else {
                return false
            }
        },
        has_valid_product_lot: function () { //  TODO: is line multi lots or not
            if (this.lot_ids && this.lot_ids.length) {
                return true
            } else {
                return _super_Orderline.has_valid_product_lot.apply(this, arguments);
            }
        },
        has_input_return_reason: function () {
            if (this.tags && this.tags.length) {
                let reason = _.find(this.tags, function (reason) {
                    return reason.is_return_reason;
                });
                if (reason) {
                    return true
                } else {
                    return false
                }
            } else {
                return false
            }
        },
        has_multi_unit: function () {
            let product = this.product;
            let product_tmpl_id;
            if (product.product_tmpl_id instanceof Array) {
                product_tmpl_id = product.product_tmpl_id[0]
            } else {
                product_tmpl_id = product.product_tmpl_id;
            }
            let uom_items = this.pos.uoms_prices_by_product_tmpl_id[product_tmpl_id];
            if (!uom_items) {
                return false;
            }
            let base_uom_id = product['base_uom_id'];
            if (base_uom_id) {
                let base_uom = this.pos.uom_by_id[base_uom_id[0]];
                base_uom['price'] = product.lst_price;
                base_uom['uom_id'] = [base_uom['id'], base_uom['name']];
                uom_items = uom_items.concat(base_uom)
            }
            if (uom_items.length > 0) {
                return true
            }
        },
        set_taxes: function (tax_ids) { // TODO: add taxes to order line
            if (this.product) {
                this.product.taxes_id = tax_ids;
                this.trigger('change', this);
            }
        },
        get_unit_price: function () {
            let unit_price = _super_Orderline.get_unit_price.apply(this, arguments);
            if (this.price_extra) {
                unit_price += this.price_extra;
            }
            if (this.discount_extra && this.discount_extra > 0 && this.discount_extra <= 100) {
                unit_price = unit_price - (unit_price * this.discount_extra / 100)
            }
            if (this.promotion_id) {
                if (this.promotion_amount > 0) {
                    unit_price = unit_price - this.promotion_amount
                }
            }
            return unit_price;
        },
        get_product_price_quantity_item: function () {
            let product_tmpl_id = this.product.product_tmpl_id;
            if (product_tmpl_id instanceof Array) {
                product_tmpl_id = product_tmpl_id[0]
            }
            let product_price_quantities = this.pos.price_each_qty_by_product_tmpl_id[product_tmpl_id];
            if (product_price_quantities) {
                let product_price_quanty_temp = null;
                for (let i = 0; i < product_price_quantities.length; i++) {
                    let product_price_quantity = product_price_quantities[i];
                    if (this.quantity >= product_price_quantity['quantity']) {
                        if (!product_price_quanty_temp) {
                            product_price_quanty_temp = product_price_quantity;
                        } else {
                            if (product_price_quanty_temp['quantity'] <= product_price_quantity['quantity']) {
                                product_price_quanty_temp = product_price_quantity;
                            }
                        }
                    }
                }
                return product_price_quanty_temp;
            }
            return null
        },
        has_variants: function () {
            if (this.variants && this.variants.length && this.variants.length > 0) {
                return true
            } else {
                return false
            }
        },
        set_product_lot: function (product) {
            if (product) { // first install may be have old orders, this is reason made bug
                return _super_Orderline.set_product_lot.apply(this, arguments);
            } else {
                return null
            }
        },
        // if config product tax id: have difference tax of other company
        // but when load data account.tax, pos default only get data of current company
        // and this function return some item undefined
        get_taxes: function () {
            const taxes = _super_Orderline.export_for_printing.apply(this, arguments);
            let new_taxes = [];
            let taxes_ids = this.get_product().taxes_id;
            for (let i = 0; i < taxes_ids.length; i++) {
                if (this.pos.taxes_by_id[taxes_ids[i]]) {
                    new_taxes.push(this.pos.taxes_by_id[taxes_ids[i]]);
                }
            }
            return new_taxes;
        },
        get_packaging: function () {
            if (!this || !this.product || !this.pos.packaging_by_product_id) {
                return false;
            }
            if (this.pos.packaging_by_product_id[this.product.id]) {
                return true
            } else {
                return false
            }
        },
        get_packaging_added: function () {
            if (this.packaging) {
                return this.packaging;
            } else {
                return false
            }
        },
        set_discount_to_line: function (discount) {
            if (discount != 0) {
                this.discount_reason = discount.reason;
                this.set_discount(discount.amount);
            } else {
                this.discount_reason = null;
                this.set_discount(0);
            }
        },
        change_unit: function (unit) {
            this.pos.db.clear_cache_product_price_by_id('product.product', this.product.id);
            
            this.set_unit(unit.uom_id[0], unit.price);

            this.pos.db.clear_cache_product_price_by_id('product.product', this.product.id);
            this.product.get_price_with_tax(); // update [cache_product_price]
            return true;
        },
        set_unit: function (uom_id) {
            if (!this.pos.the_first_load && !uom_id) {
                return Gui.showPopup('ErrorPopup', {
                    title: _t('Error !!!'),
                    body: _t('Unit for set not found')
                })
            }
            this.uom_id = uom_id;
            const newPrice = this.product.get_price(this.pos._get_active_pricelist(), this.quantity, 0, this.uom_id);
            this.set_unit_price(newPrice);
            this.price_manually_set = true;
            return true;
        },
        get_units_price: function () {
            // TODO: each product we have multi unit (uom_ids), if current pricelist have set price for each unit, We return back all units available and price
            let units = [];
            if (!this.order.pricelist) {
                return units
            }
            let pricelist = this.order.pricelist;
            if (this.product.uom_ids && this.product.uom_ids.length) {
                let date = moment().startOf('day');
                let category_ids = [];
                let category = this.product.categ;
                while (category) {
                    category_ids.push(category.id);
                    category = category.parent;
                }
                for (let i = 0; i < this.product.uom_ids.length; i++) {
                    let uom_id = this.product.uom_ids[i];
                    let uom = this.pos.uom_by_id[uom_id];
                    let uom_has_price_included_pricelist = false;
                    for (let n = 0; n < pricelist.items.length; n++) {
                        let item = pricelist.items[n];
                        if ((!item.product_tmpl_id || item.product_tmpl_id[0] === this.product.product_tmpl_id) &&
                            (!item.product_id || item.product_id[0] === this.product.id) &&
                            (!item.categ_id || _.contains(category_ids, item.categ_id[0])) &&
                            (!item.date_start || moment(item.date_start).isSameOrBefore(date)) &&
                            (!item.date_end || moment(item.date_end).isSameOrAfter(date))) {
                            if (item.product_id && item.product_id[0] == this.product.id && item.uom_id && item.uom_id[0] == uom_id) {
                                uom_has_price_included_pricelist = true
                                break;
                            }
                        }
                    }
                    if (uom && uom_has_price_included_pricelist) {
                        let price = this.product.get_price(this.order.pricelist, 1, 0, uom_id);
                        units.push({
                            uom: uom,
                            price: price
                        })
                    }
                }
            }
            return units
        },
        is_package: function () {
            if (!this.pos.packaging_by_product_id) {
                return false
            }
            let packagings = this.pos.packaging_by_product_id[this.product.id];
            if (packagings) {
                return true
            } else {
                return false
            }
        },
        is_cross_selling: function () {
            let self = this;
            let cross_items = _.filter(this.pos.cross_items, function (cross_item) {
                return cross_item['product_tmpl_id'][0] == self.product.product_tmpl_id;
            });
            if (cross_items.length) {
                return true
            } else {
                return false
            }
        },
        change_cross_selling: function () {
            let self = this;
            let cross_items = _.filter(this.pos.cross_items, function (cross_item) {
                return cross_item['product_tmpl_id'][0] == self.product.product_tmpl_id;
            });
            if (cross_items.length) {
                Gui.showPopup('popup_cross_selling', {
                    title: _t('Please, Suggest Customer buy more products bellow'),
                    widget: this,
                    cross_items: cross_items
                });
            } else {
                this.pos.alert_message({
                    title: _t('Warning'),
                    body: 'You not active cross selling or product have not items cross selling'
                });
            }
        },
        get_number_of_order: function () {
            let uid = this.uid;
            let order = this.order;
            for (let i = 0; i < order.orderlines.models.length; i++) {
                let line = order.orderlines.models[i];
                if (line.uid == uid) {
                    return i + 1
                }
            }
        },
        get_price_without_quantity: function () {
            if (this.quantity != 0) {
                return this.get_price_with_tax() / this.quantity
            } else {
                return 0
            }
        },

        get_line_image: function () {
            const product = this.product;
            return `/web/image?model=product.product&field=image_128&id=${product.id}&write_date=${product.write_date}&unique=1`;
        },

        is_has_tags: function () {
            if (!this.tags || this.tags.length == 0) {
                return false
            } else {
                return true
            }
        },
        is_multi_variant: function () {
            let variants = this.pos.variant_by_product_tmpl_id[this.product.product_tmpl_id];
            if (!variants) {
                return false
            }
            if (variants.length > 0) {
                return true;
            } else {
                return false;
            }
        },
        // TODO: method return disc value each line
        get_price_discount: function () {
            const allPrices = this.get_all_prices();
            return allPrices['priceWithTaxBeforeDiscount'] - allPrices['priceWithTax']
        },
        get_unit: function () {
            if (!this.uom_id) {
                let unit_id = this.product.uom_id;
                if (!unit_id) {
                    return undefined;
                }
                unit_id = unit_id[0];
                if (!this.pos) {
                    return undefined;
                }
                let unit = this.pos.units_by_id[unit_id];
                return unit;
            } else {
                let unit_id = this.uom_id;
                let unit = this.pos.units_by_id[unit_id];
                return unit;
            }
        },
        is_multi_unit_of_measure: function () {
            let uom_items = this.pos.uoms_prices_by_product_tmpl_id[this.product.product_tmpl_id];
            if (!uom_items) {
                return false;
            }
            if (uom_items.length > 0) {
                return true;
            } else {
                return false;
            }
        },
        
        // TODO: this is dynamic combo ( selected_combo_items is {product_id: quantity} )
        set_dynamic_combo_items: function (selected_combo_items) {
            let price_extra = 0;
            for (let product_id in selected_combo_items) {
                let product = this.pos.db.product_by_id[parseInt(product_id)];
                price_extra += product['combo_price'] * selected_combo_items[product_id];
            }
            this.selected_combo_items = selected_combo_items;
            if (price_extra) {
                this.price_extra = price_extra;
            }
            this.trigger('change', this);
        },
        is_combo: function () {
            for (let product_id in this.selected_combo_items) {
                return true
            }
            return false
        },
        has_combo_item_tracking_lot: function () {
            let tracking = false;
            for (let i = 0; i < this.pos.combo_items.length; i++) {
                let combo_item = this.pos.combo_items[i];
                if (combo_item['tracking']) {
                    tracking = true;
                }
            }
            return tracking;
        },

        product_status: function () {
            return this.product.to_weight;
        },

        set_quantity: function (quantity, keep_price) {
            if(typeof quantity == 'undefined'){
                quantity = 0;
            }
            if (this.pos.the_first_load == false && this.product.refundable == false && parseFloat(quantity) < 0) {
                return Gui.showPopup('ErrorPopup', {
                    title: _t('Error'),
                    body: this.product.display_name + _t(' Refundable is Unactive, not possible Discount it')
                })
            }
            let self = this;
            let update_combo_items = false;
            if (this.uom_id || this.redeem_point) {
                keep_price = 'keep price because changed uom id or have redeem point'
            }
            let qty_will_set = parseFloat(quantity);
            if (qty_will_set <= 0) {
                this.selected_combo_items = {}
                update_combo_items = true
            } else {
                for (let product_id in this.selected_combo_items) {
                    let qty_of_combo_item = this.selected_combo_items[product_id]
                    let new_qty = qty_will_set / this.quantity * qty_of_combo_item;
                    this.selected_combo_items[product_id] = new_qty
                    update_combo_items = true;
                }
            }
            let res = _super_Orderline.set_quantity.call(this, quantity, keep_price); // call style change parent parameter : keep_price
            if (update_combo_items) {
                this.set_dynamic_combo_items(this.selected_combo_items)
            }
            if (this.combo_items && this.pos.config.screen_type != 'kitchen') { // if kitchen screen, no need reset combo items
                this.trigger('change', this);
            }
            let get_product_price_quantity = this.get_product_price_quantity_item(); // product price filter by quantity of cart line. Example: buy 1 unit price 1, buy 10 price is 0.5
            if (get_product_price_quantity) {
                setTimeout(function () {
                    self.syncing = true;
                    self.set_unit_price(get_product_price_quantity['price_unit']);
                    self.syncing = false;
                }, 500)
            }
            let order = this.order;
            let orderlines = order.orderlines.models;
            if (!order.fiscal_position || orderlines.length != 0) {
                for (let i = 0; i < orderlines.length; i++) { // reset taxes_id of line
                    orderlines[i]['taxes_id'] = [];
                }
            }
            if (order.fiscal_position && orderlines.length) {
                let fiscal_position = order.fiscal_position;
                let fiscal_position_taxes_by_id = fiscal_position.fiscal_position_taxes_by_id
                if (fiscal_position_taxes_by_id) {
                    for (let number in fiscal_position_taxes_by_id) {
                        let fiscal_tax = fiscal_position_taxes_by_id[number];
                        let tax_src_id = fiscal_tax.tax_src_id;
                        let tax_dest_id = fiscal_tax.tax_dest_id;
                        if (tax_src_id && tax_dest_id) {
                            for (let i = 0; i < orderlines.length; i++) { // reset taxes_id of line
                                orderlines[i]['taxes_id'] = [];
                            }
                            for (let i = 0; i < orderlines.length; i++) { // append taxes_id of line
                                let line = orderlines[i];
                                let product = line.product;
                                let taxes_id = product.taxes_id;
                                for (let number in taxes_id) {
                                    let tax_id = taxes_id[number];
                                    if (tax_id == tax_src_id[0]) {
                                        orderlines[i]['taxes_id'].push(tax_dest_id[0]);
                                    }
                                }
                            }
                        }
                    }
                } else {
                    for (let i = 0; i < orderlines.length; i++) { // reset taxes_id of line
                        orderlines[i]['taxes_id'] = [];
                    }
                }
            }
            if (this.coupon_ids && !this.pos.the_first_load) {
                this.pos.rpc({
                    model: 'coupon.generate.wizard',
                    method: 'remove_giftcards',
                    args: [[], this.coupon_ids],
                })
                this.coupon_ids = null;
                this.pos.alert_message({
                    title: this.pos.env._t('Alert'),
                    body: this.pos.env._t('Gift cards created before just removed')
                })
            }
            if (this.product.open_price && !this.restoring) {
                this._openPrice()
            }
            return res;
        },

        async _openPrice() {
            let {confirmed, payload: number} = await Gui.showPopup('NumberPopup', {
                'title': _t('What Price of Item ?'),
                'startingValue': 0,
            });
            if (confirmed) {
                this.set_unit_price(number);
            }
        },

        set_selected: function (selected) {
            _super_Orderline.set_selected.apply(this, arguments);
        },



        async set_discount(discount) {
            if (this.pos.the_first_load == false && this.product.discountable == false) {
                return this.pos.alert_message({
                    title: _t('Error'),
                    body: this.product.display_name + _t(' discountable is Unactive, not possible Discount it')
                });
            }
            if (parseFloat(discount) == 0) {
                return _super_Orderline.set_discount.apply(this, arguments);
            }
            if (!this.pos.the_first_load && this.pos.config.discount_limit && discount > this.pos.config.discount_limit_amount) {
                let validate = await this.pos._validate_action(_t(' Need set Discount: ') + discount + ' % .');
                if (!validate) {
                    return this.pos.alert_message({
                        title: _t('Error'),
                        body: _t('Your discount just set bigger than Discount limit % (POS Setting), and required Manager Approve it')
                    });
                }
            }
            _super_Orderline.set_discount.apply(this, arguments);
        },

        // Handle discount set on Numpad | Manual discount by Numpad/Keypad
        async set_discount_from_numpad(discount) {
            var parsed_discount = isNaN(parseFloat(discount)) ? 0 : field_utils.parse.float('' + discount);
            var disc = Math.min(Math.max(parsed_discount || 0, 0),100);

            if (this.pos.the_first_load == false && this.product.discountable == false) {
                return this.pos.alert_message({
                    title: _t('Error'),
                    body: this.product.display_name + _t(' discountable is Unactive, not possible Discount it')
                });
            }
            if (!this.pos.the_first_load && this.pos.config.discount_limit && disc > this.pos.config.discount_limit_amount) {
                let validate = await this.pos._validate_action(_t(' Need set Discount: ') + disc + ' % .');
                if (!validate) {
                    return this.pos.alert_message({
                        title: _t('Error'),
                        body: _t('Your discount just set bigger than Discount limit % (POS Setting), and required Manager Approve it')
                    });
                }
            }
            let values = { 'value': disc,'type': 'percentage'};
            if(this.discount_other_promotion){
                this.discount_other_promotion['discount_from_numpad'] = values;
            }else{
                this.discount_other_promotion = { 'discount_from_numpad': values };
            }
            this.trigger('change', this);
        },


        get_full_product_name: function () {
            if (this.full_product_name) {
                var full_name = this.full_product_name
                if (this.promotion_gift){
              
                    full_name = '(Free Item) '+ full_name
                
            }
                return full_name
            }
            var full_name = this.product.display_name;
            if (this.description) {
                full_name += ` (${this.description})`;
            }
            if (this.promotion_gift){
              
                    full_name = '(Free Item) '+ full_name
                
            }
            return full_name;
        },
        get_orderline_product_name: function () {
            if(this.pos_coupon_reward_description){
                return this.pos_coupon_reward_description;
            }
            if(this.pos.config && this.pos.config.display_product_name_without_product_code){
                let full_name = this.product.display_name;
                full_name = full_name.replace(/[\[].*?[\]] */, '');
                if(this.product.default_code){
                    full_name = this.product.display_name.replace('['+this.product.default_code+'] ', '');
                }
                if (this.description) {
                    full_name += ` (${this.description})`;
                }
                if (this.promotion_gift){
                    full_name = '(Free Item) '+ full_name
                }
           
                return full_name;
            }
            var full_name = this.get_full_product_name();
            return full_name;
        },
        can_be_merged_with: function (orderline) {
            let merge = _super_Orderline.can_be_merged_with.apply(this, arguments);
            if (orderline.weight_scale){
                return false
            }
            if( this.get_unit() !== orderline.get_unit()){    //only orderline of the same product can be merged
                return false;
            }
            if (orderline.promotion || orderline.variants || orderline.is_return || orderline.discount_extra || orderline.price_extra || orderline['note'] || orderline['combo_items'] || orderline.product.is_combo || orderline.is_return || orderline.coupon_program_id || orderline.coupon_ids || orderline.coupon_id) {
                return false;
            }
            if (orderline && orderline.product && orderline.product.pos_categ_id && orderline.mp_dirty) { // if product have category is main, not allow merge
                const posCategory = this.pos.pos_category_by_id[orderline.product.pos_categ_id[0]]
                if (posCategory && posCategory['category_type'] == 'main') {
                    return false;
                }
            }
            if (orderline && orderline['product']['open_price']) {
                return false
            }
            return merge
        },
        // returns the discount [0,100]%
        get_all_taxes_new: function (price) {
            let tax_amount = 0;
            var self = this
            var line = self
            var taxes =  this.pos.taxes;
            var all_taxes = false
            var taxes_ids = _.filter(self.product.taxes_id, t => t in self.pos.taxes_by_id);
            if(taxes_ids){
                var product_taxes = [];
                var taxtotal = 0;
                var tax_included = 0
                _(taxes_ids).each(function(el){
                    var tax = _.detect(taxes, function(t){
                        return t.id === el;
                    });
                    product_taxes.push.apply(product_taxes, [tax]);
                });
                product_taxes = _.uniq(product_taxes, function(tax) { return tax.id; });
                all_taxes = line.compute_all_without_rounding(product_taxes, price, 1,0.0000001);
                _(all_taxes.taxes).each(function(tax) {
                    var taxdetail =  taxes.filter(p => p.id == tax.id) 
                    if(taxdetail){
                        if(taxdetail[0].price_include){
                            tax_included+=tax.amount
                        }
                    }
                });
                all_taxes['included_only'] = tax_included
            }   
            return all_taxes

        },
        get_real_total_w_discount: function () {
            let additional_cost = this.get_additional_cost() || 0;
            return ((this.get_unit_price() + additional_cost + this.price_extra) * this.get_quantity())  - this.get_all_discount() 
        },

        get_price_unit_w_pricelist_before_tax: function () {
            //TO DO : Count price unit w pricelist and w/o tax
            var price = this.get_price_with_pricelist()
            var detail_tax = this.get_all_taxes_new(price)
            if (detail_tax){
                price = detail_tax['total_excluded']
            }
            return price
        },

        get_price_unit_w_pricelist_after_tax: function () {
            //TO DO : Count price unit w pricelist and w tax
            var price = this.get_price_with_pricelist()
            var detail_tax = this.get_all_taxes_new(price)
            if (detail_tax){
                price = detail_tax['total_included']
            }
            return price
        },

        get_price_with_pricelist: function () {
            var price = this.price
            var rounding = this.pos.currency.rounding;
            var pricelistOfOrder = this.pos._get_active_pricelist();
            var qty = this.get_quantity();
            var originprice = round_pr(this.product.get_price(pricelistOfOrder,qty),rounding);
            var datapp = this.product.get_price_with_pricelist(pricelistOfOrder,qty);
            var pricelistprice = round_pr(datapp[0],rounding);
            if(!this.is_return){
                if(this.price == originprice && originprice!=pricelistprice){
                    price = pricelistprice;
                }
            }
            let additional_cost = this.get_additional_cost();
            if(additional_cost){
                price += additional_cost;
            }
            return price;
        },
        get_total_wo_tax_after_pricelist: function () {
            //To do : untuk hitung semua nominal total tanpa tax per line setelah pricelist
            var total = this.get_price_with_pricelist() * this.get_quantity()
            var taxes = this.get_all_taxes_new(total)
            if(taxes){
                total = taxes['total_excluded']
            }
            return total
        },



        get_all_discount: function () {
            //To do : untuk hitung semua nominal diskon per line
            var self = this;
            var quantity = this.get_quantity();
            var diff_price = 0;
            var unit_price_pricelist = 0;
            var this_price = this.price;
            var first_first = this_price;

            // TODO: Include Tax when calculate Discount (Price + Tax)
            var all_taxes = self.get_all_taxes_new(this_price)
            var discount = 0;
            var tax_discount_policy = this.pos.company.tax_discount_policy;
            var rounding = this.pos.currency.rounding;
            var include_tax_only = 0;
            if (tax_discount_policy !=' untax' && all_taxes){
                include_tax_only =round_pr( all_taxes['included_only'] ,rounding)
                first_first = round_pr(all_taxes['total_excluded'] + include_tax_only, rounding)
            }
            if (tax_discount_policy == 'untax' && all_taxes){
                first_first = round_pr(all_taxes['total_excluded'], rounding)
            }

            first_first = first_first * quantity;

            //TODO: additional cost for BOM and Combo
            let additional_cost = this.get_additional_cost_x_quantity();
            if(additional_cost){
                first_first += additional_cost;
            }

            /////////////////////////////////pos.global.discount/////////////////////////
            if(this.discount_other_promotion){
                if('pos.global.discount' in this.discount_other_promotion){
                    var pos_global_discount = this.discount_other_promotion['pos.global.discount']
                    var tmp_price = (first_first - diff_price)*(pos_global_discount/100)
                    diff_price+=tmp_price

                }
            }
            /////////////////////////////////////////////////////////////////////////////

            ///////////////////////////////////discount_pc///////////////////////////////
            if(this.discount_other_promotion){
                if('discount_pc' in this.discount_other_promotion){
                    var pos_global_discount = this.discount_other_promotion['discount_pc']
                    var tmp_price = (first_first - diff_price)*(pos_global_discount/100)
                    diff_price+=tmp_price

                }
            }
            /////////////////////////////////////////////////////////////////////////////

            ///////////////////////////////////Manual discount by Numpad/Keypad//////////
            // if(this.discount){
            //     var line_discount = this.discount
            //     var tmp_price = (first_first - diff_price)*(line_discount/100)
            //     diff_price+=tmp_price
            // }

            if(this.discount_other_promotion){
                if('discount_from_numpad' in this.discount_other_promotion){
                    var discount_from_numpad = this.discount_other_promotion['discount_from_numpad'];
                    var tmp_price = (first_first - diff_price)*(discount_from_numpad['value']/100);
                    diff_price+=tmp_price;

                }
            }
            /////////////////////////////////////////////////////////////////////////////

            ///////////////////////////////PROMOTION/////////////////////////////////////
             if(this.promotion_stack){
                let real_discount = 0;
                let base_price = this_price * quantity;
                let total_discount = base_price; 
                let promotion_stacks = [];
                for(let promotion_id in this.promotion_stack){
                    promotion_stacks.push(this.promotion_stack[promotion_id]);
                }
                promotion_stacks = promotion_stacks.sort((a, b) => a.sequence - b.sequence);

                for(let promotion of promotion_stacks){
                    let price_discount = total_discount * (promotion.discount/100);
                    let amount_discount_percentage = price_discount / base_price;
                    real_discount += amount_discount_percentage;
                    total_discount = total_discount - price_discount; 
                    let amount_discount = (first_first - diff_price) * ((amount_discount_percentage * 100)/100); // tmp_price

                    this.promotion_stack[promotion.id].data = {
                        'price': total_discount,
                        'amount': amount_discount,
                        'amount_percentage': amount_discount_percentage,
                    }
                }
                let promotion_discount = real_discount * 100;
                let tmp_price = (first_first - diff_price)*(promotion_discount/100);
                diff_price+=tmp_price
            }
            /////////////////////////////////////////////////////////////////////////////

            //////////////////////////////////////////voucher////////////////////////////
            if(this.discount_other_promotion){
                if('voucher' in this.discount_other_promotion){
                    var voucher_discount = this.discount_other_promotion['voucher']
                    var tmp_price = (first_first - diff_price)*(voucher_discount['value']/100)
                    diff_price+=tmp_price

                }
            }
            /////////////////////////////////////////////////////////////////////////////

            //////////////////////////////////////////coupon////////////////////////////
            if(this.discount_other_promotion){
                if('coupon' in this.discount_other_promotion){
                    var coupon_discount = this.discount_other_promotion['coupon']
                    var tmp_price = (first_first - diff_price)*(coupon_discount['value']/100)
                    diff_price+=tmp_price

                }
            }
            /////////////////////////////////////////////////////////////////////////////
            
            /////////////////////////////////////////////////////////////////////////////
            // if(diff_price&&first_first){
            //     discount = (diff_price / (first_first-include_tax_only))*100
            //     discount = Math.round(discount * 100) / 100
            // }
            this.all_total_discount = diff_price;
            this.unit_price_pricelist = unit_price_pricelist;
            return diff_price
        },

        get_all_total_discount: function () {
            // total discount per order line
            return this.all_total_discount;
        },
        get_discount: function () {
            let discount = _super_Orderline.get_discount.apply(this, arguments);
            if(this.promotion_stack){
                let real_discount = 0;
                let base_price = this.price;
                let total_discount = 0;
                total_discount += base_price;
                for(let i in this.promotion_stack){
                    let price_discount = total_discount * (this.promotion_stack[i].discount/100);
                    total_discount = total_discount - price_discount;
                    real_discount += price_discount/base_price;
                }
                return real_discount * 100;
            }
            return discount;
        },
        callback_set_discount: function (discount) {
            this.pos.config.validate_discount_change = false;
            this.set_discount(discount);
            this.pos.config.validate_discount_change = true;
        }
    });
});
