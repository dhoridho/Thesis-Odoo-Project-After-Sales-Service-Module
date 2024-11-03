odoo.define('equip3_pos_payment_edc.EdcManualInputCode', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    const {Gui} = require('point_of_sale.Gui');

    class EdcManualInputCode extends PosComponent {
        constructor() {
            super(...arguments);
        }

        async onClick(paymentline) {
            const self = this
            const order = this.env.pos.get_order()
            if(paymentline && paymentline.payment_method.is_edc_bca){
                let {confirmed, payload: payload } = await Gui.showPopup('ConfirmPopupEdcBcaApprovalCode', {'title': 'Input Approval Code'} );
                if(confirmed){
                    paymentline.approval_code = payload.approval_code;
                    paymentline.payment_edc_state = 'paid';
                }
            }

        } 
 
    }

    EdcManualInputCode.template = 'EdcManualInputCode';
    Registries.Component.add(EdcManualInputCode);
    return EdcManualInputCode;
});