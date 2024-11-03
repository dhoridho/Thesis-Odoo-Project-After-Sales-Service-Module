odoo.define('equip3_pos_membership.MemberDepositPopups', function(require) {
    'use strict';

    const { useState } = owl;
    const { useListener } = require('web.custom_hooks');
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class MemberDepositPopups extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);

            this.state = useState({
                send_state: '',
            });
        }

        mounted() {
            super.mounted();
            let self = this;
            let members = self.env.pos.partners.filter((m)=>m.is_pos_member);
            let results = members;

            $("#member-deposit_partner_id").select2({
                minimumInputLength: 2,
                query: function(query) {
                    let key = query.term.toLowerCase();
                    results = members
                            .filter((m)=>m.name.toLowerCase().startsWith(key))
                            .map((m)=>({ id: m.id, text: m.name }));
                    query.callback({results: results});
                    return;
                },
            }).select2('val', []);
        }

        get_payment_methods(){
            let payment_methods = this.env.pos.payment_methods;
            return payment_methods;
        }

        get_deposit_values($popups){
            let values = {}
            let partner_id = $popups.find('[name="partner_id"]').val();
            let payment_method_id = $popups.find('[name="payment_method_id"]').val();
            let amount = $popups.find('[name="amount"]').val();

            values['partner_id'] = parseInt(partner_id);
            values['payment_method_id'] = parseInt(payment_method_id);
            values['amount'] = parseInt(amount);

            if(!partner_id || !payment_method_id){
                return false;
            }
            if(!amount){
                return false;
            }
            if(amount){
                if(parseInt(amount) <= 0){
                    return false
                }
            }
            return values
        }

        async save_deposit(ev){
            let self = this;
            let $btn = $(ev.target);
            let $popups = $btn.closest('.popups');

            let deposit_values = self.get_deposit_values($popups);
            if (!deposit_values){
                return;
            }
            if(self.state.send_state == 'process'){
                return;
            }

            self.state.send_state = 'process';
            await self.rpc({
                model: 'customer.deposit',
                method: 'action_create_deposit_from_pos',
                args: [[], {
                    'pos_session_id': self.env.pos.pos_session.id,
                    'pos_config_id': self.env.pos.config_id,
                    'deposit_values': self.get_deposit_values($popups),
                }],
                context: {}
            }).then(function (resp) {
                self.state.send_state = 'done';
                if(resp.status == 'success'){
                    return self.showPopup('ErrorPopup', {
                        title: 'Success',
                        body: 'Successfully create member deposit',
                    });
                }
                return self.showPopup('ErrorPopup', {
                    title: 'Error',
                    body: resp.message,
                });
            });

            self.state.send_state = 'done';
            self.confirm();
        }

        close(){
            if(this.state.send_state == 'process'){
                return;
            }
            this.trigger('close-popup');
        }

    }

    MemberDepositPopups.template = 'MemberDepositPopups';
    MemberDepositPopups.defaultProps = {
        confirmText: 'Confirm',
        cancelText: 'Cancel',
        title: 'Member Deposit',
        body: '',
        cheap: false,
        startingValue: null,
    };
    Registries.Component.add(MemberDepositPopups);
    return MemberDepositPopups;
});
