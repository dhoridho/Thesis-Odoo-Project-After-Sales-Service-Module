odoo.define('equip3_pos_masterdata.DB', function (require) {
"use strict";

    var PosDB = require('point_of_sale.DB');

    PosDB.include({
        init: function (options) {
            this._super.apply(this, arguments);
            this.card_groups = [];
            this.card_payments = [];
            this.receipt_templates = []
            this.pos_weight_scale_barcode_format = []
            this.pos_weight_scale_barcode_format_line = []
        },
        set_pos_receipt_template:function(receipt_templates){
            this.receipt_templates = [];
            for(var i = 0, len = receipt_templates.length; i < len; i++){
                this.receipt_templates.push(receipt_templates[i]);
            }
        },
        set_card_groups:function(card_groups){
            this.card_groups = [];
            for(var i = 0, len = card_groups.length; i < len; i++){
                this.card_groups.push(card_groups[i]);
            }
        },
        get_receipt_templates: function(){
            return this.receipt_templates;
        },
        get_card_groups: function(){
            return this.card_groups;
        },
        set_card_payments:function(card_payments){
            this.card_payments = [];
            for(var i = 0, len = card_payments.length; i < len; i++){
                this.card_payments.push(card_payments[i]);
            }
        },
        get_card_payments: function(){
            return this.card_payments;
        },
        get_card_payments_types: function(){
            let type = {}
            for (let card of this.card_payments){
                if (type[card.card_type]){
                    type[card.card_type].push(card);
                } else {
                    type[card.card_type] = [];
                }
            }
            return type;
        },
        get_card_payment_by_group_id: function(gid){
            return this.card_payments.filter((cpid)=> cpid.card_group.length && cpid.card_group[0] == gid);
        },
        get_card_payment_by_id: function(scpid){
            var cardpayment =  this.card_payments.filter((cpid)=> cpid.id == scpid);
            if(cardpayment.length){
                return cardpayment[0];
            }
            return false;
        }

    });

});