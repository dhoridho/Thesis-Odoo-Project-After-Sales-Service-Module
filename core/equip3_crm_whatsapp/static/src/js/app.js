odoo.define('equip3_crm_whatsapp.res_partner', function(require){
    var resParterForm = require('acrux_chat_sale.res_partner');
    resParterForm.include({
        willStart: function(){
            var self = this;
            var viewProm = this._rpc({
                method: 'xmlid_to_res_id',
                model: 'ir.model.data',
                args: ['equip3_crm_whatsapp.view_partner_form_acrux_chat']
            }).then(function(viewId){
                self.form_name = viewId;
            });
            return Promise.all([this._super.apply(this, arguments), viewProm]);
        }
    });
});