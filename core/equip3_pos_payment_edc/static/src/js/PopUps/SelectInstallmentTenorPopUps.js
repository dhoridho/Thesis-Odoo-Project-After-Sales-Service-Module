odoo.define('equip3_pos_payment_edc.SelectInstallmentTenorPopUps', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const {posbus} = require('point_of_sale.utils');

    class SelectInstallmentTenorPopUps extends PosComponent {
        constructor() {
            super(...arguments);
        }
        
        get_value_options(){
            let self = this;
            let values = [];
            for (var i = self.env.pos.db.pos_payment_installment_tenor.length - 1; i >= 0; i--) {
                let record = self.env.pos.db.pos_payment_installment_tenor[i];
                if( self.props.installment_tenor_ids.includes(record.id) ){
                    values.push(record);
                }
            }

            values.sort((a, b) => a.id - b.id);
            return values
        }

        async confirm() {
            let $popup = $('.popup.edc-popup-cc'); 
            let payload = {
                'value': $popup.find('[name="value"]').val(),
            } 
            this.props.resolve({ confirmed: true, payload: payload });
            this.trigger('close-popup');
        }
        cancel() {
            this.trigger('close-popup');
        }
    }

    SelectInstallmentTenorPopUps.template = 'SelectInstallmentTenorPopUps';
    Registries.Component.add(SelectInstallmentTenorPopUps);
    return SelectInstallmentTenorPopUps;
});