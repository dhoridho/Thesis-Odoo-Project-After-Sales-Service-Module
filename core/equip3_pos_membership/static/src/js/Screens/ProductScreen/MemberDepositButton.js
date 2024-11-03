odoo.define('equip3_pos_membership.MemberDepositButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const {posbus} = require('point_of_sale.utils');
    const {Gui} = require('point_of_sale.Gui');

    class MemberDepositButton extends PosComponent {
        constructor() {
            super(...arguments);
        }
        
        async onClick() {
            // await Gui.showPopup('MemberDepositPopups');
            await this.env.pos.getCustomerDepositFromBackend();
            this.showScreen('MemberDepositList');
        }
    }

    MemberDepositButton.template = 'MemberDepositButton';
    ProductScreen.addControlButton({
        component: MemberDepositButton,
        condition: function() {
            return true;
        },
    });
    Registries.Component.add(MemberDepositButton);
    return MemberDepositButton;
});