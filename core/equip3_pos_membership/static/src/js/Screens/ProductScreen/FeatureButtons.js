odoo.define('equip3_pos_membership.FeatureButtons', function (require) {
    'use strict';

    const FeatureButtons = require('equip3_pos_masterdata.FeatureButtons')
    const Registries = require('point_of_sale.Registries')

    const PosMemFeatureButtons = (FeatureButtons) =>
        class extends FeatureButtons {
            constructor() {
                super(...arguments);
            }

            async selectLoyaltyReward() {
                const selectedOrder = this.env.pos.get_order();
                var client = selectedOrder.get_client();
                if (!client) {
                    const {confirmed, payload: newClient} = await this.env.pos.chrome.showTempScreen(
                        'ClientListScreen',
                        {client: null, body: this.env._t('Required Customer')}
                    );
                    if (confirmed) {
                        selectedOrder.set_client(newClient);
                    } else {
                        const {confirmed, payload: confirm} = await this.env.showPopup('ErrorPopup', {
                            title: this.env._t('Error'),
                            body: this.env._t('Customer is required set to Order for checking points existing of Customer')
                        })
                        if (confirmed) {
                            const {confirmed, payload: newClient} = await this.env.pos.chrome.showTempScreen(
                                'ClientListScreen',
                                {client: null, body: this.env._t('Required Customer')}
                            )
                            if (confirmed) {
                                selectedOrder.set_client(newClient);
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
                }))
                const filteredArr = list.filter(obj => obj.membertype.includes(client.pos_loyalty_type[0]));

                let {confirmed, payload: reward} = await this.env.pos.chrome.showPopup('SelectionPopup', {
                    title: this.env._t('Please select one Reward need apply to customer'),
                    list: filteredArr,
                });
                if (confirmed) {
                    selectedOrder.setRewardProgram(reward)
                }
            }
        }
        
    Registries.Component.extend(FeatureButtons, PosMemFeatureButtons);
    return PosMemFeatureButtons;
});