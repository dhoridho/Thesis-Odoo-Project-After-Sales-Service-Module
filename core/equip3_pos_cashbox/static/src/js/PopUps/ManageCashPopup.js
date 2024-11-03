odoo.define('equip3_pos_cashbox.ManageCashPopup', function (require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');

    class ManageCashPopup extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.state = useState({ 
                action: this.props.action,
                product_id: this.props.product_id,
                amount: this.props.amount,
                reason: this.props.reason,
            });
        }

        getProductServices(){
            if(this.env.pos.config.pos_cashbox_product_services){
                return JSON.parse(this.env.pos.config.pos_cashbox_product_services);
            }
            return [];
        }
        
        getPayload() {
            let values =  { 
                action: this.state.action,
                product_id: this.state.product_id,
                amount: this.state.amount,
                reason: '',
            }
            if(this.state.reason){
                values['reason'] = this.state.reason;
            }
            return values
        }

        confirm(){
            let has_error = [];
            $('.manage-cash-popup .manage-cash-group').removeClass('has_error');
            $('.manage-cash-popup .manage-cash-form > input[required], .manage-cash-popup .manage-cash-form > select[required]').each(function(){
                if($(this).val() == '' || $(this).val() == null){
                    has_error.push('required');
                    $(this).closest('.manage-cash-group').addClass('has_error');
                }
            });

            $('.manage-cash-popup .manage-cash-form > input[type=number]').each(function(){
                if(isNaN($(this).val())){
                    has_error.push('required');
                    $(this).closest('.manage-cash-group').addClass('has_error');
                }
            });

            if(has_error.length){
                return;
            }
            super.confirm();
        }
    }

    ManageCashPopup.template = 'ManageCashPopup';
    Registries.Component.add(ManageCashPopup);
    return ManageCashPopup;
});