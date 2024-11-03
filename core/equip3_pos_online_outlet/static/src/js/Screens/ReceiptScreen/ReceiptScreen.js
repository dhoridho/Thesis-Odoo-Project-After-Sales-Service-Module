odoo.define('equip3_pos_online_outlet.ReceiptScreen', function (require) {
    'use strict';

    const ReceiptScreen = require('point_of_sale.ReceiptScreen');
    const Registries = require('point_of_sale.Registries');
    const framework = require('web.framework');
   
    const OloReceiptScreen = (ReceiptScreen) =>
      class extends ReceiptScreen {
        constructor() {
            super(...arguments);
        }

        async nextOnlineOrder() {
            framework.blockUI();
            await this.orderDone();
            const selectedOrder = this.currentOrder;

            // await this.env.pos.getOnlineOrders();

            await this.showScreen('ProductScreen', {selected_order_method: 'online-order'});

            this.showScreen('OnlineOrderList',{
                order: null,
                selectedClient: null,
                close_screen_button: true
            });
            framework.unblockUI();
        }
    }

    Registries.Component.extend(ReceiptScreen, OloReceiptScreen);

    return OloReceiptScreen;
});

