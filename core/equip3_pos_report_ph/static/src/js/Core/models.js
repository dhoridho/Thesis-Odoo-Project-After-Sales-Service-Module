odoo.define('equip3_pos_report_ph.models', function (require) {
    "use strict";

    var models = require('point_of_sale.models');
    var equip3_pos_general_models = require('equip3_pos_general.models');
    const PosOrderGeneral = require('equip3_pos_general.pos_order');
    const PosOrderMasterdata = require('equip3_pos_masterdata.order');



    models.load_fields('pos.receipt.template', ['is_ph_vat_detail','is_ph_template','is_ph_show_customer_information','is_ph_show_pos_information','is_ph_show_company_information']);
    models.load_fields('pos.config', ['ph_machine_identification_number','is_ph_enable_ptu_number','ph_ptu_number','ph_ptu_issued_date','ph_ptu_valid_date']);
    models.load_fields('res.company', ['ph_company_no','is_ph_bir_accreditation','ph_bir_accreditation_no','ph_bir_accreditation_issued_date','ph_bir_accreditation_valid_until','company_npwp','street','street2']);
    models.load_fields('res.partner', ['vat','street','street2']);
    models.load_fields('product.product', ['ph_vat_type']);
    models.load_fields('pos.order', ['is_ph_training_mode']);


    let _super_Order = models.Order.prototype;
    models.Order = models.Order.extend({

        initialize: function (attributes, options) {
            _super_Order.initialize.apply(this, arguments);
            this.is_ph_training_mode = this.is_ph_training_mode || false
        },

        init_from_JSON: function (json) {
            let res = _super_Order.init_from_JSON.apply(this, arguments);
            if (json.is_ph_training_mode) {
                this.is_ph_training_mode = json.is_ph_training_mode;
            }


            return res;
        },


        export_as_JSON: function () {
            const json = _super_Order.export_as_JSON.apply(this, arguments);
            if (this.is_ph_training_mode) {
                json.is_ph_training_mode = this.is_ph_training_mode
            }
            return json;
        },
        export_for_printing: function () {
            let receipt = _super_Order.export_for_printing.call(this);
            var receipt_template = this.pos.get_receipt_template()
            let order = this;
            if(order.void_order_id){
                receipt['is_void_order'] = true
            }
            receipt['is_exchange_order'] = order.is_exchange_order
            receipt['is_return_order'] = order.is_return_order
            
            receipt['is_ph_training_mode'] = order.is_ph_training_mode
            
            if(receipt_template.is_ph_vat_detail && receipt_template.is_ph_template) {
                receipt['VATable'] = 0
                receipt['VATexempt'] = 0
                receipt['VATZeroRate'] = 0
                for (let i = 0; i < order.orderlines.models.length; i++) {
                    let line = order.orderlines.models[i];
                    let product = this.pos.db.get_product_by_id(line.product.id);

                    if (product && product.ph_vat_type == 'VATable') {
                        receipt['VATable'] += line.get_price_without_tax()
                    }
                    if (product && product.ph_vat_type == 'VAT zero rate') {
                        receipt['VATZeroRate'] += line.get_price_without_tax()
                    }
                    if (product && product.ph_vat_type == 'VAT exempt') {
                        receipt['VATexempt'] += line.get_price_without_tax()
                    }
                }
            }
            return receipt
        },
    })

});
