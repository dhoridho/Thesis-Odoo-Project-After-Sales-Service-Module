odoo.define('equip3_pos_membership.PaymentLoyaltyRewardButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');
    
    class PaymentLoyaltyRewardButton extends PosComponent {
        constructor() {
            super(...arguments);
            this.currentOrder = this.env.pos.get_order();
        }

        get getLoyaltyPoints() {
            let order = this.env.pos.get_order();
            let client = order.get_client()
            if (!client || !this.env.pos.rewards || (client && client['pos_loyalty_point'] <= 0)) {
                return this.env._t('Loyalty not Available')
            } else {
                return this.env._t('Use Points: ') + this.env.pos.format_currency_no_symbol(client['pos_loyalty_point'])
            }
        } 
        
        async selectLoyaltyReward() {
            let client = this.currentOrder.get_client();
            if (!client) {
                const {confirmed, payload: newClient} = await this.env.pos.chrome.showTempScreen(
                    'ClientListScreen',
                    {client: null}
                );
                if (confirmed) {
                    this.currentOrder.set_client(newClient);
                    client = this.currentOrder.get_client();
                } else {
                    posbus.trigger('set-screen', 'Payment')
                    return this.showPopup('ErrorPopup', {
                        title: this.env._t('Error'),
                        body: this.env._t('Required select customer for checking customer points')
                    })
                }
                posbus.trigger('set-screen', 'Payment')

            }
            if (!client || !this.env.pos.rewards || client['pos_loyalty_point'] <= 0) {
                return this.showPopup('ErrorPopup', {
                    title: this.env._t('Warning'),
                    body: this.env._t('Customer not set or have not any Reward available in your POS')
                })
            }
            let {confirmed, payload: confirm} = await this.showPopup('ConfirmPopup', {
                title: client.name,
                body: this.env._t('Have total points: ') + this.env.pos.format_currency_no_symbol(client['pos_loyalty_point']),
                confirmText: this.env._t('Use Points now'),
                cancelText: this.env._t('Close')
            })
            if (confirmed) {
                const list = this.env.pos.rewards.map(reward => ({
                    id: reward.id,
                    label: reward.name,
                    isSelected: false,
                    item: reward,
                    membertype: reward.pos_loyalty_category_ids,
                }))
                const filteredArr = list.filter(obj => obj.membertype.includes(client.pos_loyalty_type[0]));

                let {confirmed, payload: reward} = await this.showPopup('SelectionPopup', {
                    title: this.env._t('Please select one Reward need apply to customer'),
                    list: filteredArr,
                });
                if (confirmed) {
                    await this.currentOrder.setRewardProgram(reward);
                }
            }
        }
    }

    PaymentLoyaltyRewardButton.template = 'PaymentLoyaltyRewardButton';
    Registries.Component.add(PaymentLoyaltyRewardButton);
    return PaymentLoyaltyRewardButton;
});

