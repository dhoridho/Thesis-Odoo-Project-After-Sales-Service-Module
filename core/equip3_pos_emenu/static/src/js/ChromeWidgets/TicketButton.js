odoo.define('equip3_pos_emenu.TicketButton', function (require) {
    'use strict';

    const TicketButton = require('equip3_pos_masterdata.TicketButton');
    const Registries = require('point_of_sale.Registries');

    // const EmenuTicketButton = (TicketButton) => class extends TicketButton {
    //     constructor() {
    //         super(...arguments);
    //     } 

    //     async SyncSessionOrders(){
    //         super.SyncSessionOrders()
    //         console.log('00.e.emenu.SyncSessionOrders::11111')
    //         await this.env.pos.sync_emenu_orders(); 
    //     }

    // }

    // Registries.Component.extend(TicketButton, EmenuTicketButton);
    // return EmenuTicketButton;
});