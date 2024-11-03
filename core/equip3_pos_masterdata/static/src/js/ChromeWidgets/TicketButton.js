odoo.define('equip3_pos_masterdata.TicketButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const TicketButton = require('point_of_sale.TicketButton');
    const {useState} = owl.hooks;
    const {useListener} = require('web.custom_hooks');
    const models = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');
    const { posbus } = require('point_of_sale.utils');

    const RetailTicketButton = (TicketButton) =>
        class extends TicketButton {
            constructor() {
                super(...arguments);
            }

            onClick() {
                let receiptScreen = $('.receipt-screen.screen').length;
                let currentOrder = this.env.pos.get_order();
                if(receiptScreen && currentOrder){
                    if(currentOrder.is_complete){
                        currentOrder.finalize();
                    }    
                }

                if (this.env.pos.config.is_manual_sync_for_sync_between_session){
                    this.SyncSessionOrders();
                }

                if (this.props.isTicketScreenShown) {
                    posbus.trigger('ticket-button-clicked');
                } else {
                    this.showTempScreen('TicketScreen');
                }
            }

            async SyncSessionOrders(){
                await this.env.pos.sync_session_orders();
                posbus.trigger('ticket-button-refresh'); 
            }

            get isKitchenScreen() {
                if (!this || !this.env || !this.env.pos || !this.env.pos.config) {
                    return false
                } else {
                    if (this.env.pos.config.screen_type == 'kitchen' || this.env.pos.config.hide_order_screen) {
                        return true
                    } else {
                        return false
                    }
                }
            }

            get count() {
                posbus.on('ticket-button-refresh', this, this.render);
                if (!this.env.pos || !this.env.pos.config) return 0;
                if (this.env.pos.config.iface_floorplan) {
                    let orders = this.env.pos.get('orders').models;
                    orders = orders.filter((o)=>o.is_complete!=true);
                    return orders.length;
                } else {
                    return super.count;
                }
            }

        }
    TicketButton.template = 'RetailTicketButton'
    Registries.Component.extend(TicketButton, RetailTicketButton);

    return RetailTicketButton;
});
