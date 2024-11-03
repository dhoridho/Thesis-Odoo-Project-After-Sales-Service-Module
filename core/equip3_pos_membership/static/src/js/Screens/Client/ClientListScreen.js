odoo.define('equip3_pos_membership.ClientListScreen', function (require) {
    'use strict';

    const ClientListScreen = require('equip3_pos_masterdata.ClientListScreen');
    const Registries = require('point_of_sale.Registries');
    const {posbus} = require('point_of_sale.utils');
    const {useState} = owl.hooks;

    const PosMemClientListScreen = (ClientListScreen) =>
        class extends ClientListScreen {
            constructor() {
                super(...arguments);
            } 
    
            get lineHeaders() {
                let value =  [
                    { 
                        name:'No.',
                        width: '10%',
                    }, 
                    { 
                        name:'Name',
                        width: '25%',
                    }, 
                    { 
                        name:'Address',
                        width: '20%',
                    }, 
                    { 
                        name:'Phone',
                        width: '10%',
                    }, 
                    { 
                        name:'Member Code',
                        width: '15%',
                    }, 
                    { 
                        name:'Member Point',
                        width: '10%',
                    }, 
                    { 
                        name:'Orders Count',
                        width: '10%',
                    }
                ];

                let res = super.lineHeaders;
                return value;
            }

            back() {
                const selectedOrder = this.env.pos.get_order(); 
                if(selectedOrder && selectedOrder.attributes){
                    selectedOrder.attributes.client = null;
                }
                if(selectedOrder && selectedOrder.orderlines){
                    selectedOrder.orderlines.models.forEach(l => {
                        if (l.is_product_redeemed) {
                            selectedOrder.remove_orderline(l);
                        }
                    });
                }
                return super.back();
            }

            setCustomerToCart(event) {
                const selectedOrder = this.env.pos.get_order(); 
                if(selectedOrder && selectedOrder.orderlines){
                    selectedOrder.orderlines.models.forEach(l => {
                        if (l.is_product_redeemed) {
                            selectedOrder.remove_orderline(l);
                        }
                    });
                }
                return super.setCustomerToCart(event);
            }

            getChangesValues(detail){
                let values = super.getChangesValues(detail);
                values['is_pos_member'] = true;
                return values;
            }

            is_allow_create_client(){
                if(this.env.pos.config.is_allow_create_member_in_pos_screen){
                    return true;
                }
                this.env.pos.alert_message({
                    title: this.env._t('Error'),
                    body: this.env._t('You have not permission create new Member')
                })
                return false;
            }

            sync_pos_partner_button_label(){
                let label = super.sync_pos_partner_button_label(event);
                return 'Sync Member';
            }

        }

        
    Registries.Component.extend(ClientListScreen, PosMemClientListScreen);
    return PosMemClientListScreen;
});
