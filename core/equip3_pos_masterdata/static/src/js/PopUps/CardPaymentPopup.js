odoo.define('equip3_pos_masterdata.CardPaymentPopup', function(require) {
   'use strict';

   const AbstractAwaitablePopup = require('point_of_sale.AbstractAwaitablePopup');
   const { useListener } = require('web.custom_hooks');
   const Registries = require('point_of_sale.Registries');
   const { useState } = owl.hooks;

   class CardPaymentPopup extends AbstractAwaitablePopup {
      constructor() {
         super(...arguments);
         let self = this;
         this.card_payments = this.get_card_payment();
         this.card_types = this.get_card_types();
         this.search_card_payment = false;

         this.state = useState({
            warning_message: '',

            card_group_id: false,
            card_type: false,
            card_payment_id: false,
            card_number: '',
            payment_mdr_id: false, // pos.payment.method.mdr
         });

         if (this.props.selected_payment) {
            self.state.card_number = self.props.selected_payment.card_number;
            self.search_card_payment = self.env.pos.db.get_card_payment_by_id(self.props.selected_payment.card_payment_id);
            setTimeout(async () => {
               if(self.state.card_number){
                  $(self.el).find('[name="card_number"]').val(self.state.card_number);
                  self._auto_select_values();
               }
            }, 300);
         }
      }

      get_card_payment(){
         let values = this.env.pos.db.get_card_payments();
         if (this.props.payment_method){
            let card_payment_ids = [];
            for (let data of this.get_mdr_datas(this.props.payment_method.id)){
               card_payment_ids = [...card_payment_ids, ...data.card_payment_ids];
            }
            values = values.filter((v)=>card_payment_ids.includes(v.id));
         }
         return values;
      }

      get_card_payment_by_card_type(mdr_type){
         let values = this.env.pos.db.get_card_payments();
         if (this.props.payment_method){
            let card_payment_ids = [];
            for (let data of this.get_mdr_datas(this.props.payment_method.id)){
               if (data.mdr_type == mdr_type) {
                  card_payment_ids = [...card_payment_ids, ...data.card_payment_ids];
               }
            }
            values = values.filter((v)=>card_payment_ids.includes(v.id));
         }
         return values;
      }

      get_card_types(){
         let values = [];
         let card_payments_types = this.env.pos.db.get_card_payments_types();
         for (let card_type in card_payments_types){
            values.push({
               name: card_type + ' Card',
               id: 'false;' + card_type,
            });
         }

         if (this.props.payment_method){
            let map = {}
            values = [];
            for (let data of this.get_mdr_datas(this.props.payment_method.id)){
               map[data.mdr_type] = data;
            }
            for (let card_type in map){
               values.push({
                  name: map[card_type].name,
                  id: map[card_type].id + ';' + map[card_type].mdr_type,
               })
            }
         }
         return values;
      }

      get_mdr_datas(payment_method_id) {
         let datas = [];
         let payment_method_mdr_by_payment_id = this.env.pos.db.payment_method_mdr_by_payment_id
         if(payment_method_mdr_by_payment_id && payment_method_mdr_by_payment_id[payment_method_id]){
            datas = payment_method_mdr_by_payment_id[payment_method_id];
         }
         return datas;
      }

      get_value(event){
         let value = event.target.value;
         if(jQuery.type( new String(event.target.value) ) === "string"){
            value = value.replace(',','');
         }
         return value;
      }

      _change_form() {
         this.state.warning_message = ''; 

         this.render();
      }

      _set_input(name, value) {
         $(this.el).find('[name="'+name+'"][value="'+value+'"]').click();
      }

      _reset_input(name) {
         this.state[name] = false;
         this.state[name + '_id'] = false;
         $(this.el).find('[name="'+name+'"]:checked').prop('checked', false);
      }

      _refresh_card_payment_form() {
         if (this.state.card_type && this.state.card_payment_id) {
            let card_payment = this.env.pos.db.get_card_payment_by_id(this.state.card_payment_id);
            if (card_payment.card_type != this.state.card_type) {
               this._reset_input('card_payment');
            } 
         }
         if (this.props.payment_method) {
            if (this.state.card_type){
               this.card_payments = this.get_card_payment_by_card_type(this.state.card_type);
            } else {
               this.card_payments = this.get_card_payment();
            }

            if(this.card_payments.length == 0){
               this._reset_input('card_payment');
            }
         }
      }

      _refresh_card_type_form() {
         if (this.state.card_payment_id) {
            let card_payment = this.env.pos.db.get_card_payment_by_id(this.state.card_payment_id);
            this._set_input('card_type', 'false;'+card_payment.card_type);
         }
      }

      _auto_select_values(){
         if (this.search_card_payment) {
            this._set_input('card_type', 'false;'+this.search_card_payment.card_type);
         } else {
            this._reset_input('card_type');
         }
         if (this.props.payment_method){
            for (let data of this.get_mdr_datas(this.props.payment_method.id)){
               if (data.card_payment_ids.includes(this.search_card_payment.id)){
                  this._set_input('card_type', data.id + ';' + data.mdr_type );
               }
            }
         }


         if (this.search_card_payment) {
            this._set_input('card_payment', this.search_card_payment.id);
         } else {
            this._reset_input('card_payment');
         }
      }

      onChangeCardNumber(ev){
         this.state.card_number = this.get_value(ev).replace(' ','');
         let card_payments = this.get_card_payment();
         let search_card_payment = card_payments.filter((p)=>p.BIN && this.state.card_number.startsWith(p.BIN));
         if (search_card_payment.length) {
            this.search_card_payment = search_card_payment[0];
         } else {
            this.search_card_payment = false;
         }

         this._auto_select_values();
      }

      onChangeCardPayment(ev){
         this.state.card_payment_id = parseInt(this.get_value(ev));
         let card_payment = this.env.pos.db.get_card_payment_by_id(this.state.card_payment_id);
         this.state.card_group_id = card_payment.card_group[0];

         this._refresh_card_type_form();
         this._change_form();
      }

      onChangeCardType(ev){
         this.state.card_type = '';
         this.state.payment_mdr_id = false;
         let value = this.get_value(ev).split(';');
         if(value.length == 2){
            if(!isNaN(this.state.payment_mdr_id)){
               this.state.card_type = value[1];
            }
            this.state.payment_mdr_id = parseInt(value[0]);
         }

         this._refresh_card_payment_form();
         this._change_form();
      }
     
      async confirm() {
         if(!this.state.card_number){
            this.state.warning_message = 'Please input card number first.'; 
            return false;
         }
         if(this.state.card_number.length < 6){
            this.state.warning_message = 'Please input card number with correctly.'; 
            return false;
         }
         let card_payment = this.env.pos.db.get_card_payment_by_id(this.state.card_payment_id);
         if(card_payment.BIN){
            let first_number = this.state.card_number.substring(0, 6);
            if(first_number != card_payment.BIN){
               this.state.warning_message = 'BIN not matched.';
               return false;
            } 
         }

         if(!this.state.card_type){
            this.state.warning_message = 'Please select type card first.';
            return false;
         }

         if(this.state.card_type != 'QRIS'){
            if(!this.state.card_payment_id){
               this.state.warning_message = 'Please select card payment first.';
               return false;
            }
         }
         await super.confirm();
      }

      async getPayload() {
         let values = {
            card_group_id: this.state.card_group_id,
            card_type: this.state.card_type,
            card_payment_id: this.state.card_payment_id,
            card_number: this.state.card_number,
            payment_mdr_id: this.state.payment_mdr_id,

         }
         return values
      }

      close_warning_message(ev){
         $(ev.target).addClass('oe_hidden');
      }
   }

   CardPaymentPopup.template = 'CardPaymentPopup'; 
   CardPaymentPopup.defaultProps = {
      title: 'Input Customer Card',
   };
   Registries.Component.add(CardPaymentPopup);
   return CardPaymentPopup;
});