odoo.define('equip3_pos_general_contd.OrderHistoryLocalDetail', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const field_utils = require('web.field_utils');
    const {Gui} = require('point_of_sale.Gui');
    const { useState } = owl.hooks;

    class OrderHistoryLocalDetail extends PosComponent {
        constructor() {
            super(...arguments);

            this.sync = useState({ 'state': '' });
        }
        
        getDate(order){
            return moment(order.creation_date).format('YYYY-MM-DD hh:mm A');
        }

        getCustomer(order){
            if (order.partner_id) {
                if(this.env.pos.db.partner_by_id){
                    let partner = this.env.pos.db.partner_by_id[order.partner_id]
                    return partner.name;
                }
            }
            return '';
        }

        getCashier(order){
            if (order.cashier_id) {
                let cashier = this.env.pos.user_by_id[order.cashier_id];
                if (cashier) {
                    return cashier.name;
                }
            }
            return '';
        }

        async pushOrder(order) {
            let self = this;

            if (self.sync_state == 'Synced') {
                return Gui.showPopup('ConfirmPopup', {
                    title: this.env._t('Force Sync'),
                    body: this.env._t('This order is already in the POS Orders'),
                    disableCancelButton: true,
                })
            }

            if (self.sync.state == 'connecting') {
                return false;
            }

            const pingServer = await self.env.pos._check_connection();
            if (!pingServer) {
                this.env.pos.alert_message({
                    title: this.env._t('Offline'),
                    body: this.env._t('Your Internet or Hashmicro Server Offline')
                });
                return false;
            }

            self.sync.state = 'connecting';
            let result = await self.rpc({
                model: 'pos.order',
                method: 'check_sync_order',
                args: [[], { 'order_uids': [order.name] }]
            }, {
                shadow: true,
                timeout: 5000 // 5 seconds
            }).then(function (response) {
                return response;
            }).guardedCatch(function (error) {
                if (error && error.message && error.message.code == -32098) {
                    console.error('[pushOrder] ~ Server Offline:', error)
                    self.env.pos.alert_message({
                        title: self.env._t('Offline'),
                        body: self.env._t('Your Internet or Hashmicro Server Offline...')
                    });
                } else {
                    error.event.preventDefault(); // Stop default popup error
                    console.error('[pushOrder] ~ Error 403', error);
                    Gui.showPopup('PosErrorMessagePopup', {
                        title: self.env._t('Failed Force Sync Order'),
                        message: error.message,
                    })
                }
                self.sync.state = 'error';
                return null;
            });
            console.warn('[pushOrder] ~ result:', result);

            if (result) {
                let order_log = JSON.parse(JSON.stringify(order));
                if (result.notsync_order_uids.length == 0) {
                    order_log.sync_state = 'Synced';
                    self.env.pos.update_order_history_local(order_log); // save to IndexedDB
                    self.env.pos.db.save_order_history_local([order_log]); // update variables
                    Gui.showPopup('ConfirmPopup', {
                        title: this.env._t('Force Sync'),
                        body: this.env._t('This order is already in the POS Orders'),
                        disableCancelButton: true,
                    });
                } else {
                    let data_orders = [self.env.pos._prepare_data_from_local_order_log(JSON.parse(JSON.stringify(order)))];
                    let push_order_one = await self.env.pos._force_push_orders(data_orders, { show_error: true }); 
                    if(push_order_one.length){
                        order_log.sync_state = 'Synced';
                        self.env.pos.update_order_history_local(order_log); // save to IndexedDB
                        self.env.pos.db.save_order_history_local([order_log]); // update variables
                        this.env.pos.alert_message({
                            title: this.env._t('Success'),
                            body: this.env._t('This order Successfully sync'),
                        });
                    }
                }
            }
            self.sync.state = 'done';
        }

    }

    OrderHistoryLocalDetail.template = 'OrderHistoryLocalDetail';
    Registries.Component.add(OrderHistoryLocalDetail);
    return OrderHistoryLocalDetail;
});
