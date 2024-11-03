odoo.define('equip3_hr_cash_advance.cash_advance_flow', function (require){
    "use strict";
        var core = require('web.core');
        var AbstractAction = require('web.AbstractAction');
        var session = require('web.session');
    
        var cash_advance_flow = AbstractAction.extend({
            contentTemplate: "cash_advance_configuration_action",
            hasControlPanel: !1,
            events: {
                "click button.btn-flow": "_onOpen",
                "click .accordion .accordion-item .accordion-header": "_onClickAccordion"
            },
            start: function() {
                var self = this;
                var master_data = self.$('.accordion-master-data')
                var reporting = self.$('.accordion-reporting')
                var all_advance = self.$('.all-advance')
                var advance_to_approve = self.$('.advance-to-approve')
                var advance_to_pay = self.$('.advance-to-pay')

                this.getSession().user_has_group('equip3_hr_cash_advance.group_cash_advance_supervisor').then(function(has_group) {
                    if(!has_group) {
                        advance_to_approve.prop('disabled', true)
                        advance_to_pay.prop('disabled', true)
                        
                    } 
                });

                this.getSession().user_has_group('equip3_accounting_accessright_setting.group_cash_advance_manager').then(function(has_group) {
                    if(!has_group) {
                        all_advance.prop('disabled', true)
                        master_data.remove();
                        reporting.remove();
                        
                    } 
                });

               

                
                return this._super.apply(this, arguments);
            },
            _onClickAccordion: function(ev){
                let $target = $(ev.currentTarget);
                let _id = $target.attr('data-target');
                let $accordion = $(`#${_id}`);
                if($accordion.hasClass('show')){
                    $accordion.removeClass('show').addClass('collapse');
                    $accordion.parent().find('.accordion-button').addClass('collapse');
                }else{
                    $accordion.removeClass('collapse').addClass('show');
                    $accordion.parent().find('.accordion-button').removeClass('collapse');
                }
            },
            _onOpen: function(ev){ 
                let self = this;
                let $target = $(ev.currentTarget);
                let $button_name = $target.attr('name')
                if ($button_name != 'action_none'){
                    self.do_action( $button_name);
                }
            }
        });
    
        core.action_registry.add('cash_advance_flow_tag', cash_advance_flow);
        return cash_advance_flow;
    });