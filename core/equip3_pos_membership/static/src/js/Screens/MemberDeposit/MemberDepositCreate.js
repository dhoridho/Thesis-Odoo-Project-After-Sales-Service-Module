odoo.define('equip3_pos_membership.MemberDepositCreate', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const field_utils = require('web.field_utils');

    class MemberDepositCreate extends PosComponent {
        constructor() {
            super(...arguments);
            this.intFields = ['partner_id', 'payment_method_id'];
            this.currencyFields = ['amount'];
            this.changes = {
                'amount': 0,
                'partner_id': false,
                'payment_method_id': false,
            };
        }

        mounted() {
            this.env.bus.on('save-deposit-member', this, this.saveChanges);

            this.addEventListenerPartnerId();
            this.addEventFormatCurrency();
        }

        willUnmount() {
            this.env.bus.off('save-deposit-member', this);
        }

        get_payment_methods(){
            return this.env.pos.payment_methods;
        }

        /**
         * Save to field `changes` all input changes from the form fields.
         */
        captureChange(event) {
            this.changes[event.target.name] = event.target.value;
            $("input[name='remaining_amount']").val(event.target.value)
        }

        addEventListenerPartnerId() {
            let self = this;
            let disable_partner_ids = self.env.pos.db.customer_deposit_disable_partner_ids;
            setTimeout(function() {
                $('#member-deposit_partner_id').select2({
                    minimumInputLength: 1,
                    query: function(query) {
                        let results =  self.env.pos.db.search_partner(query.term.trim());
                        results = results.filter((m)=> m.is_pos_member && disable_partner_ids.includes(m.id) == false && m.name.toLowerCase().startsWith(query.term.trim().toLowerCase()) )
                                    .map((m)=>({ id: m.id, text: m.name }));
                        query.callback({results: results});
                        return;
                    },
                }).on('change', function(e) { 
                    let $i = $(this);
                    self.changes[$i.attr('name')] = $i.val();
                });
            }, 50);
        }

        addEventFormatCurrency(){
            let self = this;
            let $el = $(this.el);
            setTimeout(function() {
                $el.find('.need_separator').on('change keyup', function(event){
                    let $i = $( this );
                    var selection = window.getSelection().toString();
                    if ( selection !== '' ) {
                        return;
                    }
                    // When the arrow keys are pressed, abort.
                    if ( $.inArray( event.keyCode, [38,40,37,39] ) !== -1 ) {
                        return;
                    }
                    // format currency by commas
                    var input = $i.val();
                        input = input.replace('.00', '');
                        input = input.replace(/[\D\s\._\-]+/g, "");
                        input = input ? parseInt( input, 10 ) : 0;
                        $i.val( function() {
                            return ( input === 0 ) ? "" : input.toLocaleString( "en-US" );
                        } );
                });

            }, 50);
        }

        saveChanges() {
            let processedChanges = {};
            if(jQuery.type( new String(this.changes['amount']) ) === "string"){
                this.changes['amount'] = this.changes['amount'].replace(',','')
            }
            for (let [key, value] of Object.entries(this.changes)) {
                if (this.intFields.includes(key)) {
                    processedChanges[key] = parseInt(value) || false;
                }else if(this.currencyFields.includes(key)){
                    value = value.replace('.00', '');
                    value = value.replace(/[\D\s\._\-]+/g, '');
                    processedChanges[key] = parseInt(value) || false;
                } else {
                    processedChanges[key] = value;
                }
            }
            this.trigger('save-changes', { processedChanges });
        }

    }

    MemberDepositCreate.template = 'MemberDepositCreate';
    Registries.Component.add(MemberDepositCreate);
    return MemberDepositCreate;
});
