odoo.define('equip3_pos_payment_edc.Models', function (require) {
"use strict";

    var models = require('point_of_sale.models');
    var core = require('web.core');
    var _t = core._t;

    models.load_fields('pos.order', ['payment_edc_id']);
    models.load_fields('pos.payment.method', ['is_payment_edc', 'edc_port', 'is_edc_bca', 'is_edc_manual_input', 'trans_type', 'trans_type_code', 'installment_plan', 'installment_tenor_ids']);

    models.load_models([
        {
            model: 'pos.payment.installment.tenor',
            fields: ['id', 'name','value'],
            domain: function(self) {
                return [];
            },
            context: function (self) {
                return { }
            },
            loaded: function (self, records) {
                self.savePaymentInstallmentTenor(records);
            },
        },
    ], {'after': 'product.product'});


    const _super_PosModel = models.PosModel.prototype;
    models.PosModel = models.PosModel.extend({
        initialize: async function (session, attributes) {
            if (attributes && attributes.chrome) {
                this.chrome = attributes.chrome
            }
            let self = this;
            _super_PosModel.initialize.call(this, session, attributes);
        },

        savePaymentInstallmentTenor(records) { 
            this.db.save_payment_installment_tenor(records);
        },
    });
    

    var SuperOrder = models.Order.prototype;
    models.Order = models.Order.extend({
        initialize: function(attributes, options) {
            var self = this; 
            self.is_edc_bca = false;
            self.payment_edc_id = false;
            SuperOrder.initialize.call(this, attributes, options);
        },

        init_from_JSON: function (json) { 
            let res = SuperOrder.init_from_JSON.apply(this, arguments);
            if (json.is_edc_bca) {
                this.is_edc_bca = json.is_edc_bca;
            }
            if (json.payment_edc_id) {
                this.payment_edc_id = json.payment_edc_id;
            }
            return res;
        },

        export_as_JSON: function() {
            var self = this;
            var loaded = SuperOrder.export_as_JSON.call(this);
            var current_order = self.pos.get_order();
            if (self.pos.get_order() != null) {
                loaded.is_edc_bca = current_order.is_edc_bca;
                loaded.payment_edc_id = current_order.payment_edc_id;
            }
            return loaded;
        },
    });


    const SuperPaymentline = models.Paymentline.prototype;
    models.Paymentline = models.Paymentline.extend({
        initialize: function(attr, options) {
            SuperPaymentline.initialize.call(this,attr,options);
            this.is_payment_edc = this.is_payment_edc  || false;
            this.approval_code = this.approval_code  || '';
            this.installment_tenor = this.installment_tenor  || '';
            this.installment_amount = this.installment_amount  || '';
        },
        init_from_JSON: function(json){
            SuperPaymentline.init_from_JSON.apply(this,arguments);
            this.is_payment_edc = json.is_payment_edc;
            this.approval_code = json.approval_code;
            
            this.installment_tenor = json.installment_tenor;
            this.installment_amount = json.installment_amount;
        },
        export_as_JSON: function(){
            const json = SuperPaymentline.export_as_JSON.call(this);
            json.is_payment_edc = this.is_payment_edc;
            json.approval_code = this.approval_code;

            json.installment_tenor = this.installment_tenor;
            json.installment_amount = this.installment_amount;
            return json;
        },
    });

});

