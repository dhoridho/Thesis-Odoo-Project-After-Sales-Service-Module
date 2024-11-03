odoo.define('equip3_pos_membership.BigData', function (require) {
	'use strict';
	const models = require('point_of_sale.models');
    const _super_PosModel = models.PosModel.prototype;
    const _super_Orderline = models.Orderline.prototype;
    const _super_Paymentline = models.Paymentline.prototype;
    const _super_Order = models.Order.prototype;
    
    models.PosModel = models.PosModel.extend({
        initialize: async function (session, attributes) {
            _super_PosModel.initialize.call(this, session, attributes);
            let pos_order_line_object = this.get_model('pos.order.line');
            let pos_order_object = this.get_model('pos.order');
            if (pos_order_line_object) {
                pos_order_line_object.fields.push('plus_point', 'redeem_point', 'is_product_redeemed', 'reward_id');
            }
            if (pos_order_object) {
                pos_order_object.fields.push('plus_point', 'redeem_point');
            }
        }
    });

    models.Orderline = models.Orderline.extend({ 
        initialize: function(attr, options) {
            var self = this;
            this.plus_point = 0;
            this.redeem_point = 0;
            this.reward_id = null;
            this.is_product_redeemed = false;
            this.is_product_voucher = false;
            _super_Orderline.initialize.call(this, attr, options);
        },

        init_from_JSON: function (json) {
            _super_Orderline.init_from_JSON.apply(this, arguments);
            
            if (json.plus_point) {
                this.plus_point = json.plus_point;
            }
            if (json.redeem_point) {
                this.redeem_point = json.redeem_point;
            }
            if (json.reward_id) {
                this.reward_id = json.reward_id;
            }
            if (json.is_product_redeemed) {
                this.is_product_redeemed = json.is_product_redeemed;
            }
            if (json.is_product_voucher) {
                this.is_product_voucher = json.is_product_voucher;
            }
        },
        export_as_JSON: function() {
            var json = _super_Orderline.export_as_JSON.call(this);

            if (this.plus_point) {
                json.plus_point = this.plus_point;
            }
            if (this.redeem_point) {
                json.redeem_point = this.redeem_point;
            }
            if (this.reward_id) {
                json.reward_id = this.reward_id;
            }
            if (this.is_product_redeemed) {
                json.is_product_redeemed = this.is_product_redeemed;
            }
            if (this.is_product_voucher) {
                json.is_product_voucher = this.is_product_voucher;
            }
            return json;
        },
    });

    models.Paymentline = models.Paymentline.extend({
        initialize: function(attr, options) {
            var self = this;
            this.customer_deposit_id = false;

            _super_Paymentline.initialize.call(this, attr, options);
        },
        init_from_JSON: function (json) {
            let res = _super_Paymentline.init_from_JSON.apply(this, arguments);
            if (json.customer_deposit_id) {
                this.customer_deposit_id = json.customer_deposit_id
            }
            return res
        },
        export_as_JSON: function () {
            let json = _super_Paymentline.export_as_JSON.apply(this, arguments);
            if (this.customer_deposit_id) {
                json['customer_deposit_id'] = this.customer_deposit_id;
            }
            return json
        },
        export_for_printing: function () {
            let datas = _super_Paymentline.export_for_printing.apply(this, arguments);
            if (this.customer_deposit_id) {
                datas['customer_deposit_id'] = this.customer_deposit_id
            }
            return datas
        },
    });


    models.Order = models.Order.extend({
        initialize: function(attr, options) {
            var self = this;
            this.plus_point = 0;
            this.redeem_point = 0;
            _super_Order.initialize.call(this, attr, options);
        },
        init_from_JSON: function (json) {
            let res = _super_Order.init_from_JSON.apply(this, arguments);
            if (json.plus_point) {
                this.plus_point = json.plus_point
            }
            if (json.redeem_point) {
                this.redeem_point = json.redeem_point
            }
            return res
        },
        export_as_JSON: function () {
            let json = _super_Order.export_as_JSON.apply(this, arguments);
            if (this.plus_point) {
                json['plus_point'] = this.plus_point;
            }
            if (this.redeem_point) {
                json['redeem_point'] = this.redeem_point;
            }
            return json
        },

        export_for_printing: function () {
            let receipt = _super_Order.export_for_printing.apply(this, arguments);
            let order = this.pos.get_order();
            receipt['plus_point'] = parseInt(order['plus_point'])
            receipt['redeem_point'] = parseInt(order['redeem_point'])
            return receipt
        },
    });

});