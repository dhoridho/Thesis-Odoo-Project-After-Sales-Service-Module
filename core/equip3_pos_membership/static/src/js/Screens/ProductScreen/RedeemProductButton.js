odoo.define('equip3_pos_membership.RedeemProductButton', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');

    class RedeemProductButton extends PosComponent {
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

            let product_list = [];
            let reward = false;
            for(let redeem_product of this.env.pos.redeem_product){
                reward = redeem_product;
                for (let rule of redeem_product.gift_product_rule){
                    if(client['pos_loyalty_point'] > rule.redeem_point){
                        let product = this.env.pos.db.get_product_by_id(rule.product_id[0]);
                        if(!product){
                            console.error('Product ' + rule.product_id[1] + ' not available in POS');
                        }
                        if(product){
                            product_list.push(product);
                        }
                    }
                }
                break;
            }
            product_list = product_list.filter((p)=>p.is_gift_product == true);
            const list = product_list.map(product => ({
                id: product.id,
                label: product.display_name,
                isSelected: false,
                item: product
            }));
            let {confirmed, payload: product_gift} = await this.env.pos.chrome.showPopup('SelectionPopup', {
                title: this.env._t('Please select one Product need apply to customer'),
                list: list
            });
            if (confirmed) {
                this.currentOrder.setRedeemedProduct(product_gift, reward);
            }
        }

    }

    RedeemProductButton.template = 'RedeemProductButton';
    Registries.Component.add(RedeemProductButton);
    return RedeemProductButton;
});