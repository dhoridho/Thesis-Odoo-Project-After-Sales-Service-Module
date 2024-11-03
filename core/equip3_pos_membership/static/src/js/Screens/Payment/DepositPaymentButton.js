odoo.define('equip3_pos_membership.DepositPaymentButton', function (require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const DepositPaymentButton = require('equip3_pos_masterdata.DepositPaymentButton');
    

    const MembershipDepositPaymentButton = (DepositPaymentButton) =>
        class extends DepositPaymentButton { 
            
            constructor() {
                super(...arguments);
                this.currentOrder = this.env.pos.get_order();

            }

            is_hidden(){
                if(!this.env.pos.company.is_pos_use_deposit){
                    return true;
                }

                let client = this.currentOrder.get_client();
                if(client){
                    return false;
                }
                return true;
            }

            async useMemberDeposit() {
                let client = this.currentOrder.get_client();
                let deposit = this.env.pos.db.get_customer_deposit_by_partner_id(client.id);
                if(!deposit){
                    this.showPopup('ErrorPopup', {
                        title: 'Warning',
                        body: client.name + this.env._t(" don't have deposit."),
                    });
                    return;
                }

                let payment_method = _.find(this.env.pos.payment_methods, function (p) {
                    return p.is_deposit_payment == true;
                });
                if(!payment_method){
                    this.showPopup('ErrorPopup', {
                        title: 'Warning',
                        body: this.env._t('Payment method Deposit Payment is not found.')
                            + this.env._t('Please setup payment with field "Is Deposit Payment=True"')
                    });
                    return;
                }

                const {confirmed: c, payload: p} = await this.showPopup('ConfirmPopup', {
                    title: client.name,
                    body: this.env._t('Have Deposit: '  + this.env.pos.format_currency(deposit.remaining_amount,  this.currentOrder.currency) ),
                    confirmText: this.env._t('Use Deposit'),
                    cancelText: this.env._t('Close'),
                });
                if (c) {
                    let order_total = this.currentOrder.get_total_with_tax(); 
                    const {confirmed, payload} = await this.showPopup('MemberDepositPaymentPopups', {
                        client: client,
                        deposit: deposit,
                        order_total: order_total,
                        startingValue: order_total
                    });

                    if(confirmed){
                        if(payload.amount){
                            this.currentOrder.customer_deposit_id = deposit.id
                            this.currentOrder.add_paymentline(payment_method);
                            let paymentline = this.currentOrder.selected_paymentline;
                            paymentline.customer_deposit_id = deposit.id;
                            paymentline.set_amount(payload.amount);

                            return this.showPopup('ConfirmPopup', {
                                title: this.env._t('Successfully'),
                                body: this.env._t('Set deposit payment: ') + this.env.pos.format_currency(payload.amount),
                                cancelText: '',
                            });
                        }
                    }
                }
            }

        }

    Registries.Component.extend(DepositPaymentButton, MembershipDepositPaymentButton);
    return MembershipDepositPaymentButton;
});


