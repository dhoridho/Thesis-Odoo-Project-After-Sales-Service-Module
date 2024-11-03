odoo.define('equip3_hr_employee_loan_extend.loan_flow', function (require){
    "use strict";
        var core = require('web.core');
        var AbstractAction = require('web.AbstractAction');
        var session = require('web.session');
    
        var loan_flow = AbstractAction.extend({
            contentTemplate: "loan_configuration_action",
            hasControlPanel: !1,
            events: {
                "click button.btn-flow": "_onOpen",
                "click .accordion .accordion-item .accordion-header": "_onClickAccordion"
            },
            start: function() {
                var self = this;
                var master_data = self.$('.accordion-master-data')
                var reporting = self.$('.accordion-reporting')
                var loan_to_approve = self.$('.menu-button-loan-requests-to-approve')
                var loan_to_disburse = self.$('.menu-button-loan-to-disburse')
                var cancellation_to_approve = self.$('.menu-button-loan-cancellation-to-approve')
                this.getSession().user_has_group('equip3_hr_employee_loan_extend.group_loan_supervisor').then(function(has_group) {
                    if(!has_group) {
                        cancellation_to_approve.prop('disabled', true)
                        
                    } 
                });
                this.getSession().user_has_group('equip3_hr_employee_loan_extend.group_loan_finance').then(function(has_group) {
                    if(!has_group) {
                        master_data.remove();
                        reporting.remove();
                        loan_to_approve.prop('disabled', true)
                        loan_to_disburse.prop('disabled', true)
                        
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
                self.do_action( $target.attr('name'));
            }
        });
    
        core.action_registry.add('loan_flow_tag', loan_flow);
        return loan_flow;
    });