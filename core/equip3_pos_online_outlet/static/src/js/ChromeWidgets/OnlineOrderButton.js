odoo.define('equip3_pos_online_outlet.OnlineOrderButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const {posbus} = require('point_of_sale.utils');

    class OnlineOrderButton extends PosComponent {
        constructor() {
            super(...arguments);
        }
        
        onClick() {
            this.showScreen('OnlineOrderList',{
                order: null,
                selectedClient: null,
                close_screen_button: true
            });
        }

        mounted() {
            posbus.on('reload-online-orders', this, this.render);
        }

        willUnmount() {
            posbus.off('reload-online-orders', this, null);
        }

        get isHidden() {
            return false;
        }
    }

    OnlineOrderButton.template = 'OnlineOrderButton';
    Registries.Component.add(OnlineOrderButton);
    return OnlineOrderButton;
});