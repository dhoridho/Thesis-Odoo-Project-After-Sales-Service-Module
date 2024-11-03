odoo.define('xendit.XenditQRCodePopup', function(require) {
    'use strict';
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const PosComponent = require('point_of_sale.PosComponent');
    const ControlButtonsMixin = require('point_of_sale.ControlButtonsMixin');
    const NumberBuffer = require('point_of_sale.NumberBuffer');
    const { useListener } = require('web.custom_hooks');
    const { useState } = owl.hooks;
    class XenditQRCodePopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
        }

        get currentOrder() {
            return this.env.pos.get_order();
        }
    }

        //Create products popup
    XenditQRCodePopup.template = 'XenditQRCodePopup';
    XenditQRCodePopup.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        title: 'Xendit QRcode',
        body: '',
        xenditPaymentStatus: 'Processing...',
        invoiceUrl: '',
        qrCodeImage: ''
    };
    Registries.Component.add(XenditQRCodePopup);
    return XenditQRCodePopup;
})