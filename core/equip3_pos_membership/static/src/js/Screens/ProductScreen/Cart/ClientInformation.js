odoo.define('equip3_pos_membership.ClientInformation', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class ClientInformation extends PosComponent {
        constructor() {
            super(...arguments);
            this.currentOrder = this.env.pos.get_order();
        }

        async usePointsDoPayment() {
            var client = this.currentOrder.get_client();
            if (!client) {
                const {confirmed, payload: newClient} = await this.env.pos.chrome.showTempScreen(
                    'ClientListScreen',
                    {client: null}
                );
                if (confirmed) {
                    this.currentOrder.set_client(newClient);
                } else {
                    return this.env.pos.alert_message({
                        title: this.env._t('Error'),
                        body: this.env._t('Required select customer for checking customer points')
                    })
                }

            } 
            if (!this.env.pos.rewards) {
                return this.showPopup('ConfirmPopup', {
                    title: this.env._t('Error'),
                    body: this.env._t('Your POS not set any Loyalty Program'),
                    disableCancelButton: true
                })
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
                this.currentOrder.setRewardProgram(reward)
            }
        }

    }

    Registries.Component.add(ClientInformation);
    return ClientInformation;
});
