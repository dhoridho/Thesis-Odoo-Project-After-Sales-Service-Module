odoo.define('equip3_pos_masterdata.CartPaymentButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');

    class CartPaymentButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('click', this.onClick);
        }
        async onClick() {
            const card_groups = this.env.pos.db.get_card_groups() || []
            const { confirmed, payload: selected_payment_card_id} = await this.showPopup('PopUpCardPayment', {
                card_groups: card_groups
            });
            if (confirmed) {
                this.env.pos.get_order().set_selected_card_payment_id(selected_payment_card_id);
                var card_payment_obj = this.env.pos.db.get_card_payment_by_id(selected_payment_card_id);
                return this.env.pos.alert_message({
                    title: this.env._t('Successfully...'),
                    body: this.env._t('Successfully Selected '+ card_payment_obj.card_name+ ' Card Payment.'),
                });
            }
        }
    }
    CartPaymentButton.template = 'CartPaymentButton';
    
    ProductScreen.addControlButton({
        component: CartPaymentButton,
        condition: function() {
            return true;
        },
    });

    Registries.Component.add(CartPaymentButton);

    return CartPaymentButton;
});
