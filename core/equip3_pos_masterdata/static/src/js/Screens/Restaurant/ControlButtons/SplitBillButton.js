odoo.define('equip3_pos_masterdata.SplitBillButton', function (require) {
    'use strict';

    const SplitBillButton = require('pos_restaurant.SplitBillButton');
    const {posbus} = require('point_of_sale.utils');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require('web.custom_hooks');
    SplitBillButton.template = 'MasterSplitBillButton';

    const RetailSplitBillButton = (SplitBillButton) =>
        class extends SplitBillButton {

            async onClick() {
                const order = this.env.pos.get_order();
                if (order.get_orderlines().length > 0) {
                    posbus.trigger('set-screen', 'Split')
                }
                if (jQuery('.paymentlines-empty').length > 0){
                    this.env.pos.chrome.showScreen('SplitBillScreen');
                }
            }
        }
    Registries.Component.extend(SplitBillButton, RetailSplitBillButton);

    return RetailSplitBillButton;
});
