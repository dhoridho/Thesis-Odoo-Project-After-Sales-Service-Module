odoo.define('equip3_pos_membership.MemberDepositAddPopups', function(require) {
    'use strict';

    const { useState } = owl;
    const { useListener } = require('web.custom_hooks');
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class MemberDepositAddPopups extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);

            this.deposit = this.props.deposit;
            this.state = useState({
                send_state: '',
                final_amount: 0,
                final_remaining_amount: 0,
            });
        }

        mounted() {
            super.mounted();
        }

        OnChange(event) {
            let amount = 0;
            var value = event.target.value
            if(jQuery.type( new String(event.target.value) ) === "string"){
                value = value.replace(',','')
            }
            let deposit_amount = parseInt(value);
            if(!isNaN(deposit_amount)){
                amount = deposit_amount;
            }

            let current_amount = this.deposit.amount;
            let current_remaining_amount = this.deposit.remaining_amount;
            var final_amount = (amount != 0) ? (amount + current_amount) : 0
            var final_remaining_amount = (amount != 0) ? (amount + current_remaining_amount) : 0
            this.state.final_amount = this.format_currency(final_amount)
            this.state.final_remaining_amount = this.format_currency(final_remaining_amount)
            event.target.value = this.format_currency(amount)
        }

        format_currency(value){
            // Format by commas
            let input = value.toLocaleString();
            input = input.replace('.00', '');
            input = input.replace(/[\D\s\._\-]+/g, "");
            input = input ? parseInt( input, 10 ) : 0;
            return ( input === 0 ) ? "" : input.toLocaleString( "en-US" );
        }

        reset_format_currency(value){
            value = value.replace('.00', '');
            value = value.replace(/[\D\s\._\-]+/g, '');
            return value
        }

        async save_deposit(ev){
            let self = this;
            let $popups = $(ev.target).closest('.popups');
            let deposit_amount = $popups.find('[name="deposit_amount"]').val();
            let payment_method_id = parseInt($popups.find('[name="payment_method_id"]').val());
            deposit_amount = parseInt(self.reset_format_currency(deposit_amount));
            
            if (isNaN(deposit_amount) || deposit_amount == 0){
                return;
            }
            if (isNaN(payment_method_id)){
                return;
            }
            if(self.state.send_state == 'process'){
                return;
            }

            self.state.send_state = 'process';
            let values = {
                'pos_session_id': self.env.pos.pos_session.id,
                'pos_config_id': self.env.pos.config_id,
                'deposit_amount': deposit_amount,
                'payment_method_id': payment_method_id,
                'customer_deposit_id': this.deposit.id,
            }
            
            await self.rpc({
                model: 'customer.deposit',
                method: 'action_add_deposit_from_pos',
                args: [[], values],
                context: {}
            }).then(function (resp) {
                self.state.send_state = 'done';
                if(resp.status == 'success'){
                    return self.showPopup('ConfirmPopup', {
                        title: self.env._t('Successfully'),
                        body: self.env._t('Successfully add deposit: ') + deposit_amount,
                        disableCancelButton: true,
                    });
                }
                return self.showPopup('ErrorPopup', {
                    title: 'Error',
                    body: resp.message,
                });
            });
            
            await self.env.pos.getCustomerDepositFromBackend();

            self.state.send_state = 'done';
            self.confirm();
        }

        get_payment_methods(){
            let payment_methods = this.env.pos.payment_methods.filter((p)=>{
                if(typeof p.is_edc_bca != 'undefined'){
                    if(!p.is_edc_bca && !p.is_receivables){
                        return true;
                    }
                }
                if(!p.is_receivables){
                    return true;
                }
                return false;
            });
            return payment_methods;
        }

        close(){
            if(this.state.send_state == 'process'){
                return;
            }
            this.trigger('close-popup');
        }

    }

    MemberDepositAddPopups.template = 'MemberDepositAddPopups';
    MemberDepositAddPopups.defaultProps = {
        confirmText: 'Confirm',
        cancelText: 'Cancel',
        title: 'Add Deposit',
        body: '',
        cheap: false,
        startingValue: null,
    };
    Registries.Component.add(MemberDepositAddPopups);
    return MemberDepositAddPopups;
});
