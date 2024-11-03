odoo.define('equip3_pos_payment_edc.EdcBcaPopup', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const {posbus} = require('point_of_sale.utils');

    class EdcBcaPopup extends PosComponent {
        constructor() {
            super(...arguments);
        }
        
        async confirm() {
            let $popup = $('.popup.edc-bca-popup'); 
            let payload = {
                'url': $popup.find('[name="url"]').val().trim(),
            } 
            this.props.resolve({ confirmed: true, payload: payload });
            this.trigger('close-popup');
        }
        cancel() {
            this.trigger('close-popup');
        }
    }

    EdcBcaPopup.template = 'EdcBcaPopup';
    Registries.Component.add(EdcBcaPopup);
    return EdcBcaPopup;
});


odoo.define('equip3_pos_payment_edc.ConfirmPopupEdcBcaApprovalCode', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const {posbus} = require('point_of_sale.utils');

    class ConfirmPopupEdcBcaApprovalCode extends PosComponent {
        constructor() {
            super(...arguments);
        }
        
        async confirm() {
            let approval_code = $('.ConfirmPopupEdcBcaApprovalCode input').val().trim();
            if(approval_code == ''){
                return;
            }
            let payload = {
                'approval_code': approval_code,
            } 
            this.props.resolve({ confirmed: true, payload: payload });
            this.trigger('close-popup');
        }
        cancel() {
            this.trigger('close-popup');
        }
    }

    ConfirmPopupEdcBcaApprovalCode.template = 'ConfirmPopupEdcBcaApprovalCode';
    Registries.Component.add(ConfirmPopupEdcBcaApprovalCode);
    return ConfirmPopupEdcBcaApprovalCode;
});