odoo.define('equip3_school_flow_configuration.ems_flow', function (require){
    "use strict";
        var core = require('web.core');
        var AbstractAction = require('web.AbstractAction');
        var session = require('web.session');
        const TeacherAllowedMenus = ["equip3_school_flow_configuration.ems_flow_wizard_action_client",
                                     "equip3_school_flow_configuration.class_flow_wizard_action_client",
                                     "school.action_student_student_form_2",
                                     "equip3_school_operation.ems_subject_action",
                                     "equip3_school_operation.subject_score_action",
                                     "school.action_student_student_form_12",
                                     "equip3_school_operation.academic_tracking_action",
                                     "equip3_school_report.action_attendance_report",
                                     "equip3_school_operation.action_teacher_attendance"
                                    ]
    
        var ems_flow = AbstractAction.extend({
            contentTemplate: "ems_flow_wizard_action_one",
            hasControlPanel: !1,
            events: {
                "click button.btn-flow": "_onOpen",
                "click button.btn-flow-active": "_onOpen",
                "click button.btn-flow-deactive": "_onOpen",
                "click .accordion .accordion-item .accordion-header": "_onClickAccordion"
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
            _onOpen: async function(ev){
                let self = this;
                let $target = $(ev.currentTarget);
                var in_group_teacher = false;
                await session.user_has_group('school.group_school_teacher').then(function(has_group) {
                    in_group_teacher = has_group;
                });
                if(in_group_teacher) {
                    let _action_name = $target.attr('name');
                    if (! TeacherAllowedMenus.includes(_action_name)) {
                        $("#not_allowed_warning_modal").modal('show');
                        return;
                    }
                }
                self.do_action( $target.attr('name'));
            }
        });
    
        core.action_registry.add('ems_flow_tag', ems_flow);
        return ems_flow;
    });