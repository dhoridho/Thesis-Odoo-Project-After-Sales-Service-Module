odoo.define('equip3_pos_emenu.TicketScreen', function (require) {
    'use strict';

    const TicketScreen = require('point_of_sale.TicketScreen');
    const RetailTicketScreen = require('equip3_pos_masterdata.TicketScreen');
    const Registries = require('point_of_sale.Registries');

    const EmenuTicketScreen = (TicketScreen) => class extends TicketScreen {
        constructor() {
            super(...arguments);
        }

        mounted() {
            super.mounted()
        }

        willUnmount() {
            super.willUnmount()
        }


        async onClickSyncSessionOrders(){
            super.onClickSyncSessionOrders();
            await this.env.pos.sync_emenu_orders(); 
        }

        optsEmenuStatus(state){
            /* Status:
                - Created: QR Code printed 
                - New Order (1): New order received, (1) is order count
                - Received: Order served to the Customer
                - To Pay: Customer click Payment in the app
            */
            let opts = {
                'created': 'Created',
                'new_order': 'New Order',
                'received': 'Received',
                'to_pay': 'To Pay',
            }

            return opts[state];
        }

        getEmenuStatus(order) {
            if(order.emenu_status){
                return this.optsEmenuStatus(order.emenu_status);
            }
            return '';
        }

    }

    Registries.Component.extend(TicketScreen, EmenuTicketScreen);
    return EmenuTicketScreen;
});