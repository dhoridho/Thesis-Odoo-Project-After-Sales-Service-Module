odoo.define('equip3_hr_attendance_overtime.overtime_flow', function (require){
    "use strict";
        var core = require('web.core');
        var AbstractAction = require('web.AbstractAction');
        var session = require('web.session');
    
        var overtime_flow = AbstractAction.extend({
            contentTemplate: "overtime_configuration_action",
            hasControlPanel: !1,
            events: {
                "click button.btn-flow": "_onOpen",
                "click .accordion .accordion-item .accordion-header": "_onClickAccordion"
            },
            start: function() {
                var self = this;
                var master_data = self.$('.accordion-master-data')
                var reporting = self.$('.accordion-reporting')
                var overtime_request = self.$('.menu-button-overtime-request')
                var overtime_request_to_approve1 = self.$('.menu-button-overtime-request-to-approve1')
                var overtime_request_to_approve = self.$('.menu-button-overtime-request-to-approve')
                var actual_overtime_request = self.$('.menu-button-actual-overtime-request')
                var actual_overtime_to_approve = self.$('.menu-button-actual-overtime-to-approve')
                var actual_overtime_to_approve1 = self.$('.menu-button-actual-overtime-to-approve1')

                this.getSession().user_has_group('equip3_hr_attendance_overtime.group_overtime_team_approver').then(function(has_group) {
                    if(!has_group) {
                        overtime_request_to_approve.prop('disabled', true)
                        actual_overtime_to_approve.prop('disabled', true)
                        actual_overtime_to_approve1.prop('disabled', true)
                        overtime_request_to_approve1.prop('disabled', true)
                        
                    } 
                });
                this.getSession().user_has_group('equip3_hr_attendance_overtime.group_overtime_all_approver').then(function(has_group) {
                    if(!has_group) {
                        master_data.remove();
                        reporting.remove();
                        actual_overtime_request.prop('disabled', true)
                        overtime_request.prop('disabled', true)
                        
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
    
        core.action_registry.add('overtime_flow_tag', overtime_flow);
        return overtime_flow;
    });