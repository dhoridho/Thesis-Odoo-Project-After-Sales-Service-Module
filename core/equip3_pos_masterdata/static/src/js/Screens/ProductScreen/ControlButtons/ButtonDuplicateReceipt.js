odoo.define('equip3_pos_masterdata.ButtonDuplicateReceipt', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const {useListener} = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');

    class ButtonDuplicateReceipt extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
    }

    ButtonDuplicateReceipt.template = 'ButtonDuplicateReceipt';

    Registries.Component.add(ButtonDuplicateReceipt);

    return ButtonDuplicateReceipt;
});
