odoo.define('equip3_pos_membership.RedeemRewardButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');

    class RedeemRewardButton extends PosComponent {
        constructor() {
            super(...arguments);
            this.currentOrder = this.env.pos.get_order();
        }
 

        get isShown(){
            if(!this.currentOrder){
                return false;
            }
            var client = this.currentOrder.get_client();
            if(client && this.env.pos.config.is_allow_redeem_in_pos_screen){
                return true;
            }
            return false;
        }

        async onClick(){
            if(!this.currentOrder){
                return false;
            }
            var client = this.currentOrder.get_client();
            if (!client) {
                const {confirmed, payload: newClient} = await this.env.pos.chrome.showTempScreen(
                    'ClientListScreen',
                    {client: null, body: this.env._t('Required Customer')}
                );
                if (confirmed) {
                    this.currentOrder.set_client(newClient);
                } else {
                    const {confirmed, payload: confirm} = await this.env.pos.chrome('ErrorPopup', {
                        title: this.env._t('Error'),
                        body: this.env._t('Customer is required set to Order for checking points existing of Customer')
                    })
                    if (confirmed) {
                        const {confirmed, payload: newClient} = await this.env.pos.chrome.showTempScreen(
                            'ClientListScreen',
                            {client: null, body: this.env._t('Required Customer')}
                        )
                        if (confirmed) {
                            this.currentOrder.set_client(newClient);
                            return await this.selectLoyaltyReward()
                        }
                    }
                }

            }
            const list = this.env.pos.rewards.map(reward => ({
                id: reward.id,
                label: reward.name,
                isSelected: false,
                item: reward,
                membertype: reward.pos_loyalty_category_ids,
            }));
            const filteredArr = list.filter(obj => obj.membertype.includes(client.pos_loyalty_type[0]));

            let {confirmed, payload: reward} = await this.env.pos.chrome.showPopup('SelectionPopup', {
                title: this.env._t('Please select one Reward need apply to customer'),
                list: filteredArr,
            });
            if (confirmed) {
                this.currentOrder.setRewardProgram(reward)
            }
        }
    }

    RedeemRewardButton.template = 'RedeemRewardButton';
    Registries.Component.add(RedeemRewardButton);
    return RedeemRewardButton;
});