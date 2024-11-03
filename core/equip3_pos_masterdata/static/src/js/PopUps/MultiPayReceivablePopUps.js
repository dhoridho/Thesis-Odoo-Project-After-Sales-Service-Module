odoo.define('equip3_pos_general.MultiPayReceivablePopUps', function(require) {
    'use strict';

    const { useState, useExternalListener } = owl.hooks;
    const { useListener } = require('web.custom_hooks');
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const NumberBuffer = require('point_of_sale.NumberBuffer');
    const utils = require('web.utils');
    const round_di = utils.round_decimals;

    class MultiPayReceivablePopUps extends AbstractAwaitablePopup {
        /**
         * @param {Object} props
         * @param {string} props.startingValue
         */

        constructor() {
            super(...arguments);

            useExternalListener(window, 'keyup', this._keyUp);
            this.env.pos.lockedUpdateOrderLines = true; // todo: we locked event keyboard when popup show, when this variable active, ProductScreen trigger method _updateSelectedOrderline wil return

            this.data_order = false;
            this.payments = false;
            this.order = this.props.order;
            this.state = useState({
                payments: [],
                selectedPayment: false,
                save_payment_state: '',
            });

            useListener('mpr-update-selected-payment', this.updateSelectedPayment);
            NumberBuffer.use({
                // The numberBuffer listens to this event to update its state.
                // Basically means 'update the buffer when this event is triggered'
                nonKeyboardInputEvent: 'input-from-numpad',
                // When the buffer is updated, trigger this event.
                // Note that the component listens to it.
                triggerAtInput: 'mpr-update-selected-payment',
            });
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
            console.log('[MultiPayReceivablePopUps_keyboardHandler]: ', event.key)
            if(this.is_saving_payment()){
                return;
            }

            // if (event.key == 'Enter') {
            //     await this.confirm();
            // }
        }

        async clickPaymentMethod(payment){
            if(this.is_saving_payment()){
                return;
            }
            this.setPayment(payment);
            this.selectPayment(payment);
        }

        getPayments(){
            return this.state.payments;
        }

        setPayment(payment){
            let ids = this.state.payments.map((p)=>p.id);
            if(ids.includes(payment.id) == false){
                let amount = this.getAmountDifferent();
                if(amount < 0){
                    amount = 0;
                }
                this.state.payments.push({
                    id: payment.id,
                    name: payment.name,
                    payment_method: payment, // pos.payment.method object
                    amount: amount,
                });
            }
        }

        deletePayment(payment){
            if(this.is_saving_payment()){
                return;
            }
            
            for (var i = this.state.payments.length - 1; i >= 0; i--) {
                if(this.state.payments[i].id == payment.id){
                    this.state.payments.splice(i, 1);
                }
            }
            NumberBuffer.reset();
        }

        updateSelectedPayment(){
            if(this.is_saving_payment()){
                return;
            }

            let selected_payment = this.getSelectedPayment();
            if(selected_payment){
                if (NumberBuffer.get() === null) {
                    this.deletePayment(payment);
                } else {
                    let amount = round_di(parseFloat(NumberBuffer.getFloat()) || 0, this.env.pos.currency.decimals);
                    selected_payment.amount = amount;
                }
            }
        }

        selectPayment(payment){
            this.state.selectedPayment = payment;
            NumberBuffer.reset();
        }

        getSelectedPayment(){
            if(this.state.selectedPayment && this.state.payments){
                return this.state.payments.find((line) => line.id === this.state.selectedPayment.id);
            }
            return false;
        }

        isSelectedPayment(payment){
            if(this.state.selectedPayment){
                if(payment.id == this.state.selectedPayment.id){
                    return true
                }
            }
            return false;
        }


        getAmountPaid(){
            let amounts = this.state.payments.map((p)=>p.amount);
            let amount_paid = amounts.reduce((accumulator, currentValue) => {
              return accumulator + currentValue
            },0);
            if(this.order.payment_paid){
                amount_paid += this.order.payment_paid;
            }
            return amount_paid;
        }

        getAmountDifferent(){
            let amount_paid = this.getAmountPaid();
            let amount_total = this.order.amount_total;
            return amount_total - amount_paid;
        }

        getSummary(){
            let amount_paid = this.getAmountPaid();
            let amount_different = this.getAmountDifferent();
            return {
                amount_different: amount_different,
                amount_paid: amount_paid,
            };
        }

        is_saving_payment(){
            if(this.state.save_payment_state == 'process'){
                return true;
            }
            return false;
        }

        async save_payment(){
            let self = this;
            if(self.state.payments.length==0){
                return;
            }
            if(this.is_saving_payment()){
                return;
            }
            self.state.save_payment_state = 'process';

            let payments = [];
            for(let payment of self.state.payments){
                payments.push({
                    id: payment.id,
                    amount: payment.amount,
                })
            }

            let result = await self.rpc({
                model: 'pos.make.payment',
                method: 'action_multipay_receivable_frontend',
                args: [[], {
                    'pos_order_id': self.props.order.id,
                    'payments': payments,
                    'pos_session_id': self.env.pos.pos_session.id
                }],
                context: {}
            }, {
                shadow: true,
                timeout: 1200000 // 20 minutes
            }).then(function (response) {
                return response;
            }, function (error) {
                if (error && error.message && error.message.code == -32098) {
                    console.error('[syncPromotions] ~ Server Offline')
                } else {
                    console.error('[syncPromotions] ~ Error 403')
                }
                self.state.save_payment_state = 'error';
                return null;
            });

            if (result != null) {
                if(result.status != 'success'){
                    return self.showPopup('ErrorPopup', {
                        title: 'Error',
                        body: 'Failed to complete payment',
                    });
                }
                if(result.status == 'success'){
                    self.data_order = result.data_order;
                    self.payments = result.payments;
                }
            }

            self.state.save_payment_state = 'done';
            super.confirm();
        }
 
        getPayload() { 
            return { 
                'data_order': this.data_order,
                'payments': this.payments,
            };
        }

        cancel(){
            if(this.is_saving_payment()){
                return;
            }
            super.cancel();
        }

        confirm(){
            super.confirm();
        }
    }
    
    MultiPayReceivablePopUps.template = 'MultiPayReceivablePopUps';
    Registries.Component.add(MultiPayReceivablePopUps);
    return MultiPayReceivablePopUps;
});
