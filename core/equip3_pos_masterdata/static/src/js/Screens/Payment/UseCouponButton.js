odoo.define('equip3_pos_masterdata.UseCouponButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');
    const core = require('web.core');
    const _t = core._t;
    
    class UseCouponButton extends PosComponent {
        constructor() {
            super(...arguments);
        }

        is_hidden(){
            return false;
        }

        async useCouponButton(){
            let order = this.env.pos.get_order();
            let order_lines = order.get_orderlines();

            if (order_lines.length <= 0) {
                return this.showPopup('ErrorPopup', {
                    title: this.env._t('Warning'),
                    body: this.env._t('Your cart is empty')
                })
            }

            const {confirmed, payload} = await this.showPopup('TextInputPopup', {
                title: _t('You can Scan to Coupon Barcode or Input Code direct here !'),
                body: _t('Please input Coupon Code or Number bellow'),
                startingValue: '',
                confirmText: this.env._t('Validate Code'),
                cancelText: this.env._t('Close'),
            });
            if (confirmed) {
                let number = payload.trim();
                if(!number){
                    return this.showPopup('ErrorPopup', {
                        title: _t('Warning'),
                        body: _t('Coupon Code not found'),
                    })
                }
                if (number) {
                    var selectedOrder = this.env.pos.get_order();
                    if (selectedOrder) {
                        return selectedOrder.client_use_coupon(number);
                    }
                }
            }

        }
    }

    UseCouponButton.template = 'UseCouponButton';
    Registries.Component.add(UseCouponButton);
    return UseCouponButton;
});