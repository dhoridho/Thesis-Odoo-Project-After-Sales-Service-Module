odoo.define('equip3_pos_masterdata.PrintQROrderReceipt', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const {useListener} = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const core = require('web.core');
    const qweb = core.qweb;

    class PrintQROrderReceipt extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }

        async onClick() {
            const order = this.env.pos.get_order()
            order['qrCodeLink'] = '/report/barcode/QR/' + order.ean13
            const QrCode = qweb.render('QrOrderReceipt', {
                order: order
            })
            this.showScreen('ReportScreen', {
                report_html: QrCode
            })

        }

    }

    PrintQROrderReceipt.template = 'PrintQROrderReceipt';

    ProductScreen.addControlButton({
        component: PrintQROrderReceipt,
        condition: function () {
            return true;
        },
    });

    Registries.Component.add(PrintQROrderReceipt);

    return PrintQROrderReceipt;
});
