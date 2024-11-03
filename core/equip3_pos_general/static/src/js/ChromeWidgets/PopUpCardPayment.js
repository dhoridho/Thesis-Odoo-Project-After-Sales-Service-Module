odoo.define('equip3_pos_masterdata.PopUpCardPayment', function(require) {
    'use strict';

    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const { useListener } = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const { useState } = owl.hooks;

    // formerly ConfirmPopupWidget
    class PopUpCardPayment extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            useListener('click-card-group', this._clickOnCardGroup);
            useListener('click-card-payment', this._clickOnCardPayment);
            this.state = useState({sel_card_group: null, card_payments: [], sel_card_payment: null});
         }
         async _clickOnCardGroup(event) {
            var card_group = event.detail;
            this.state.sel_card_group = card_group.id;
            this.state.card_payments = this.env.pos.db.get_card_payment_by_group_id(card_group.id);
            this.state.sel_card_payment = null;
         }
         async _clickOnCardPayment(event) {
            var card_payment = event.detail;
            this.state.sel_card_payment = card_payment.id;
         }
         get selected_group_id(){
            return this.state.sel_card_group;
         }
         get selected_card_payment(){
            return this.state.sel_card_payment;
         }
         get card_payments(){
            return this.state.card_payments
         }
         async getPayload() {
            return this.selected_card_payment;
         }
         async confirm() {
            if(this.elected_card_payment != null || !this.selected_card_payment){
               await this.showPopup('ErrorPopup', {
                  title: this.env._t('Not Selected Card Payment'),
                  body: this.env._t('Please Select Any One Card Payment!'),
               });
               return false;
            }

            let selectedOrder = this.env.pos.get_order();
            selectedOrder.remove_all_promotion_line();
            // reset the apply promotion button
            this.env.pos.apply_promotion_succeed = false;

            await super.confirm();
        }
    }
    PopUpCardPayment.template = 'PopUpCardPayment';
    PopUpCardPayment.defaultProps = {
        confirmText: 'Confirm',
        cancelText: 'Cancel',
        title: 'Choose a Card',
        card_groups: [],
    };

    Registries.Component.add(PopUpCardPayment);

    return PopUpCardPayment;
});
