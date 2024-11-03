odoo.define('equip3_pos_masterdata.PopUpChangeCartMobile', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const { useState } = owl.hooks;

    class PopUpChangeCartMobile extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);

            this.state = useState({
                quantity: this.props.quantity,
                quantity_changed: false,
                price: this.props.price,
                price_changed: false,
                unit: false,
            });
        }

        changeQty(ev) {
            let $i = $(ev.target);
            this.state.quantity = parseInt($i.val());
            if(this.state.quantity != this.props.quantity){
                this.state.quantity_changed = true;
                $i.addClass('changed');
            } else {
                this.state.quantity_changed = false;
                $i.removeClass('changed');
            }
        }

        clickChangeQty(action){
            if (action == 'plus') {
                this.state.quantity += 1;
            } else {
                if (this.state.quantity > 1){
                    this.state.quantity -= 1;
                } else {
                    this.state.quantity = 1;
                }
            }
        }

        changePrice(ev) {
            let $i = $(ev.target);
            this.state.price = parseInt($i.val());
            if(this.state.price != this.props.price){
                this.state.price_changed = true;
                $i.addClass('changed');
            } else {
                this.state.price_changed = false;
                $i.removeClass('changed');
            }
        }

        changeUnit(unit_id) {
            this.props.change_unit_list.forEach((l) => { l.isSelected = false; });

            let selected_unit = this.props.change_unit_list.filter((l)=>l.id==unit_id)[0];
            selected_unit.isSelected = true;
            this.state.unit = selected_unit;
        }

        async getPayload() {
            let values = {
                quantity: this.state.quantity,
                quantity_changed: this.state.quantity_changed,
                price: this.state.price,
                price_changed: this.state.price_changed,
            }
            if (this.state.unit){
                values['unit'] = this.props.change_unit_list.filter((l)=>l.id == this.state.unit.id)[0].item;
            }
            return values;
        }

        async confirm() {
            await super.confirm();
        }

        cancel() {
            this.trigger('close-popup');
        }

    }

    PopUpChangeCartMobile.template = 'PopUpChangeCartMobile';
    PopUpChangeCartMobile.defaultProps = {
        confirmText: 'Confirm',
        cancelText: 'Cancel',
        title: 'Change Estimation Ready Time (Duration)',
    };
    Registries.Component.add(PopUpChangeCartMobile);

    return PopUpChangeCartMobile;
});
