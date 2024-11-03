odoo.define('equip3_pos_masterdata.PopUpSetPaymentMDR', function (require) {
    'use strict';

    const {useState, useRef, useContext} = owl.hooks;
    const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
    const Registries = require('point_of_sale.Registries');
    const contexts = require('point_of_sale.PosContext');
    const {useExternalListener} = owl.hooks;

    class PopUpSetPaymentMDR extends AbstractAwaitablePopup {
        constructor() {
            super(...arguments);
            this.props.select_card = false
            this.props.title = 'Select Payment'
            this.props.mdractive = []
            this.props.card_group_mdr = []
            this.props.card_payment_mdr = []
            this.props.error = false
        }
        async OnChangeCardGroup(event) {
            this.props.card_payment_mdr = []
            var card_group_id = parseInt(event.target.value)
            var mdractive = this.props.mdractive
            for (var i = 0; i < mdractive.card_payment_ids.length; i++) {
                var card_payment = this.props.card_payment.filter(p=>p.id==mdractive.card_payment_ids[i]);
                if(card_payment){
                    if(card_payment[0].card_group[0]==card_group_id){
                        this.props.card_payment_mdr.push({'id':card_payment[0].id,'name':card_payment[0].card_name})
                    }
                }                
            }
            this.render()
            
        }

        async confirm() {
            var card_group_id = $('select[name="card_group_mdr"]').val()
            var card_payment_id = $('select[name="card_payment_mdr"]').val()
            var card_number_mdr = $('input[name="card_number_mdr"]').val()
            var payment_mdr_id = this.props.mdractive.id
            var error = false
            this.props.error = false
            if(!card_group_id){
                error = true
                this.props.error = 'Please select card group first.'
            }
            else if(!card_payment_id){
                error = true
                this.props.error = 'Please select card first.'
            }
            else if(!card_number_mdr){
                error = true
                this.props.error = 'Please input card number first.'
            }
            if(!error){
                card_number_mdr = card_number_mdr.replace(' ','')
                if(card_number_mdr.length<6){
                    error = true
                    this.props.error = 'Please input card number with correctly.'
                }
            }
            if(!error){
                var card_payment = this.props.card_payment.filter(p=>p.id==parseInt(card_payment_id))[0];
                var bincard_number = card_number_mdr.substring(0, 6)
                if(card_payment.BIN){
                    if(bincard_number!=card_payment.BIN){
                        error = true
                        this.props.error = 'BIN not matched.'
                    } 
                }
            }
            if(error){
                this.render()
            }
            else{
                var card_group_id = parseInt(card_group_id)
                var card_payment_id = parseInt(card_payment_id)
                this.props.resolve({ confirmed: true, payload: {
                    card_number_mdr:card_number_mdr,
                    card_group_id:card_group_id,
                    card_payment_id:card_payment_id,
                    payment_mdr_id:payment_mdr_id,
                }});
                this.trigger('close-popup');
            }
            
        }

        mdrClick(event) {
            var idmdr = $(event.target).data('id');
            var mdractive = this.props.all_mdr.filter(p=>p.id==idmdr)[0];
            this.props.mdractive = mdractive
            this.props.select_card = true
            this.props.title = 'Input Customer Card'
            this.props.card_group_mdr = []
            this.props.card_payment_mdr = []
            if(mdractive.mdr_type=='QRIS'){
                this.props.resolve({ confirmed: true, payload: {
                    card_number_mdr:false,
                    card_group_id:false,
                    card_payment_id:false,
                    payment_mdr_id:mdractive.id,
                }});
                this.trigger('close-popup');
            }
            for (var i = 0; i < mdractive.card_group_ids.length; i++) {
                var card_group = this.props.card_groups.filter(p=>p.id==mdractive.card_group_ids[i]);
                if(card_group){
                    this.props.card_group_mdr.push({'id':card_group[0].id,'name':card_group[0].card_group_name})
                }
                
            }
            this.render()
        }
        

    }

    PopUpSetPaymentMDR.template = 'PopUpSetPaymentMDR';
    PopUpSetPaymentMDR.defaultProps = {
        confirmText: 'Ok',
        cancelText: 'Cancel',
        array: [],
        isSingleItem: false,
    };

    Registries.Component.add(PopUpSetPaymentMDR);

    return PopUpSetPaymentMDR
});
