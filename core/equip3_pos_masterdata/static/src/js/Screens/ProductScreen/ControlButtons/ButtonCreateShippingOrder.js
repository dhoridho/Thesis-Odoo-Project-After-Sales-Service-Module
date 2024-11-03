odoo.define('equip3_pos_masterdata.ButtonCreateShippingOrder', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const {useListener} = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const {Printer} = require('point_of_sale.Printer');
    const core = require('web.core');
    const _t = core._t;

    // TODO: let : là biến trong 1 khối, biến này được thay đổi giá trị và được duy trì trong khối mà thôi (khối là 1 block {} )
    // TODO: const : là 1 biến không bao giờ thay đổi và duy trì xuyên suốt trong 1 class

    class ButtonCreateShippingOrder extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
            this._currentOrder = this.env.pos.get_order();
            this._currentOrder.orderlines.on('change', this.render, this);
            this.env.pos.on('change:selectedOrder', this._updateCurrentOrder, this);
        }

        willUnmount() {
            this._currentOrder.orderlines.off('change', null, this);
            this.env.pos.off('change:selectedOrder', null, this);
        }

        get isHighlighted() {
            var order = this.env.pos.get_order();
            if (order && order.is_return) {
                return false;
            }
            if (order.get_client()) {
                return true
            } else {
                return false
            }
        }

        _updateCurrentOrder(pos, newSelectedOrder) {
            this._currentOrder.orderlines.off('change', null, this);
            if (newSelectedOrder) {
                this._currentOrder = newSelectedOrder;
                this._currentOrder.orderlines.on('change', this.render, this);
            }
        }

        async onClick() {
            let self = this;
            let order = this.env.pos.get_order();
            if (!order) {
                return this.env.pos.alert_message({
                    title: this.env._t('Warning!'),
                    body: this.env._t('Please create order first.'),
                });
            }
            await order._open_pop_up_home_delivery_order()
        }
    }

    ButtonCreateShippingOrder.template = 'ButtonCreateShippingOrder';

    ProductScreen.addControlButton({
        component: ButtonCreateShippingOrder,
        condition: function () {
            return this.env.pos.config.shipping_order;
        },
    });

    Registries.Component.add(ButtonCreateShippingOrder);

    return ButtonCreateShippingOrder;
});
