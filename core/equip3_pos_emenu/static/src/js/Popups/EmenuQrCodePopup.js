odoo.define('equip3_pos_emenu.EmenuQrCodePopup', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class EmenuQrCodePopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
        }

        async print_qrcode() {
            console.log('Print QR Code for emenu order');
            const receiptHtml = $('.popups .emenu_qrcode_label')[0].outerHTML;
            this.showScreen('ReportScreen', {
                report_html: receiptHtml,
                report_xml: null,
            });

            this.confirm();
        }

        getPayload() { 
            return true;
        }

        confirm(){
            super.confirm();
        }
    }
    
    EmenuQrCodePopup.template = 'EmenuQrCodePopup';
    EmenuQrCodePopup.defaultProps = {
        confirmText: 'Print QR Code',
        cancelText: 'Cancel',
        title: 'E-Menu QR Code',
        body: '',
    };
    Registries.Component.add(EmenuQrCodePopup);
    return EmenuQrCodePopup;
});
