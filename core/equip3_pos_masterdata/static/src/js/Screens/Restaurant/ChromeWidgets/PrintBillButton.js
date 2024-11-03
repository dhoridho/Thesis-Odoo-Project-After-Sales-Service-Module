odoo.define('equip3_pos_masterdata.PrintBillButton', function (require) {
    'use strict';

    const PrintBillButton = require('pos_restaurant.PrintBillButton');
    const Registries = require('point_of_sale.Registries');

    const RetailPrintBillButton = (PrintBillButton) =>
    class extends PrintBillButton {
        async onClick() {
            let selectedOrder = this.env.pos.get_order()
            if (selectedOrder) {
                selectedOrder.skipOrder = true
                await super.onClick()
                selectedOrder.skipOrder = false
            }

        }
    }

    PrintBillButton.template = 'RetailPrintBillButton';
    Registries.Component.extend(PrintBillButton, RetailPrintBillButton);

    return RetailPrintBillButton;
});
