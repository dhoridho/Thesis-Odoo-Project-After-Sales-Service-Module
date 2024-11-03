odoo.define('xendit_pos.models', function (require) {
    var models = require('point_of_sale.models');
    var PaymentXendit = require('xendit_pos.payment');
    
    models.register_payment_method('xendit_pos', PaymentXendit);
    models.load_fields(
        'pos.payment.method', 
        [
            'xendit_pos_terminal_identifier',
            'xendit_pos_test_mode', 
            'xendit_pos_secret_key'
        ]
    );

    const superPaymentline = models.Paymentline.prototype;
    models.Paymentline = models.Paymentline.extend({
        initialize: function(attr, options) {
            superPaymentline.initialize.call(this,attr,options);
            this.xenditInvoiceId = this.xenditInvoiceId  || null;
        },
        export_as_JSON: function(){
            const json = superPaymentline.export_as_JSON.call(this);
            json.xendit_invoice_id = this.xenditInvoiceId;
            return json;
        },
        init_from_JSON: function(json){
            superPaymentline.init_from_JSON.apply(this,arguments);
            this.xenditInvoiceId = json.xendit_invoice_id;
        },
        setXenditInvoiceId: function(id) {
            this.xenditInvoiceId = id;
        },
        getXenditInvoiceId: function() {
            return this.xenditInvoiceId;
        }
    });
});
    