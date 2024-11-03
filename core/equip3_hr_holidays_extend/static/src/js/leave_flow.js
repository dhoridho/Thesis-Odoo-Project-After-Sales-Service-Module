odoo.define('equip3_hr_holidays_extend.hr_leave_flow', function (require){
    "use strict";
        var core = require('web.core');
        var AbstractAction = require('web.AbstractAction');
        var session = require('web.session');
    
        var talent_management_flow = AbstractAction.extend({
            contentTemplate: "hr_leave_configuration_flow_action",
            hasControlPanel: !1,
            events: {
                "click button.btn-flow": "_onOpen",
                "click .accordion .accordion-item .accordion-header": "_onClickAccordion"
            },
            start: function() {
                var self = this;
                var master_data = self.$('.accordion-master-data')
                var reporting = self.$('.accordion-reporting')
                var allocation = self.$('.menu-button-generate-allocation')
                var leave_movement = self.$('.menu-button-leave-movement')
                var leave_balance = self.$('.menu-button-leave-balance')
                var leave_count = self.$('.menu-button-leave-count')
                var leaves = self.$('.menu-button-leaves')
                var leave_cancellation = self.$('.menu-button-leave-cancelation')
                
                this.getSession().user_has_group('equip3_hr_employee_access_right_setting.group_responsible').then(function(has_group) {
                    if(!has_group) {
                        leaves.prop('disabled', true)
                        
                        
                    } 
                });

                this.getSession().user_has_group('hr_holidays.group_hr_holidays_user').then(function(has_group) {
                    if(!has_group) {
                        master_data.remove()
                        reporting.remove()
                        allocation.prop('disabled', true)
                        leave_movement.prop('disabled', true)
                        leave_balance.prop('disabled', true)
                        leave_count.prop('disabled', true)
                        leave_cancellation.prop('disabled', true)
                        
                        
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
    
        core.action_registry.add('hr_leave_flow_tag', talent_management_flow);
        return talent_management_flow;
    });