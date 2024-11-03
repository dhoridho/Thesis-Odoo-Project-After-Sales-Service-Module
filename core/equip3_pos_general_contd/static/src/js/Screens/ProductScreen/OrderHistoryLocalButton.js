odoo.define('equip3_pos_membership.OrderHistoryLocalButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const {posbus} = require('point_of_sale.utils');
    const {Gui} = require('point_of_sale.Gui');

    class OrderHistoryLocalButton extends PosComponent {
        constructor() {
            super(...arguments);
        }
        
        async onClick() {
            this.showScreen('OrderHistoryLocalList');
        }
    }

    OrderHistoryLocalButton.template = 'OrderHistoryLocalButton';
    ProductScreen.addControlButton({
        component: OrderHistoryLocalButton,
        condition: function() {
            return this.env.pos.config.is_save_order_history_local;
        },
    });
    Registries.Component.add(OrderHistoryLocalButton);
    return OrderHistoryLocalButton;
});