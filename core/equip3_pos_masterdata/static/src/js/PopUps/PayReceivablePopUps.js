odoo.define('equip3_pos_general.PayReceivablePopUps', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const {useExternalListener} = owl.hooks;

    class PayReceivablePopUps extends AbstractAwaitablePopup {
        /**
         * @param {Object} props
         * @param {string} props.startingValue
         */

        constructor() {
            super(...arguments);

            useExternalListener(window, 'keyup', this._keyUp);
            this.env.pos.lockedUpdateOrderLines = true; // todo: we locked event keyboard when popup show, when this variable active, ProductScreen trigger method _updateSelectedOrderline wil return
        }

        mounted() {
            super.mounted();
            this.env.pos.lockedUpdateOrderLines = true; // todo: we locked event keyboard when popup show, when this variable active, ProductScreen trigger method _updateSelectedOrderline wil return
        }

        willUnmount() {
            super.willUnmount();
            const self = this;
            setTimeout(function () {
                self.env.pos.lockedUpdateOrderLines = false; // timeout 0.5 seconds unlock todo: we locked event keyboard when popup show, when this variable active, ProductScreen trigger method _updateSelectedOrderline wil return
            }, 500)
        }

        async _keyUp(event) {
            console.log('[PayReceivablePopUps_keyboardHandler]: ', event.key)
            if (event.key == 'Enter') {
                await this.confirm();
            }
        }

        async selectOption(event){  
            $('.pay_receivable_popups .pay-receivable-line').removeClass('selected');
            let $input = $(event.target).find('input');
            let $target = $input.closest('.pay-receivable-line');
            $input.click();
            if($target.hasClass('selected')){
                $target.removeClass('selected');
            }else{
                $target.addClass('selected');
            }
        }

        getSelectedPaymentMethodId(){
            let $payment_method = $('.pay_receivable_popups select[name=pay_receivable_payment_method]');
            return $payment_method.val();
        }
        
        getPayload() { 
            let $amount = $('.pay_receivable_popups input[name=pay_receivable_amount]');
            return {
                amount: parseInt($amount.val()),
                payment_method_id: parseInt(this.getSelectedPaymentMethodId()),
            }
        }

        confirm(){
            if(!this.getSelectedPaymentMethodId()){
                return;
            }
            super.confirm();
        }
    }
    
    PayReceivablePopUps.template = 'PayReceivablePopUps';
    PayReceivablePopUps.defaultProps = {
        confirmText: 'Make Payment',
        cancelText: 'Cancel',
        title: 'Pay Receivable',
        body: '',
    };
    Registries.Component.add(PayReceivablePopUps);
    return PayReceivablePopUps;
});
