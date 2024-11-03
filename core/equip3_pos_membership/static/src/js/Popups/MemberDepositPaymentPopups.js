odoo.define('equip3_pos_membership.MemberDepositPaymentPopups', function(require) {
    'use strict';

    const { useState } = owl;
    const { useListener } = require('web.custom_hooks');
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const NumberBuffer = require('point_of_sale.NumberBuffer');

    class MemberDepositPaymentPopups extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.currentOrder = this.env.pos.get_order();
            useListener('accept-input', this.confirm);
            useListener('close-this-popup', this.cancel);

            let startingBuffer = '';
            if (typeof this.props.startingValue === 'number' && this.props.startingValue > 0) {
                startingBuffer = this.props.startingValue.toString();
            }
            this.state = useState({
                error_msg: '',
                buffer: startingBuffer
            });

            NumberBuffer.use({
                nonKeyboardInputEvent: 'numpad-click-input',
                triggerAtEnter: 'accept-input',
                triggerAtEscape: 'close-this-popup',
                state: this.state,
            });
        }

        get decimalSeparator() {
            return this.env._t.database.parameters.decimal_point;
        }

        sendInput(key) {
            this.state.error_msg = '';
            this.trigger('numpad-click-input', { key });
        }

        get inputBuffer() {
            if (this.state.buffer === null) {
                return '';
            }
            return this.state.buffer;
        }

        get remainingAmount() {
            if (this.state.buffer === null) {
                return '';
            }
            let remaining_amount = this.props.deposit.remaining_amount;
            let value = this.state.buffer;
            if(value){
                remaining_amount = remaining_amount - parseFloat(value);
            }
            return this.env.pos.format_currency(remaining_amount,  this.currentOrder.currency);
        }
        
        confirm(event) {
            const bufferState = event.detail;
            this.state.error_msg = '';
            if (bufferState.buffer !== '') {
                if(parseFloat(this.state.buffer) > this.props.deposit.remaining_amount){
                    this.state.error_msg = 'cannot process more than your deposit amount';
                    return;
                }
                super.confirm();
            }
        }

        getPayload() {
            return {
                'amount': NumberBuffer.get()
            }
        }
    }

    MemberDepositPaymentPopups.template = 'MemberDepositPaymentPopups';
    MemberDepositPaymentPopups.defaultProps = {
        confirmText: 'Confirm',
        cancelText: 'Cancel',
        title: 'Use Deposit',
        body: '',
    };
    Registries.Component.add(MemberDepositPaymentPopups);
    return MemberDepositPaymentPopups;
});
