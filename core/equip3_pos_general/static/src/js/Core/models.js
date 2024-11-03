odoo.define('equip3_pos_general.models', function (require) {
    "use strict";

var models = require('point_of_sale.models');
const time = require('web.time');
const core = require('web.core');
const QWeb = core.qweb;
var utils = require('web.utils');
var round_pr = utils.round_precision;
var SuperPosModel = models.PosModel.prototype;
var _super_order = models.Order.prototype;
models.Order = models.Order.extend({

    export_for_printing: function(){
        var receipt = _super_order.export_for_printing.apply(this, arguments);
        receipt['ean13'] = this.ean13
        return receipt;
    },
});


models.PosModel = models.PosModel.extend({
    _save_to_server: function (orders, options) {
        var self = this;
        return SuperPosModel._save_to_server.call(this,orders,options).then(function(return_dict){
            if(return_dict){
                _.forEach(return_dict, function(data){
                    if(data.orders != null){
                        if(self.db.all_payments)
                            data.payments.forEach(function(payment) {
                                self.db.all_payments.unshift(payment);
                                self.db.payment_by_id[payment.id] = payment;
                        });
                        delete data.orders;
                        delete data.orderlines;
                        delete data.payments;
                    }
                })
            }
            return return_dict
        });
    }
});

    

models.load_models({
    model: 'pos.receipt.template',
    fields: ['name','size','custom_size','is_need_header','receipt_header_text','is_need_footer','receipt_footer_text',
        'is_receipt_disc_in_orderline','is_receipt_tax_include_orderline','is_receipt_serial_lot_info','is_receipt_product_code',
        'is_voucher_receipt','voucher_receipt_display','generate_voucher_id','is_show_discount_detail', 
        'is_receipt_savings_summary', 'savings_summary_text'],
    loaded: function(self,receipt_templates){
        self.db.set_pos_receipt_template(receipt_templates);
    },
});
models.load_models({
    model: 'weight.scale.barcode.format',
    fields: ['id','name','total_digit','line_ids'],
    loaded: function(self,result){
        self.db.pos_weight_scale_barcode_format = result ;
    },
});
models.load_models({
    model: 'weight.scale.barcode.format.line',
    fields: ['name','digit','data','parent_id','coefficient_ratio'],
    domain: function(self){ return [['parent_id', '!=', false]]; },
    loaded: function(self,result){
        self.db.pos_weight_scale_barcode_format_line = result ;
    },
});
models.load_fields('pos.promotion', ['card_payment_ids','is_priority','note']);
models.load_fields('pos.config', ['iface_splitbill','pos_receipt_template_id','weight_scale_barcode_format_id']);
models.load_fields('res.company', ['apply_rounding_type','rounding_method_id','is_order_rounding','order_rounding_type','rounding_multiplier']);
models.load_models({
    model: 'group.card',
    fields: ['card_group_name','card_group_active','company_id'],
    domain: function(self){ return [['company_id', '=', self.company && self.company.id || false], ['card_group_active', '=', true]]; },
    loaded: function(self,card_groups){
        self.db.set_card_groups(card_groups);
    },
});

models.load_models({
    model: 'card.payment',
    fields: ['card_name','card_active','card_group','BIN', 'company_id', 'have_char', 'card_type'],
    domain: function(self){ return []; },
    loaded: function(self,card_payments){
        self.db.set_card_payments(card_payments);
    },
});

models.load_models([{
    label: 'Cashier Access(res.users)',
    model:  'res.users',
    fields: [
        'id',
        'name',
        'image_1920',
        'allow_discount',
        'allow_qty',
        'allow_price',
        'allow_remove_line',
        'allow_minus',
        'allow_payment',
        'allow_customer',
        'allow_add_order',
        'allow_remove_order',
        'allow_add_product',
        'allow_payment_zero',
        'cashier_code',
    ],
    domain: function(self){
        return self.config.user_ids.length > 0 ? [['id', 'in', self.config.user_ids]] : [];
    },
    loaded: function(self, users) {
        self.allowed_users = [];
        if (self.config.module_pos_hr && users) {
            self.allowed_users = users;
            self.user_by_id = {};
            self.allowed_users.forEach(function(user) {
                self.user_by_id[user.id] = user;
                user.is_cashier = true;
                user.role = 'cashier';
            });
        }
    }
},
{
        model: 'account.cash.rounding',
        fields: ['name', 'rounding', 'rounding_method'],
        domain: function(self){return [['id', '=', self.company.rounding_method_id[0]]]; },
        loaded: function(self, cash_rounding) {
            self.cash_rounding = cash_rounding;
        }
    }, 
]);

var posmodel_super = models.PosModel.prototype;
models.PosModel = models.PosModel.extend({
    load_server_data: function () {
        var self = this;
        return posmodel_super.load_server_data.apply(this, arguments).then(function () {
            var user_ids = _.map(self.allowed_users, function(user){return user.id;});
            var records = self.rpc({
                model: 'res.users',
                method: 'get_user_pos_security_pin',
                args: [user_ids],
            });
            return records.then(function (users_data) {
                self.allowed_users.forEach(function (user) {
                    var data = _.findWhere(users_data, {'id': user.id});
                    if (data !== undefined){
                        user.pin = data.pos_security_pin;
                        user.pos_security_pin = data.pos_security_pin;
                    }
                });
            });
        });
    },

    check_expiry_date: function (order) {
        // var order = this.env.pos.get_order();
        var currentDate = new Date();
        var return_period = this.env.pos.config.pos_order_period_return_days * 24 * 60 * 60 * 1000; // 30 days in milliseconds
        if (currentDate.getTime() - order.creation_date.getTime() > return_period) {
            return true;
        } else {
            return false;
        }
    },

    set_cashier: function(user) {
        posmodel_super.set_cashier.apply(this, arguments);
        const selectedOrder = this.get_order();
        if (selectedOrder && !selectedOrder.get_orderlines().length) {
            // Order without lines can be considered to be un-owned by any cashier.
            // We set the cashier on that order to the currently set cashier.
            selectedOrder.cashier = user;
        }
        if (user.is_cashier && this.chrome) {
            this.config.cashier = user;
            this.config.allow_discount = user['allow_discount'];
            this.config.allow_qty = user['allow_qty'];
            this.config.allow_price = user['allow_price'];
            this.config.allow_remove_line = user['allow_remove_line'];
            this.config.allow_minus = user['allow_minus'];
            this.config.allow_payment = user['allow_payment'];
            this.config.allow_customer = user['allow_customer'];
            this.config.allow_add_order = user['allow_add_order'];
            this.config.allow_remove_order = user['allow_remove_order'];
            this.config.allow_add_product = user['allow_add_product'];
            this.config.allow_payment_zero = user['allow_payment_zero'];
            this.chrome.env.qweb.forceUpdate();
        }
    },
    render_html_for_customer_facing_display: function () { // TODO: we add shop logo to customer screen
        var self = this;
        var order = this.get_order();
        var currency_order = false
        var rendered_html = this.config.customer_facing_display_html;
        var get_image_promises = [];

        if (order) {

            currency_order = order.currency
            order.get_orderlines().forEach(function (orderline) {
                let product = orderline.product;
                let image_url = window.location.origin + '/web/image?model=product.product&field=image_128&id=' + product.id;
                if (!product.image_base64) {
                    get_image_promises.push(self._convert_product_img_to_base64(product, image_url));
                }
            });
        }

        // when all images are loaded in product.image_base64
        return Promise.all(get_image_promises).then(function () {
            var rendered_order_lines = "";
            var rendered_payment_lines = "";
            var order_total_with_tax = self.format_currency(0,undefined,currency_order);

            if (order) {
                rendered_order_lines = QWeb.render('CustomerFacingDisplayOrderLines', {
                    'pos': self.env.pos,
                    'orderlines': order.get_orderlines(),
                });
                rendered_payment_lines = QWeb.render('CustomerFacingDisplayPaymentLines', {
                    'order': order,
                    'pos': self.env.pos,
                });
                order_total_with_tax = self.format_currency(order.get_total_with_tax(),undefined,currency_order);
            }
            var $rendered_html = $(rendered_html);
            $rendered_html.find('.pos_orderlines_list').html(rendered_order_lines);
            $rendered_html.find('.pos-total').find('.pos_total-amount').html(order_total_with_tax);
            var pos_change_title = $rendered_html.find('.pos-change_title').text();
            $rendered_html.find('.pos-paymentlines').html(rendered_payment_lines);
            $rendered_html.find('.pos-change_title').text(pos_change_title);
            if (order && order.get_client()) {
                $rendered_html.find('.pos-total').find('.client-name').html(order.get_client().name);
            }
            if (order) {
                let discount = self.format_currency(order.get_total_discount(),undefined,currency_order)
                $rendered_html.find('.pos-total').find('.pos_total-discount').html(discount);
            }
            if (order) {
                $rendered_html.find('.pos-total').find('.pos_total-taxes').html(self.format_currency(order.get_total_tax(),undefined,currency_order));
            }
//            const logo_base64 = self.get_logo();
//            const image_html = '<img src="' + logo_base64 + '" class="logo-shop" style="width: 100%">';
//                $rendered_html.find('.pos-company_logo').html(image_html);
            rendered_html = _.reduce($rendered_html, function (memory, current_element) {
                return memory + $(current_element).prop('outerHTML');
            }, "");

            rendered_html = QWeb.render('CustomerFacingDisplayHead', {
                origin: window.location.origin
            }) + rendered_html;
            return rendered_html;
        });
    },
});


let SuperPaymentline = models.Paymentline.prototype;
models.Paymentline = models.Paymentline.extend({
    initialize: function(attr,options) {
        SuperPaymentline.initialize.apply(this,arguments);
        this.mdr_payment_card_id = false
        this.payment_mdr_id = false
        this.card_payment_number = false
        this.mdr_amount = 0
        this.mdr_paid_by = false
    },
    init_from_JSON: function(json) {
        SuperPaymentline.init_from_JSON.apply(this,arguments);
        if (json.mdr_payment_card_id) {
            this.mdr_payment_card_id = json.mdr_payment_card_id;
        }
        if (json.payment_mdr_id) {
            this.payment_mdr_id = json.payment_mdr_id;
        }

        if (json.card_payment_number) {
            this.card_payment_number = json.card_payment_number;
        }
        if (json.mdr_amount) {
            this.mdr_amount = json.mdr_amount;
        }
        if (json.mdr_paid_by) {
            this.mdr_paid_by = json.mdr_paid_by;
        }
    },

    export_as_JSON: function(){
        var res = SuperPaymentline.export_as_JSON.apply(this,arguments);
        res['payment_card_id'] = this.order ? this.order.get_selected_card_payment_id(): false;
        if (this.mdr_payment_card_id) {
            res.mdr_payment_card_id = this.mdr_payment_card_id
        }
        if (this.payment_mdr_id) {
            res.payment_mdr_id = this.payment_mdr_id
        }

        if (this.card_payment_number) {
            res.card_payment_number = this.card_payment_number
        }
        if (this.mdr_amount) {
            res.mdr_amount = this.mdr_amount
        }
        if (this.mdr_paid_by) {
            res.mdr_paid_by = this.mdr_paid_by
        }
        return res;
    }
});

var super_order_model = models.Order.prototype;
models.Order = models.Order.extend({
    initialize: function (attributes, options) {
        super_order_model.initialize.apply(this, arguments);

        if (!options.json) {
            this.cashier = this.pos.get_cashier();
        }

        this.selected_card_payment_id = this.selected_card_payment_id || false;
        this.selected_card_payment_number = this.selected_card_payment_number || false;
        this.total_mdr_amount_customer = 0;
        this.total_mdr_amount_company = 0;
        this.is_self_picking = false
        this.is_home_delivery = false
        this.is_pre_order = false
        this.estimated_order_pre_order = false
    },
    init_from_JSON: function (json) {
        let res = super_order_model.init_from_JSON.apply(this, arguments);
        if (this.pos.config.module_pos_hr) {
            this.cashier = this.pos.user_by_id[json.cashier_id];
        }

        if (json.total_mdr_amount_customer) {
            this.total_mdr_amount_customer = json.total_mdr_amount_customer;
        }
        if (json.total_mdr_amount_company) {
            this.total_mdr_amount_company = json.total_mdr_amount_company;
        }
        if (json.is_self_picking) {
            this.is_self_picking = json.is_self_picking;
        }
        if (json.is_home_delivery) {
            this.is_home_delivery = json.is_home_delivery;
        }
        if (json.is_pre_order) {
            this.is_pre_order = json.is_pre_order;
        }
        if (json.estimated_order_pre_order) {
            this.estimated_order_pre_order = json.estimated_order_pre_order;
        }
        if (json.cashier_id) {
            this.cashier_id = json.cashier_id;
        }

        this.set_selected_card_payment_id(json.selected_card_payment_id);
        if (json.selected_card_payment_number) {
            this.selected_card_payment_number = json.selected_card_payment_number;
        }

        return res;
    },
    export_as_JSON: function () {
        const json = super_order_model.export_as_JSON.apply(this, arguments);
        if (this.pos.config.module_pos_hr) {
            this.cashier = this.pos.get_cashier(); 
            json.cashier_id = this.cashier ? this.cashier.id : false;
        }

        json['selected_card_payment_id'] = this.get_selected_card_payment_id();
        if (this.selected_card_payment_number) {
            json.selected_card_payment_number = this.selected_card_payment_number;
        }

        if (this.total_mdr_amount_customer) {
            json.total_mdr_amount_customer = this.total_mdr_amount_customer
        }
        if (this.total_mdr_amount_company) {
            json.total_mdr_amount_company = this.total_mdr_amount_company
        }
        if (this.is_self_picking) {
            json.is_self_picking = this.is_self_picking
        }
        if (this.is_home_delivery) {
            json.is_home_delivery = this.is_home_delivery
        }
        if (this.is_pre_order) {
            json.is_pre_order = this.is_pre_order
        }
        if (this.estimated_order_pre_order) {
            json.estimated_order_pre_order = this.estimated_order_pre_order
        }
        return json;
    },
    get_subtotal: function(){
        var total = this.orderlines.reduce((function(sum, orderLine){
            return sum + orderLine.get_display_price();
        }), 0)
        return round_pr(total, this.pos.currency.rounding);
    },
    get_total_without_tax_without_discount: function() {
        var total = this.orderlines.reduce((function(sum, orderLine) {
            return sum + orderLine.get_price_without_tax_without_discount();
        }), 0)
        return round_pr(total, this.pos.currency.rounding);
    },
    get_total_with_tax_without_rounding: function () {
        let total_with_tax = super_order_model.get_total_with_tax.apply(this, arguments);
        return total_with_tax
    },
    get_rounding_amount_order: function () {
        var result = 0
        if(this.pos.company.apply_rounding_type && this.pos.company.rounding_method_id && this.pos.company.is_order_rounding){
            if(this.pos.company.apply_rounding_type == 'All Payment'){
                var total_payment = this.paymentlines.reduce((function(sum, paymentLine) {
                    sum += paymentLine.get_amount();
                    return sum;
                }), 0)
            } 
            if(this.pos.company.apply_rounding_type == 'Cash Payment'){
                var total_payment = this.paymentlines.reduce((function(sum, paymentLine) {
                    if (paymentLine.payment_method.is_cash_count) {
                        sum += paymentLine.get_amount();
                    }
                    return sum;
                }), 0)
            } 
            var rounding_calc = 0
            if (total_payment){
                if(this.pos.cash_rounding[0].rounding < total_payment) {
                    if(this.pos.cash_rounding[0].rounding_method == 'DOWN') {
                        rounding_calc = Math.floor(total_payment / this.pos.cash_rounding[0].rounding) * this.pos.cash_rounding[0].rounding;
                    }
                    if(this.pos.cash_rounding[0].rounding_method == 'UP') {
                        rounding_calc = Math.ceil(total_payment / this.pos.cash_rounding[0].rounding) * this.pos.cash_rounding[0].rounding;
                    }
                    if(this.pos.cash_rounding[0].rounding_method == 'HALF-UP') {
                        rounding_calc = Math.round(total_payment / this.pos.cash_rounding[0].rounding) * this.pos.cash_rounding[0].rounding;  
                    }
                    result = rounding_calc - total_payment
                }
                else{
                    result = this.pos.cash_rounding[0].rounding - total_payment
                }
            }
        }
        this.rounding_payment = result
        return result
    },
    get_total_mdr_customer: function () {
        var total_mdr_amount_customer = this.paymentlines.reduce((function(sum, paymentLine) {
            if (paymentLine.mdr_paid_by=='Customer') {
                sum += paymentLine.get_mdr_customer_amount();
            }
            return sum;
        }), 0)
        return total_mdr_amount_customer
    },

    get_mdr_amounts: function (){
        let values = this.paymentlines.reduce((acc, curr) => {
            if (curr.mdr_paid_by == 'Customer'){
                acc.amount_by_customer += curr.mdr_amount;
            }
            if (curr.mdr_paid_by == 'Company'){
                acc.amount_by_company += curr.mdr_amount;
            }
            return { 
                amount_by_customer: acc.amount_by_customer, 
                amount_by_company: acc.amount_by_company,
            };
        }, { 
            amount_by_customer: 0, 
            amount_by_company: 0 
        });

        this.total_mdr_amount_customer = values.amount_by_customer;
        this.total_mdr_amount_company = values.amount_by_company;
        return values;
    },

    //TODO: Get total if product in brands | Voucher
    get_total_with_tax_in_brands: function (brand_ids) {
        let total_with_tax = this.orderlines.reduce((function(sum, orderLine) {
            let is_in_brand = false;
            let product_brand_ids = orderLine.product.product_brand_ids;
            if(product_brand_ids && product_brand_ids.length){
                for (let product_brand_id of product_brand_ids){
                    if(brand_ids.includes(product_brand_id) == true){
                        is_in_brand = true;
                        break;
                    }
                }
            }
            if(!is_in_brand){
                return sum;
            }
            return sum + orderLine.get_price_with_tax();
        }), 0);
        
        let mdr_amounts = this.get_mdr_amounts();

        total_with_tax += mdr_amounts.amount_by_customer;
        total_with_tax += this.rounding_from_payment || 0;
 
        return total_with_tax
    },
    get_total_without_tax_in_brands: function (brand_ids) {
        let total_without_tax = this.orderlines.reduce((function(sum, orderLine) {
            let is_in_brand = false;
            let product_brand_ids = orderLine.product.product_brand_ids;
            if(product_brand_ids && product_brand_ids.length){
                for (let product_brand_id of product_brand_ids){
                    if(brand_ids.includes(product_brand_id) == true){
                        is_in_brand = true;
                        break;
                    }
                }
            }
            if(!is_in_brand){
                return sum;
            }
            return sum + orderLine.get_price_without_tax();
        }), 0);
        return round_pr(total_without_tax, this.pos.currency.rounding);
    },

    // OVERRIDE
    get_total_with_tax: function () {
        let total_with_tax = this.orderlines.reduce((function(sum, orderLine) {
            return sum + orderLine.get_price_with_tax();
        }), 0);
        
        let mdr_amounts = this.get_mdr_amounts();

        total_with_tax += mdr_amounts.amount_by_customer;
        total_with_tax += this.rounding_from_payment || 0;

        return total_with_tax
    },
    get_total_without_tax: function () {
        let total_without_tax = this.orderlines.reduce((function(sum, orderLine) {
            return sum + orderLine.get_price_without_tax();
        }), 0);
 
        return total_without_tax;
    },
    get_total_wo_tax_after_pricelist: function () {
        var result = this.orderlines.reduce((function(sum, orderLine) {
                var subtotal =  orderLine.get_total_wo_tax_after_pricelist()
                return sum + subtotal;
            }), 0)

        return result
    },
    get_total_discount_wo_pricelist: function () {
        var company = this.pos.company
        var tax_discount_policy = company.tax_discount_policy
        // var res = super_order_model.get_total_discount.apply(this, arguments);
        if (tax_discount_policy=='untax'){
            var total_discount = round_pr(this.orderlines.reduce((function(sum, orderLine) {
                var discount_line = orderLine.get_all_total_discount();
                sum += discount_line;
                if (orderLine.display_discount_policy() === 'without_discount'){
                    sum += ((orderLine.get_lst_price() - orderLine.get_unit_price()) * orderLine.get_quantity());
                }
                return sum;
            }), 0), this.pos.currency.rounding);

        }
        else{
            var total_discount = this.orderlines.reduce((function(sum, orderLine) {
                var disc = 0
                var disc_percentage =  orderLine.get_all_total_discount()
                var subtotal = orderLine.get_all_prices().priceWithoutTaxWithoutDiscount
                disc = disc_percentage
                return sum + disc;
            }), 0)
        }
 
        return round_pr(total_discount, this.pos.currency.rounding);
    },
    get_total_discount: function () {
        var company = this.pos.company
        var tax_discount_policy = company.tax_discount_policy
        var res = super_order_model.get_total_discount.apply(this, arguments);
        if (tax_discount_policy=='untax'){
            var total_discount = round_pr(this.orderlines.reduce((function(sum, orderLine) {
            var discount_line = orderLine.get_all_total_discount()
            // if (discount_line){
            //     discount_line = discount_line * orderLine.get_quantity()
            // }
            sum += discount_line;
            if (orderLine.display_discount_policy() === 'without_discount'){
                sum += ((orderLine.get_lst_price() - orderLine.get_unit_price()) * orderLine.get_quantity());
            }
            return sum;
        }), 0), this.pos.currency.rounding);

        }
        else{
            var total_discount = this.orderlines.reduce((function(sum, orderLine) {
                var disc = 0
                var disc_percentage =  orderLine.get_all_total_discount()
                var subtotal = orderLine.get_all_prices().priceWithoutTaxWithoutDiscount
                disc = disc_percentage
                return sum + disc;
            }), 0)
        } 
    
        // if(this.pos.company.is_order_rounding && this.pos.company.order_rounding_type == 'Down') {
        //     if (this.pos.company.rounding_multiplier){
        //         total_discount = Math.floor(total_discount / parseFloat(this.pos.company.rounding_multiplier)) * parseFloat(this.pos.company.rounding_multiplier);
        //     }
        //     else{
        //         total_discount = Math.floor(total_discount)
        //     }
        // }
        // if(this.pos.company.is_order_rounding && this.pos.company.order_rounding_type == 'Up') {
        //     if (this.pos.company.rounding_multiplier){
        //         total_discount = Math.ceil(total_discount / parseFloat(this.pos.company.rounding_multiplier)) * parseFloat(this.pos.company.rounding_multiplier);
        //     }
        //     else{
        //         total_discount = Math.ceil(total_discount)
        //     }
        // }
        // if(this.pos.company.is_order_rounding && this.pos.company.order_rounding_type == 'Half Up') {
        //     if (this.pos.company.rounding_multiplier){
        //         total_discount = Math.round(total_discount / parseFloat(this.pos.company.rounding_multiplier)) * parseFloat(this.pos.company.rounding_multiplier);
        //     }
        //     else{
        //         total_discount = Math.round(total_discount)
        //     }
        // }

        return round_pr(total_discount, this.pos.currency.rounding);
    },
    get_total_tax: function () {
        var tax_discount_policy = this.pos.company.tax_discount_policy
        if (tax_discount_policy=='untax'){
            var total_tax = super_order_model.get_total_tax.apply(this, arguments);
        }else{
            var total_tax = this.orderlines.reduce((function(sum, orderLine) {
                return sum + (orderLine.get_price_with_tax()-orderLine.get_price_without_tax());
            }), 0)
        }
        return round_pr(total_tax, this.pos.currency.rounding);
    },
    get_total_paid: function () {
        let total_paid = this.paymentlines.reduce((function(sum, paymentLine) {
            if (paymentLine.is_done()) {
                sum += paymentLine.get_amount();
            }
            return sum;
        }), 0)
        return round_pr(total_paid, this.pos.currency.rounding);
    },
    set_selected_card_payment: function(values){
        this.selected_card_payment_id = values.card_payment_id;
        this.selected_card_payment_number = values.card_number;
        this.trigger('change');
    },
    get_selected_card_payment: function(){
        return {
            card_payment_id: this.selected_card_payment_id,
            card_number: this.selected_card_payment_number,
        };
    },
    set_selected_card_payment_id: function(selected_card_payment_id){
        this.selected_card_payment_id = selected_card_payment_id;
        this.trigger('change');
    },
    get_selected_card_payment_id: function(){
        return this.selected_card_payment_id;
    },
});

models.Orderline = models.Orderline.extend({
    get_quantity_str_with_uom: function(){
        var unit = this.get_unit();
        return this.quantityStr + ' ' + unit.name;
    },
    get_price_without_tax_without_discount: function() {
        return this.get_all_prices().priceWithoutTaxWithoutDiscount;
    },
    set_full_product_name: function(full_product_name){
        this.full_product_name = full_product_name || '';
    },

    /**
     * Hook for fnb module
     */
    get_additional_cost: function(){
        return 0;
    },
    /**
     * Hook for fnb module
     */
    get_additional_cost_x_quantity: function(){
        return 0;
    },

    // OVERRIDE
    get_all_prices: function(){
        var self = this;
        var product =  this.get_product();
        var company = this.pos.company

        var discount = this.get_all_discount()
        if(discount){
            discount = discount / this.get_quantity()
        }

        let additional_cost = this.get_additional_cost();

        var tax_discount_policy = company.tax_discount_policy
        if (tax_discount_policy=='untax'){
            var first_price = this.get_unit_price() + additional_cost;
            var base_price = first_price;
            var get_all_taxes_new = this.get_all_taxes_new(this.get_unit_price() + additional_cost)
            if(get_all_taxes_new){
                base_price = get_all_taxes_new['total_excluded'];
            }
            var price_unit = base_price  - discount;
            if (discount==0){
                price_unit = first_price
            }
    
        } else {
            var get_all_taxes_new = this.get_all_taxes_new(this.price  + additional_cost);
            var first_price = this.price + additional_cost;
            var price_exclude = first_price;
            if(get_all_taxes_new){
                var price_exclude = get_all_taxes_new['total_excluded'];
            }
            var price_unit = (this.price + additional_cost) - discount;
            var price_unit_wo_disc = this.price + additional_cost;
        }

        var taxtotal = 0;
        var taxes =  this.pos.taxes;
        var taxes_ids = _.filter(product.taxes_id, t => t in this.pos.taxes_by_id);
        var taxdetail = {};
        var taxdetail_name = {};
        var product_taxes = [];

        ////////////////////Temporary Include to exclude////////////////////////
        if (tax_discount_policy=='untax' && discount!=0){
            _(taxes).each(function(t) {
                if(t.price_include){
                    t.temporary_price_exclude = true
                    t.price_include = false
                }
            });
        }
        ////////////////////////////////////////////

        _(taxes_ids).each(function(el){
            var tax = _.detect(taxes, function(t){
                return t.id === el;
            });
            product_taxes.push.apply(product_taxes, self._map_tax_fiscal_position(tax));
        });
        product_taxes = _.uniq(product_taxes, function(tax) { return tax.id; });
        var all_taxes = this.compute_all_without_rounding(product_taxes, price_unit, this.get_quantity(), 0.0000001);

        ////////////////////Temporary Include to exclude////////////////////////
        if (tax_discount_policy=='untax'  && discount!=0){
            _(taxes).each(function(t) {
                if(t.temporary_price_exclude){
                    t.price_include = true
                    t.temporary_price_exclude = false
                }
            });
        }
        ////////////////////////////////////////////

        if (tax_discount_policy=='untax'){
            var all_taxes_before_discount = this.compute_all(product_taxes, this.get_unit_price(), this.get_quantity(),0.0000001);
            _(all_taxes.taxes).each(function(tax) {
                taxtotal += tax.amount;
                taxdetail[tax.id] = tax.amount;
                if (tax.name in taxdetail_name){
                    taxdetail_name[tax.name] += tax.amount;
                }
                else{
                    taxdetail_name[tax.name] = tax.amount;
                }
            });
        }
        else{
            var total_tax_exclude = 0
            var all_taxes_before_discount = this.compute_all(product_taxes, price_unit_wo_disc, this.get_quantity(),0.0000001);
            _(all_taxes_before_discount.taxes).each(function(tax) {
                taxtotal += tax.amount;
                taxdetail[tax.id] = tax.amount;
                if(!tax.price_include){
                    total_tax_exclude+=tax.amount
                }

                if (tax.name in taxdetail_name){
                    taxdetail_name[tax.name] += tax.amount;
                } else {
                    taxdetail_name[tax.name] = tax.amount;
                }
            });
            all_taxes.total_included = price_unit + total_tax_exclude
            all_taxes.total_excluded = price_exclude - discount
        }


        var all_prices = {
            "priceWithTax": all_taxes.total_included,
            "priceWithoutTax": all_taxes.total_excluded,
            "priceSumTaxVoid": all_taxes.total_void,
            "priceWithTaxBeforeDiscount": all_taxes_before_discount.total_included,
            "tax": taxtotal,
            "taxDetails": taxdetail,
            "taxdetail_name":taxdetail_name,
            "priceWithoutTaxWithoutDiscount": all_taxes_before_discount.total_excluded,
        };
        return all_prices
    },
});

});
