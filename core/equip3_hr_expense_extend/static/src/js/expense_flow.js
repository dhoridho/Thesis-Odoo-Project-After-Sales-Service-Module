odoo.define('equip3_hr_expense_extend.expense_flow', function (require){
    "use strict";
        var core = require('web.core');
        var AbstractAction = require('web.AbstractAction');
        var session = require('web.session');
    
        var expense_flow = AbstractAction.extend({
            contentTemplate: "expense_configuration_action",
            hasControlPanel: !1,
            events: {
                "click button.btn-flow": "_onOpen",
                "click .accordion .accordion-item .accordion-header": "_onClickAccordion"
            },
            start: function() {
                var self = this;
                var master_data = self.$('.accordion-master-data')
                var reporting = self.$('.accordion-reporting')
                var expense_to_post = self.$('.expense-to-post')
                var expense_to_pay = self.$('.expense-to-pay')

                this.getSession().user_has_group('equip3_hr_attendance_overtime.group_overtime_team_approver').then(function(has_group) {
                    if(!has_group) {
                        expense_to_post.prop('disabled', true)
                        expense_to_pay.prop('disabled', true)
                        
                    } 
                });
                this.getSession().user_has_group('hr_expense.group_hr_expense_user').then(function(has_group) {
                    if(!has_group) {
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
    
        core.action_registry.add('expense_flow_tag', expense_flow);
        return expense_flow;
    });