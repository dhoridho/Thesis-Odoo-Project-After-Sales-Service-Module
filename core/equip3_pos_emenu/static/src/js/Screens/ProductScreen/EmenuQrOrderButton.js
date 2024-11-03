odoo.define('equip3_pos_emenu.EmenuQrOrderButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');
    const core = require('web.core');
    const QWeb = core.qweb;
    const { useState } = owl.hooks;


    class EmenuQrOrderButton extends PosComponent {
        constructor() {
            super(...arguments);
            this.state = useState({
                sent_state: ''
            });
        }

        create_values(){
            let order = this.env.pos.get_order();
            let values = {
                order_session_uid: order.uid,
                pos_session_id: this.env.session.config.pos_session_id,
                pos_config_id: this.env.pos.config.id,
                table_id: order.table.id,
                floor_id: false,
            }
            if(order.floor){
                values['floor_id'] = order.floor.id;
            }
            if(order.table && order.table.floor){
                values['floor_id'] = order.table.floor.id;
            }
            return values
        }

        has_pos_restaurant_installed() {
            if (this.env && this.env.pos && this.env.pos.config ){
                if (this.env.pos.config.module_pos_restaurant && this.env.pos.config.floor_ids && this.env.pos.config.floor_ids.length > 0){
                    return true;
                }
            }
            return false;
        }

        get isHidden() {
            if (this.has_pos_restaurant_installed()) {
                return false;
            } else {
                return true;
            }
        }

        async onClick() {
            let self = this;
            let order = this.env.pos.get_order();
            let lines_count = order.get_orderlines().length;

            if(order.emenu_order_id){
                self.showPopup('ErrorPopup', {
                    title: self.env._t('Warning'),
                    body: self.env._t('QR Order already created'),
                });
                return;
            }

            if(lines_count > 0){
                self.showPopup('ErrorPopup', {
                    title: self.env._t('Warning'),
                    body: self.env._t('Please remove all items before QR Order'),
                });
                return;
            }

            let {confirmed} = await self.showPopup('ConfirmPopup', {
                title: self.env._t('Print QR Order'),
                body: self.env._t('Are you sure want to Print QR Order?'),
            });
            if (!confirmed){ return }

            if(self.state.sent_state != 'process'){
                self.state.sent_state = 'process';

                let response = await self.rpc({
                    model: 'pos.emenu.order',
                    method: 'action_create',
                    args: [[], self.create_values()],
                }).then(function (resp) { return resp });
                self.state.sent_state = 'done';

                if(response.status != 'success'){
                    console.warn('Error. Cannot Print QrCode ~ ', response);
                    return self.showPopup('ErrorPopup', {
                        title: self.env._t('Error'),
                        body: self.env._t('Cannot Print QrCode'),
                    });
                }
                if(response.status == 'success'){
                    order.is_emenu_order = true;
                    order.emenu_order_id = response.emenu_order_id;
                    order.emenu_status = 'created';
                    order.trigger('change', order); // save change to local storage

                    await self.showPopup('EmenuQrCodePopup', {
                        emenu_url: response.emenu_url,
                        printed_date: response.printed_date,
                    })
                }

            }
        }

    }

    EmenuQrOrderButton.template = 'EmenuQrOrderButton';
    Registries.Component.add(EmenuQrOrderButton);
    return EmenuQrOrderButton;
});
