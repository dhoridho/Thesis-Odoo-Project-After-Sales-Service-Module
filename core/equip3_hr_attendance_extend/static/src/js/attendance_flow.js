odoo.define('equip3_hr_attendance_extend.attendance_flow', function (require){
    "use strict";
        var core = require('web.core');
        var AbstractAction = require('web.AbstractAction');
        var session = require('web.session');
    
        var attendance_flow = AbstractAction.extend({
            contentTemplate: "attendance_configuration_action",
            hasControlPanel: !1,
            events: {
                "click button.btn-flow": "_onOpen",
                "click .accordion .accordion-item .accordion-header": "_onClickAccordion"
            },
            start: function() {
                var self = this;
                var master_data_attendance = self.$('#master-data-attendance')
                var generate_working_calendar = self.$('#btn-generate-working-calendar')
                var attendance_change_request = self.$('#btn-attendance-change-request')
                var employee_attendance = self.$('#btn-employee-attendance')
                var working_schedule_exchnage_to_approve = self.$('#btn-working-schedule-exchange-to-approve')
                var accordion_reporting = self.$('.accordion-reporting')
                var shift_variation = self.$('.shift-variation')
                var working_time = self.$('.working_time')
                var approval_matrix = self.$('.approval_matrix')

                this.getSession().user_has_group('hr_attendance.group_hr_attendance_user').then(function(has_group) {
                    if(!has_group) {
                        working_schedule_exchnage_to_approve.prop('disabled', true)
                        generate_working_calendar.prop('disabled',true)
                        attendance_change_request.prop('disabled',true)
                        employee_attendance.prop('disabled',true)
                    } 
                });

               

                this.getSession().user_has_group('equip3_hr_employee_access_right_setting.group_hr_attendance_hr_manager').then(function(has_group) {
                    if(!has_group) {
                        accordion_reporting.remove()
                        master_data_attendance.remove();
                    } 
                });

                this.getSession().user_has_group('hr_attendance.group_hr_attendance_manager').then(function(has_group) {
                    if(!has_group) {
                        shift_variation.remove();
                        working_time.remove();
                        approval_matrix.remove();
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
                if ( $button_name != 'action_none' ) {
                    self.do_action( $button_name);
                }
            }
        });
    
        core.action_registry.add('attendance_flow_tag', attendance_flow);
        return attendance_flow;
    });