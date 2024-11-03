odoo.define('acs_hms_online_appointment.acs_hms_online_appointment', function (require) {
    "use strict";
    
    require('web.dom_ready');

    $("#AcsRecordSearch").on('keyup', function() {
        var input, filter, records, rec, i, txtValue;
        input = document.getElementById("AcsRecordSearch");
        filter = input.value.toUpperCase();
        records = document.getElementsByClassName("acs_physician_block");
        for (i = 0; i < records.length; i++) {
            rec = records[i].getElementsByClassName("acs_physician_name")[0];
            txtValue = rec.textContent || rec.innerText;
            if (txtValue.toUpperCase().indexOf(filter) > -1) {
                records[i].style.display = "";
            } else {
                records[i].style.display = "none";
            }
            var physicians = $(this).parents().find('.appoint_person_panel:visible');
            if (physicians.length) {
                physicians[0].click();
            }
        }
        var search_input = document.getElementById("AcsRecordSearch");
        search_input.focus(); 
    });

    $('.acs_appointment').on('change', "input[name='appoitment_by']", function () {
        var appoitment_by = $(this);
        var $physician_datas = $(this).parents().find('#acs_physician_datas');
        var $department_datas = $(this).parents().find('#acs_department_datas');
        if (appoitment_by.val()=='department') {
            $physician_datas.addClass('acs_hide');
            $department_datas.removeClass('acs_hide');
            var departments = $(this).parents().find('.appoint_department_panel');
            if (departments.length) {
                departments[0].click();
            }
        } else {
            $department_datas.addClass('acs_hide');
            $physician_datas.removeClass('acs_hide');
            var physicians = $(this).parents().find('.appoint_person_panel');
            if (physicians.length) {
                physicians[0].click();
            }
        }

    });

    var appoitment_by = $("input[name='appoitment_by']");
    if (appoitment_by.length) {
        $("input[name='appoitment_by']").change();
        $("input[name='appoitment_by']").attr('checked', true);
    }

    $('.acs_appointment_slot').click(function() {
        var schedule_slot_input = $("input[name='schedule_slot_id']");
        var slot_date_input = $("input[name='slot_date']");
        
        var $slot_date = $(this).parent().parent();
        var $each_appointment_slot = $(this).parents().find('.acs_appointment_slot');
        var $each_slot_date = $(this).parents().find('.acs_slot_date');

        if ($(this).hasClass('acs_active') == true) {
            $each_slot_date.removeClass('acs_active');
            $each_appointment_slot.removeClass('acs_active');
            slot_date_input.val(slotdate_id);
            schedule_slot_input.val(slotline_id);
            
        } else {
            $each_slot_date.removeClass('acs_active');
            $each_appointment_slot.removeClass('acs_active');
            $(this).addClass('acs_active');
            $slot_date.addClass('acs_active');

            var slotdate_id = $slot_date.data('slotdate-id');
            var slotline_id = $(this).data('slotline-id');
            slot_date_input.val(slotdate_id);
            schedule_slot_input.val(slotline_id);
        }
    });

});