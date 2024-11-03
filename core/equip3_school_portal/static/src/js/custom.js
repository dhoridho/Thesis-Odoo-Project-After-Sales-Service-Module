odoo.define('equip3_school_portal', function (require) {
    "use strict";
    var FormController = require('web.FormController');
    var Dialog = require('web.Dialog');

    FormController.include({
        form_submit: function () {
            if (this.$('.o_required').hasClass('form_submit')) {
                Dialog.alert(this, "Harap isi field yang ditandai sebagai wajib diisi.");
                return $.Deferred().reject();
            }
            return this._super.apply(this, arguments);
        },
    });
});

$(document).on('click', '#payment_validation', function(event) {
    $("#payment_validation_id").modal("show");
});

function checkPdpaConsent() {
    var pdpaConsentChecked = $('#pdpa_consent').prop('checked');
    var modalSubmitBtn = document.getElementById('modal_submit');

    if (pdpaConsentChecked){
        modalSubmitBtn.disabled = false;
    } else{
        modalSubmitBtn.disabled = true;
    }
}

function updateButtonOnClick() {
    var button = document.getElementById('form_submit');
    var sendingMessage = document.getElementById('sending_message');
    if (button) {
        button.disabled = true;
        button.form.submit();
        button.style.display = 'none';
        $("#sending_message").removeClass('d-none');
    }
}


setTimeout(function() {
    var calendarEl = document.getElementById('calendar');
    var data = $('.calendar_values').attr('value');
    if ($('#calendar').length && $('.calendar_values').length) {
        var calendar = new FullCalendar.Calendar(calendarEl, {
            plugins: [
                'moment',
                'interaction',
                'dayGrid',
                'timeGrid'
            ],
            views: {
                timeGridDay: {
                    columnHeaderFormat: 'LL'
                },
                timeGridWeek: {
                    columnHeaderFormat: 'ddd D'
                },
                dayGridMonth: {
                    columnHeaderFormat: 'dddd'
                }
            },
            height: 750,
            unselectAuto: false,
            events: JSON.parse(data),
        });
        calendar.render();
        $(document).on('click', '.fc-next-button', function(event) {
            $.ajax({
                url: "/add/calendar/event",
                data: {
                    start: moment(calendar.state.dateProfile.currentRange.start).format('YYYY-MM-DD'),
                    end: moment(calendar.state.dateProfile.currentRange.end).format('YYYY-MM-DD'),
                },
                type: 'POST',
            }).then(function (result) {
                result = JSON.parse(result);
                if (result.data !== undefined && result.data.length) {
                    _.each(result.data, function(item) {
                        if (calendar.getEventById(item.id) === null) {
                            calendar.addEvent(item);
                        }
                    });
                }
            });
        });
        $(document).on('click', '.fc-prev-button', function(event) {
            $.ajax({
                url: "/add/calendar/event",
                data: {
                    start: moment(calendar.state.dateProfile.currentRange.start).format('YYYY-MM-DD'),
                    end: moment(calendar.state.dateProfile.currentRange.end).format('YYYY-MM-DD'),
                },
                type: 'POST',
            }).then(function (result) {
                result = JSON.parse(result);
                if (result.data !== undefined && result.data.length) {
                    _.each(result.data, function(item) {
                        if (calendar.getEventById(item.id) === null) {
                            calendar.addEvent(item);
                        }
                    });
                }
            });
        });
    }
}, 100);


$(document).on('click', '#final_modal_validate', function(event) {
    var required = $(event.target).parents('.modal-content').find('input').filter('[required]:visible');
    var allRequired = false;
    required.each(function(){
        if($(this).val() == ''){
            allRequired = true;
            if ($(this).attr('required')) {
                $(this).addClass('required-class');
            }
        } else {
            $(this).removeClass('required-class');
        }
    });
    if (!allRequired) {
        var invoice_id = document.getElementById("invoice_id").value;
        var payment = document.getElementById("payment_mode").value;
        var amount = document.getElementById("amount").value;
        var date = document.getElementById("date_of_receipt").value;
        var receipt = document.getElementById("receipt_number").value;
        var remark = document.getElementById("remark").value;
        var proof_of_payment = $('#proof_of_payment').attr('src');
        var proof_of_payment_filename = document.getElementById("proof_of_payment_filename").value;
        $.ajax({
            url: "/student/payment/validation",
            data: {
                'invoice_id': invoice_id,
                'payment': payment,
                'amount': amount,
                'date': date,
                'receipt': receipt,
                'proof_of_payment': proof_of_payment,
                'proof_of_payment_filename': proof_of_payment_filename,
                'remark': remark
            },
            type: 'POST',
        }).then(function (result) {
            $("#payment_validation").attr('disabled', 'disabled');
            $("#payment_validation_id").modal("hide");
        });
    }
});

$(document).ready(function(){

    function hideShowPassTracker() {
        if ($('.type').val() == 'international_student') {
            $(".passtracker").show();
        } else {
            $(".passtracker").hide();
        }
    }
    
    hideShowPassTracker();
    $(document).on('change', '.type', function(event) {
        hideShowPassTracker();
    });

    $(".student-pic-fa-link").click(function(){
        $(".student_pic_browse").click(); 
    });
    
    // $("#category_section_1").multiselect();
    
    $(document).on("click", ".student_pic_browse", function() {
      var file = $(this).parents().find(".file");
      file.trigger("click");
    });
    $('input[name="student_image"]').change(function(e) {
      var fileName = e.target.files[0].name;
      $("#student_image").val(fileName);
    
      var reader = new FileReader();
      reader.onload = function(e) {
        // get loaded data and render thumbnail.
        if($('#admission_preview').length>0){
            document.getElementById("admission_preview").src = e.target.result;
        }
            
      };
      // read the image file as a data URL.
      reader.readAsDataURL(this.files[0]);
    });

    $('input[name="proof_of_payment"]').change(function(e) {
      var fileName = e.target.files[0].name;
      $('input[name="proof_of_payment_filename"]').val(fileName);
    
      var reader = new FileReader();
      reader.onload = function(e) {
            $('#proof_of_payment').attr('src', e.target.result.split('base64,')[1]);
      };
      reader.readAsDataURL(this.files[0]);
    });

    $('#submit_assignment').change(function() {
       var filename = $('input[type=file]').val().split('\\').pop();
        var lastIndex = filename.lastIndexOf("\\");   
        $('#file').val(filename);
    });

    $('#submit_additional').change(function() {
       var filename = $('input[type=file]').val().split('\\').pop();
        var lastIndex = filename.lastIndexOf("\\");
        $('#file').val(filename);
    });

    $(document).on('click', '.o_school_portal', function(event) {
        if ($(event.target).parent().data('id') && $(event.target).parent().data('action')) {
            window.location.href = $(event.target).parent().data('action');
        }
    });

    $(document).on('change', '#date_of_birth', function(event) {
        const dob = $(event.target).val();
        if (dob) {
            const today = new Date();
            const birthDate = new Date(dob);
            let ageCalc = today.getFullYear() - birthDate.getFullYear();
            const monthDiff = today.getMonth() - birthDate.getMonth();
            if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
                ageCalc--;
            }
            $('#age').val(ageCalc);
        }
    });
    
    $(document).on('click', '.exam_link', function(event) {
        event.stopPropagation();
        var href = $(event.target).data('href');
        var user = $(event.target).data('user');
        var exam = $(event.target).data('id');
        sessionStorage.setItem("exam_id", exam);
        sessionStorage.setItem("assignment_id", false);
        sessionStorage.setItem("additional_id", false);
        sessionStorage.setItem("exam_student_id", false);
        sessionStorage.setItem("user", user);
        window.location.href = href;
    });
    $(document).on('click', '.assignment_link', function(event) {
        event.stopPropagation();
        var href = $(event.target).data('href');
        var assignment_id = $(event.target).data('id');
        sessionStorage.setItem("assignment_id", assignment_id);
        sessionStorage.setItem("additional_id", false);
        sessionStorage.setItem("exam_id", false);
        window.location.href = href;
    });
    $(document).on('click', '.additional_link', function(event) {
        event.stopPropagation();
        var href = $(event.target).data('href');
        var additional_id = $(event.target).data('id');
        sessionStorage.setItem("additional_id", additional_id);
        sessionStorage.setItem("assignment_id", false);
        sessionStorage.setItem("exam_id", false);
        window.location.href = href;
    });
    $(document).on('click', '.back_home', function(event){
        event.stopPropagation();
        if (sessionStorage.assignment_id !== 'false' && sessionStorage.exam_id == 'false' &&sessionStorage.additional_id !== 'false') {
            window.location.href = "/student/assignment/" + parseInt(sessionStorage.assignment_id);
        }
        else if (sessionStorage.exam_id !== 'false' && sessionStorage.assignment_id == 'false' &&sessionStorage.additional_id !== 'false') {
            window.location.href = '/student/exam/';
        }
        else if (sessionStorage.additional_id !== 'false' && sessionStorage.assignment_id == 'false' && sessionStorage.exam_id !== 'false') {
            window.location.href = '/student/additional/' + parseInt(sessionStorage.additional_id);
        }
    });

    $(document).on('click', '#modal_form_submit', function(event) {
        var required = $('input,textarea,select').filter('[required]');
        var allRequired = true;


        var dob = new Date($('#student_date_of_birth').val());
        var today = new Date();
        var age = Math.floor((today-dob) / (365.25 * 24 * 60 * 60 * 1000));
        age = parseInt($("#age").val());

        required.each(function(){
            if($(this).val() == ''){
                allRequired = false;
                if ($(this).attr('required')) {
                    $(this).addClass('required-class');
                }
            } else {
                $(this).removeClass('required-class');
            }
        });

        if (allRequired){
            if (age < 18) {
                var age_modal = $("#age_model");
                age_modal.find('.modal-body h3 small').text('Age of student should be greater than '+ 18 +' years!');
                age_modal.modal("show");
            }
            else {
                $("#submit_modal").modal("show");
            }
        }
        else {
            $("#student_email")[0].setCustomValidity("");
            if($("#student_email")[0].validity.patternMismatch){
                $("#student_email").addClass('required-class');
                $("#student_email")[0].setCustomValidity("pleasa use the correct email format eg: yourname@domain.xyz");
                $("form")[0].reportValidity();
                return false;
            }
            $("#empty_warning_modal").modal("show");
        }
    });

    $("#student_email").on("change", function(e){
        let _val = $("#student_email").val();
        $("#student_email").val(_val.toLowerCase());
        $("#student_email")[0].setCustomValidity("");
        $("#student_email").removeClass('required-class');
        if($("#student_email")[0].validity.patternMismatch){
            $("#student_email").addClass('required-class');
            $("#student_email")[0].setCustomValidity("pleasa use the correct email format eg: yourname@domain.xyz");
            $("#student_email")[0].reportValidity();
            return false;
        }
    });

    $("#empty_warning_modal").on("hidden.bs.modal", function () {
        var required = $('input,textarea,select').filter('[required]');
        required.each(function(){
            if($(this).val() == ''){
                let tab_pane = $(this).closest(".tab-pane");
                if (tab_pane.length > 0){
                    $('.nav-tabs a[href="#' + tab_pane[0].id + '"]').tab('show');
                }
                setTimeout(function(){},500);
                $(this)[0].reportValidity();
                $(this).focus();
                return false;
            }
        });
    });

    $(document).on('click', '#modal_submit', function(event) {
        var $rows = $('.parent_profile_o2m > tbody > tr:not(.d-none)');
        var parent_data = [];
        _.each($rows, function(row) {
            let id = $(row).data('id') ? $(row).data('id') : ''; 
            let name = $(row).find('input[data-name="name"]').val();
            let phone = $(row).find('input[data-name="phone"]').val();
            let mobile = $(row).find('input[data-name="mobile"]').val();
            let email = $(row).find('input[data-name="email"]').val();
            let title = $(row).find('select[data-name="parent_title"]').val();
            let language = $(row).find('select[data-name="language"]').val();
            let address = $(row).find('input[data-name="address"]').val();
            let parent_relation = $(row).find('select[data-name="parent_relation"]').val();
            let country_id = $(row).find('select[data-name="country_id"]').val();
            let city = $(row).find('input[data-name="city"]').val();
            let state_id = $(row).find('select[data-name="state_id"]').val();
            let zip = $(row).find('input[data-name="zip"]').val();
            parent_data.push({
                'name': name,
                'id': id,
                'phone': phone,
                'mobile': mobile,
                'email': email,
                'title': title != '' ? parseInt(title) : '',
                'lang': language,
                'street': address,
                'relation_id': parent_relation != '' ? parseInt(parent_relation) : '',
                'country_id': country_id != '' ? parseInt(country_id) : '',
                'city': city,
                'state_id': state_id != '' ? parseInt(state_id) : '',
                'zip': zip,
            })
        });
        $('textarea[name="parent_data"]').val(JSON.stringify(parent_data));

        var $references = $('.parent_references_o2m > tbody > tr:not(.d-none)');
        var references_data = [];
        _.each($references, function(row) {
            let id = $(row).data('id') ? $(row).data('id') : ''; 
            let name = $(row).find('input[data-name="first_name"]').val();
            let middle = $(row).find('input[data-name="middle_name"]').val();
            let last = $(row).find('input[data-name="surname"]').val();
            let designation = $(row).find('input[data-name="designation"]').val();
            let email = $(row).find('input[data-name="email"]').val();
            let phone = $(row).find('input[data-name="phone"]').val();
            let gender = $(row).find('select[data-name="ref_gender"]').val();
            references_data.push({
                'name': name,
                'middle': middle,
                'last': last,
                'id': id,
                'designation': designation,
                'email': email,
                'phone': phone,
                'gender': gender,

            })
        });
        $('textarea[name="references_data"]').val(JSON.stringify(references_data));
        var $previous = $('.previous_school_o2m > tbody > tr:not(.d-none)');
        var previous_school_data = [];
        _.each($previous, function(row) {
            let id = $(row).data('id') ? $(row).data('id') : ''; 
            let name = $(row).find('input[data-name="name"]').val();
            let admission_date = $(row).find('input[data-name="admission_date"]').val();
            let course_id = $(row).find('select[data-name="course"]').val();
            let registration_no = $(row).find('input[data-name="registration_no"]').val();
            let exit_date = $(row).find('input[data-name="exit_date"]').val();
            previous_school_data.push({
                'name': name,
                'id': id,
                'admission_date': admission_date,
                'course_id': course_id != '' ? parseInt(course_id) : '',
                'registration_no': registration_no,
                'exit_date': exit_date,

            })
        });
        $('textarea[name="previous_school_data"]').val(JSON.stringify(previous_school_data));
        var $family = $('.family_details_o2m > tbody > tr:not(.d-none)');
        var family_data = [];
        _.each($family, function(row) {
            let id = $(row).data('id') ? $(row).data('id') : ''; 
            let rel_name = $(row).find('select[data-name="related_student"]').val();
            let name = $(row).find('input[data-name="r_name"]').val();
            let stu_name = $(row).find('select[data-name="existing_student"]').val();
            let relation = $(row).find('select[data-name="family_relation"]').val();
            let email = $(row).find('input[data-name="email"]').val();
            let phone = $(row).find('input[data-name="phone"]').val();

            family_data.push({
                'rel_name': rel_name,
                'id': id,
                'name': rel_name === 'new' ? name : '',
                'stu_name': rel_name === 'exist' ? parseInt(stu_name) : false,
                'relation': relation != '' ? parseInt(relation) : '',
                'email': email,
                'phone': phone

            })
        });
        $('textarea[name="family_data"]').val(JSON.stringify(family_data));
        if (!$('#pdpa_consent').prop('checked')) {
            $("#ok_modal").modal("show");
        }
        else{
            $('.student_type').removeAttr('disabled');
            $('.existing_student_name').removeAttr('disabled');

        }
        $('#thank_submission_modal').modal('show');
        // $("#form_submit").click();
    });

    $(document).on('click', '#modal_form_save_as_draft', function(event) {
        var required = $('input,textarea,select').filter('[required]:visible');
        var allRequired = true;

        var dob = new Date($('#student_date_of_birth').val());
        var today = new Date();
        var age = Math.floor((today-dob) / (365.25 * 24 * 60 * 60 * 1000));

        required.each(function(){
            if($(this).val() == ''){
                allRequired = false;
            }
        });
        if (allRequired){ 
            if (age < 18) {
                var age_modal = $("#age_model");
                age_modal.find('.modal-body h3 small').text('Age of student should be greater than '+ 18 +' years!');
                age_modal.modal("show");
            } else {
                $('#save_draft_modal').modal('show');
            }
        } else {
            $("#form_submit").click();
        }
    });

    $(document).on('click', '.draft_modal', function(event) {
        var $rows = $('.parent_profile_o2m > tbody > tr:not(.d-none)');
        var parent_data = [];
        _.each($rows, function(row) {
            let id = $(row).data('id') ? $(row).data('id') : ''; 
            let name = $(row).find('input[data-name="name"]').val();
            let phone = $(row).find('input[data-name="phone"]').val();
            let mobile = $(row).find('input[data-name="mobile"]').val();
            let email = $(row).find('input[data-name="email"]').val();
            let title = $(row).find('select[data-name="parent_title"]').val();
            let language = $(row).find('select[data-name="language"]').val();
            let address = $(row).find('input[data-name="address"]').val();
            let parent_relation = $(row).find('select[data-name="parent_relation"]').val();
            let country_id = $(row).find('select[data-name="country_id"]').val();
            let city = $(row).find('input[data-name="city"]').val();
            let state_id = $(row).find('select[data-name="state_id"]').val();
            let zip = $(row).find('input[data-name="zip"]').val();
            parent_data.push({
                'name': name,
                'id': id,
                'phone': phone,
                'mobile': mobile,
                'email': email,
                'title': title != '' ? parseInt(title) : '',
                'lang': language,
                'street': address,
                'relation_id': parent_relation != '' ? parseInt(parent_relation) : '',
                'country_id': country_id != '' ? parseInt(country_id) : '',
                'city': city,
                'state_id': state_id != '' ? parseInt(state_id) : '',
                'zip': zip,
            })
        });
        $('textarea[name="parent_data"]').val(JSON.stringify(parent_data));

        var $references = $('.parent_references_o2m > tbody > tr:not(.d-none)');
        var references_data = [];
        _.each($references, function(row) {
            let id = $(row).data('id') ? $(row).data('id') : ''; 
            let name = $(row).find('input[data-name="first_name"]').val();
            let middle = $(row).find('input[data-name="middle_name"]').val();
            let last = $(row).find('input[data-name="surname"]').val();
            let designation = $(row).find('input[data-name="designation"]').val();
            let email = $(row).find('input[data-name="email"]').val();
            let phone = $(row).find('input[data-name="phone"]').val();
            let gender = $(row).find('select[data-name="ref_gender"]').val();
            references_data.push({
                'name': name,
                'middle': middle,
                'last': last,
                'id': id,
                'designation': designation,
                'email': email,
                'phone': phone,
                'gender': gender,

            })
        });
        $('textarea[name="references_data"]').val(JSON.stringify(references_data));
        var $previous = $('.previous_school_o2m > tbody > tr:not(.d-none)');
        var previous_school_data = [];
        _.each($previous, function(row) {
            let id = $(row).data('id') ? $(row).data('id') : ''; 
            let name = $(row).find('input[data-name="name"]').val();
            let admission_date = $(row).find('input[data-name="admission_date"]').val();
            let course_id = $(row).find('select[data-name="course"]').val();
            let registration_no = $(row).find('input[data-name="registration_no"]').val();
            let exit_date = $(row).find('input[data-name="exit_date"]').val();
            previous_school_data.push({
                'name': name,
                'id': id,
                'admission_date': admission_date,
                'course_id': course_id != '' ? parseInt(course_id) : '',
                'registration_no': registration_no,
                'exit_date': exit_date,

            })
        });
        $('textarea[name="previous_school_data"]').val(JSON.stringify(previous_school_data));
        var $family = $('.family_details_o2m > tbody > tr:not(.d-none)');
        var family_data = [];
        _.each($family, function(row) {
            let id = $(row).data('id') ? $(row).data('id') : ''; 
            let rel_name = $(row).find('select[data-name="related_student"]').val();
            let name = $(row).find('input[data-name="r_name"]').val();
            let stu_name = $(row).find('select[data-name="existing_student"]').val();
            let relation = $(row).find('select[data-name="family_relation"]').val();
            let email = $(row).find('input[data-name="email"]').val();
            let phone = $(row).find('input[data-name="phone"]').val();

            family_data.push({
                'rel_name': rel_name,
                'id': id,
                'name': rel_name === 'new' ? name : '',
                'stu_name': rel_name === 'exist' ? parseInt(stu_name) : false,
                'relation': relation != '' ? parseInt(relation) : '',
                'email': email,
                'phone': phone

            })
        });
        $('textarea[name="family_data"]').val(JSON.stringify(family_data));
        $('input[name="save_as_draft"]').prop('checked', true)
        $('.student_type').removeAttr('disabled');
        $('.existing_student_name').removeAttr('disabled');
        $("#form_submit").click();
    });

    $(document).on('click', '.student_save', function(event) {
        var $rows = $('.parent_profile_o2m > tbody > tr:not(.d-none)');
        var parent_data = [];
        _.each($rows, function(row) {
            let id = $(row).data('id');
            let name = $(row).find('input[data-name="parent_name"]').val();
            let parent_relation = $(row).find('select[data-name="parent_relation"]').val();
            let phone = $(row).find('input[data-name="parent_phone"]').val();
            let email = $(row).find('input[data-name="parent_email"]').val();
            let city = $(row).find('input[data-name="parent_city"]').val();
            let country_id = $(row).find('select[data-name="country_id"]').val();
            parent_data.push({
                'id': id,
                'name': name,
                'phone': phone,
                'email': email,
                'relation_id': parent_relation != '' ? parseInt(parent_relation) : '',
                'country_id': country_id != '' ? parseInt(country_id) : '',
                'city': city,
            })
        });
        $('textarea[name="parent_data"]').val(JSON.stringify(parent_data));
        var $family = $('.family_details_o2m > tbody > tr:not(.d-none)');
        var family_data = [];
        _.each($family, function(row) {
            let id = $(row).data('id');
            let rel_name = $(row).find('select[data-name="related_student"]').val();
            let name = $(row).find('input[data-name="r_name"]').val();
            let stu_name = $(row).find('select[data-name="existing_student"]').val();
            let relation = $(row).find('select[data-name="family_relation"]').val();
            let email = $(row).find('input[data-name="email"]').val();
            let phone = $(row).find('input[data-name="phone"]').val();

            family_data.push({
                'id': id,
                'rel_name': rel_name,
                'name': rel_name === 'new' ? name : '',
                'stu_name': rel_name === 'exist' ? parseInt(stu_name) : false,
                'relation': relation != '' ? parseInt(relation) : '',
                'email': email,
                'phone': phone

            })
        });
        $('textarea[name="family_data"]').val(JSON.stringify(family_data));
        $('.student_form_save').click();
    });

    $(document).on('click', '#modal_submit_assignment', function(event) {
        if( document.getElementById("submit_assignment").files.length == 0 ){
            document.getElementById('student_assignment_submit').click();
        }else{
            $("#assignment_modal").modal("show");
        }
        
    });

    $(document).on('click', '#modal_additional_exam', function(event) {
        if( document.getElementById("submit_additional").files.length == 0 ){
            document.getElementById('additional_exam_submit').click();
        }else {
        $("#additional_modal").modal("show");
        }
    });

    $(document).on('change', '.related_student', function(event) {
        var $tr = $(event.currentTarget).closest('tr');
        var related_student_value = $(event.currentTarget).val();
        if (related_student_value === 'exist') {
            $tr.find('select[data-name="existing_student"]').removeAttr('disabled');
            $tr.find('input[data-name="r_name"]').attr('disabled', 'disabled');
        }
        else if (related_student_value === 'new') {
            $tr.find('select[data-name="existing_student"]').attr('disabled', 'disabled');
            $tr.find('input[data-name="r_name"]').removeAttr('disabled');
        }
        else {
            $tr.find('input[data-name="r_name"]').attr('disabled', 'disabled');
            $tr.find('select[data-name="existing_student"]').attr('disabled', 'disabled');
        }
    });

    $(document).on('change', '.student_type', function(event){
        if(this.value == 'existing_student'){
            $(".existing_student_name").removeClass('d-none');
        }
        else {
            $(".existing_student_name").addClass('d-none');
        }
    });
    
    // $(document).on('change', '.academic_year', function(event){
    //     var academic = $(event.target).val();
    //     var academic_year = $('select[name="academic_year"]').val();
    //     var value = parseInt(academic)
    //     $('#student_term').html('');
    //     if (academic_year){
    //         $.ajax({
    //             url : "/student/academic/year",
    //             data: {
    //                 'academic_id': value
    //             },
    //             type: 'POST',
    //         }).then(function(result){
    //             result = JSON.parse(result);
    //             _.each(result, function(item) {
    //                 var option = $('<option/>')
    //                 option.attr('value', item.id)
    //                 option.text(item.name)
    //                 $('#student_term').append(option)
    //             });
    //         })
    //     }
    // });

    // $(document).on('change', '#program_id', function(event){
    //     var program_id = $(event.target).val();
    //     var value = parseInt(program_id)
    //     $('#standard_id').html('');
    //     $.ajax({
    //         url : "/program/intake",
    //         data: {
    //             'program_id': value
    //         },
    //         type: 'POST',
    //     })
    //     .then(function(result){
    //         result = JSON.parse(result);
    //         var option = $('<option/>')
    //         option.attr('value', -1)
    //         option.text("Intake")
    //         $('#standard_id').append(option)
    //         _.each(result, function(item) {
    //             option = $('<option/>')
    //             option.attr('value', item.id)
    //             option.text(item.name)
    //             $('#standard_id').append(option)
    //         });
    //     })
    // }); 


function get_program_intake (program_id = parseInt($('select[name="program_id"]').val()), academic_year = parseInt($('select[name="academic_year"]').val())){
    $('#standard_id').html('');
    var option = $('<option/>');
    option.attr('value', "");
    option.text('Intake');
    $('#standard_id').append(option);
    if (program_id && academic_year) {
        $.ajax({
            url : "/program/intake",
            data: {
                'program_id': parseInt(program_id),
                'academic_year': parseInt(academic_year),
            },
            type: 'POST',
            }).then(function(result){
                result = JSON.parse(result);
                $('#standard_id').append(option)
                _.each(result, function(item) {
                    option = $('<option/>')
                    option.attr('value', item.id)
                    option.text(item.name)
                    $('#standard_id').append(option)
                });
            })
    };
}

$('select[name="program_id"]').on('change', function(e){
    get_program_intake();
})
$('select[name="academic_year"]').on('change', function(e){
    get_program_intake();
})

$(document).on('change', '#school', function(event){
    var school = $(event.target).val();
    var value = parseInt(school)
    $('#program_id').html('');
    $.ajax({
        url : "/school/program",
        data: {
            'school_id': value
        },
        type: 'POST',
    })
    .then(function(result){
        result = JSON.parse(result);
        if (result.length) {
            var option = $('<option/>')
            option.attr('value', "")
            option.text("Program")
            $('#program_id').append(option)
            _.each(result, function(item) {
                option = $('<option/>')
                option.attr('value', item.id)
                option.text(item.name)
                $('#program_id').append(option)
            });
        }
    })
});

    if ($('div.homepage').length) {
        $.ajax({
            url : "/sidebar",
            type: 'GET',
        }).then(function(result) {
            setTimeout(function () {
                $('div#wrap').prepend(result);
                $('div#wrap').css({'min-height': '690px'});
                $('div.menu_sidebar').css({'margin-left': '400px', 'top': '65px'})
            }, 1000);
        });
    }

    $(".add_new_row").click(function (){
        var $new_row = $('.add_new_line').clone(true);
        $new_row.removeClass('d-none');
        $new_row.removeClass('add_new_line');
        $new_row.insertBefore($('.add_new_line'));
        _.each($new_row.find('td'), function(val) {
            if ($(val).children().data('required') == 'True') {
                $(val).children().attr('required', 'required');
            }
        });
    });
    $(document).on('click', '.remove_line', function() {
        $(this).parent().parent().remove();
    });

    $(document).on('click', '.application_submit', function(event){
        var rows = $('.course_registration > tbody > tr:not(.d-none)');
        var cost_data = [];
        _.each(rows, function(row) {
            let course_id = $(row).find('select[name="course_id"]').val();
            let course_code = $(row).find('input[name="course_code"]').val();
            cost_data.push({
                'course_id': course_id,
                'course_code': course_code,
            });
        });
        $('textarea[name="cost_data"]').val(JSON.stringify(cost_data));
        if ($('.error:not(.d-none)').length == 0) {
            $('.form_submit').click();
        }
    }); 

    $(document).on('change', '#course_id', function(event){
        var course = $(event.target).val();
        var value = parseInt(course)
        var current_row = $(event.target).closest('tr');
        $.ajax({
            url : "/subject/registration",
            data: {
                'course_id': value
            },
            type: 'POST',
        })
        .then(function(result){
            result = JSON.parse(result);
            if (result.name !== undefined) {
                current_row.find('input[name="course_code"]').val(result.name);
            }
        })
    }); 

    $(document).on('change', '#student_id', function(event){
        var course = $(event.target).val();
        var value = parseInt(course)
        $.ajax({
            url : "/student",
            data: {
                'student_id': value
            },
            type: 'POST',
        }).then(function(result){
            result = JSON.parse(result);
            if (result.name !== undefined) {
                $('input[name="pid"]').val(result.name);
            }
        })
    }); 

    if ($('#student_user').length) {
        var student_val = $('.existing_student_name').find('option:selected').val();
        student_value_change(student_val);
    };
    
    if ($('.existing_student_name').find('option:selected').val()){
        var student_val = $('.existing_student_name').find('option:selected').val();
        student_value_change(student_val);
    }

    function student_value_change(existing) {
        var value = parseInt(existing)
        var form_mode = document.getElementById('form_mode');
        base_url = "/existing/student/";
        if (form_mode) {
            if (form_mode.value === "edit_mode") {
                base_url = "/admission/existing/student/";
            }
        }
        $.ajax({
            url : base_url + value,
            type: 'POST',
        })
        .then(function(result){
            result = JSON.parse(result);
            $('#student_first_name').val(result.name);
            $('#student_middle_name').val(result.middle);
            $('#student_last_name').val(result.last);
            $('#student_email').val(result.email);
            $('#school').val(result.school_id);
            $('#academic_year').val(result.year);
            $('#academic_year').change();
            setTimeout(function () {
                $('#program_id').val(result.program_id);
                $('#standard_id').val(result.standard_id);
            }, 1000);
            $('#student_phone').val(result.phone);
            $('select[name="student_marital_status"]').val(result.maritual_status);
            $('#name_persented_on_certificate').val(result.name_presented);
            $('#nric').val(result.nric);
            $('#student_street').val(result.street);
            $('select[name="country_id"]').val(result.country_id);
            $('select[name="country_id"]').change();
            $('#city_name').val(result.city);
            $('#state_id').val(result.state_id);
            $('#student_gender').val(result.gender);
            $('#student_zip_code').val(result.zip);
            $('#age').val(result.age);
            $('#date_of_birth').val(result.date_of_birth);
            $('#student_email').val(result.email);
            $('#type').val(result.type);
            $('#type').change();
            $('#transfer_student').val(result.transfer_student);
            $('#student_pass_registry').val(result.student_pass_registry);
            $('#student_pass_status').val(result.student_pass_status);
            _.each(result.parent_id, function (value){
                var $new_row = get_parent_row();
                $new_row.find('input[data-name="name"]').val(value.name);
                $new_row.find('input[data-name="phone"]').val(value.phone);
                $new_row.find('input[data-name="email"]').val(value.email);
                $new_row.find('input[data-name="city"]').val(value.city);
                $new_row.find('input[data-name="address"]').val(value.address);
                $new_row.find('input[data-name="zip"]').val(value.zip);
                $new_row.attr('data-id', value.id);
                $new_row.find('select[data-name="parent_title"]').val(value.title);
                $new_row.find('select[data-name="language"]').val(value.lang);
                $new_row.find('select[data-name="parent_relation"]').val(value.relation_id);
                $new_row.find('select[data-name="country_id"]').val(value.country_id);
                $new_row.find('select[data-name="country_id"]').change();
            });
            _.each(result.reference_id, function (value){
                var $new_row = get_reference_row();
                $new_row.find('input[data-name="first_name"]').val(value.name);
                $new_row.find('input[data-name="middle_name"]').val(value.middle);
                $new_row.find('input[data-name="surname"]').val(value.last);
                $new_row.attr('data-id', value.id);
                $new_row.find('input[data-name="designation"]').val(value.designation);
                $new_row.find('input[data-name="email"]').val(value.email);
                $new_row.find('input[data-name="phone"]').val(value.phone);
                $new_row.find('select[data-name="ref_gender"]').val(value.ref_gender);
            });
            _.each(result.previous_school_id, function (value){
                var $new_row = get_previous_row();
                $new_row.attr('data-id', value.id);
                $new_row.find('input[data-name="name"]').val(value.name);
                $new_row.find('input[data-name="admission_date"]').val(value.admission_date);
                $new_row.find('select[data-name="course"]').val(value.course_id); 
                $new_row.find('input[data-name="registration_no"]').val(value.registration_no);
                $new_row.find('input[data-name="exit_date"]').val(value.exit_date);
            });
            _.each(result.family_id, function (value){
                var $new_row = get_family_row();
                $new_row.find('select[data-name="related_student"]').val(value.rel_name);
                $new_row.find('input[data-name="r_name"]').val(value.relative_name);
                $new_row.find('select[data-name="existing_student"]').val(value.existing_student);
                $new_row.find('select[data-name="family_relation"]').val(value.relation);
                $new_row.find('input[data-name="email"]').val(value.email);
                $new_row.attr('data-id', value.id);
                $new_row.find('input[data-name="phone"]').val(value.phone);
            });
        })
    };

    function get_family_row() {
        var $new_row = $('.extra_family_row').clone(true);
        $new_row.removeClass('d-none');
        $new_row.removeClass('extra_family_row');
        $new_row.addClass('parent_row_family');
        $new_row.insertBefore($('.extra_family_row'));
        _.each($new_row.find('td'), function(val) {
            if ($(val).children().data('required') == 'True') {
                $(val).children().attr('required', 'required');
            }
        });
        return $new_row;
    }

    function get_previous_row() {
        var $new_row = $('.extra_school_row').clone(true);
        $new_row.removeClass('d-none');
        $new_row.removeClass('extra_school_row');
        $new_row.addClass('parent_row_school');
        $new_row.insertBefore($('.extra_school_row'));
        _.each($new_row.find('td'), function(val) {
            if ($(val).children().data('required') == 'True') {
                $(val).children().attr('required', 'required');
            }
        });
        return $new_row;
    }

    function get_reference_row() {
        var $new_row = $('.extra_ref_row').clone(true);
        $new_row.removeClass('d-none');
        $new_row.removeClass('extra_ref_row');
        $new_row.addClass('parent_row_ref');
        $new_row.insertBefore($('.extra_ref_row'));
        _.each($new_row.find('td'), function(val) {
            if ($(val).children().data('required') == 'True') {
                $(val).children().attr('required', 'required');
            }
        });
        return $new_row;
    }

    function get_parent_row() {
        var $new_row = $('.extra_parent_row').clone(true);
        $new_row.removeClass('d-none');
        $new_row.removeClass('extra_parent_row');
        $new_row.addClass('parent_row');
        $new_row.insertBefore($('.extra_parent_row'));
        _.each($new_row.find('td'), function(val) {
            if ($(val).children().data('required') == 'True') {
                $(val).children().attr('required', 'required');
            }
        });
        return $new_row;
    };

    $(document).on('change', '.existing_student_name', function(event){
        var existing = $(event.target).val();
        student_value_change(existing); 
    });
    $(document).on('click', '#modal_survey_submit', function(event) {
        $('input.survey_form_submit').prop('checked', true);
        $("button[value='finish']:not('.o_survey_navigation_submit')").click();
    });
    $(document).on('click', '#std_modal_submit', function(event) {
        $("#assignment_modal").modal("hide");
        $("#additional_modal").modal("hide");
        $("#thanks_modal ").modal("show");
    }); 
    $(document).on('click', '#back_button', function(event) {
        $("#student_assignment_submit ").click();
    });
    $(document).on('click', '#back_button2', function(event) {
        $("#additional_exam_submit ").click();
    });

    $('#student_first_name,#student_middle_name,#student_last_name').change(function () {
        let firstName = $('#student_first_name').val();
        let middleName = $('#student_middle_name').val();
        let lastName = $('#student_last_name').val();
        $("#name_persented_on_certificate").val(firstName + ' ' + middleName + ' ' + lastName);
    });

    $('#start_date').change(function () {
      if($('#end_date').val() != '')
      {
        setup();
      }
    });
    $('#end_date').change(function () {
      if($('#start_date').val() != '')
      {
        setup();
      }
    });
    const setup = () => {
        let firstDate = $('#start_date').val();
        let secondDate = $('#end_date').val();
        const findTheDifferenceBetweenTwoDates = (firstDate, secondDate) => {
           firstDate = new Date(firstDate);
           secondDate = new Date(secondDate);      
           let timeDifference = (secondDate.getTime() - firstDate.getTime() + 1);
           let millisecondsInADay = (1000 * 3600 * 24);      
           let differenceOfDays = Math.ceil(timeDifference / millisecondsInADay);      
           return differenceOfDays;      
        }
        let result = findTheDifferenceBetweenTwoDates(firstDate, secondDate);
        $("#duration").val(result);
    }
    var student = eval($('.student_data').text())
    var $input = $('#student_name');
    

    // $input.select2({
    //     placeholder: "Type to search your name",
    //     theme:"bootstrap",
    // });

    $input.on('change', function() {
        var text = $("#student_name option:selected").text();
        var val = $input.val();
        if (student !== undefined) {
            var filter_student = student.filter(k => k.id == val);
            $('#class_teacher').val('');
            $('#student_class').val('');
            $('input[name="student_id"]').val('');
            if (filter_student.length) {
                $('#class_teacher').val(filter_student[0].teacher_id);
                $('#student_class').val(filter_student[0].class_id);
                $('input[name="student_id"]').val(filter_student[0].id);
            }
        }
    });

    $('#leave_request_modal').on('hidden.bs.modal', function (e) {
        $('#type_of_leave').val(null);
        $('#start_date').val(null);
        $('#end_date').val(null);
        $('#duration').val(0);
        $('#reason_for_leave').val(null);
        $('#student_name').val(null).trigger('change');
        $("#leave_request_modal label.error").hide();
    });
    
    $("#addstudentfamily").click(function (){
        var $new_row = $('.extra_student_family_row').clone(true);
        $new_row.removeClass('d-none');
        $new_row.removeClass('extra_student_family_row');
        $new_row.addClass('parent_row_ref');
        $new_row.insertBefore($('.extra_student_family_row'));
        _.each($new_row.find('td'), function(val) {
            if ($(val).children().data('required') == 'True') {
                $(val).children().attr('required', 'required');
            }
        });
    });

    $("#addparent").click(function (){
        var $new_row = $('.extra_parent_row').clone(true);
        $new_row.removeClass('d-none');
        $new_row.removeClass('extra_parent_row');
        $new_row.addClass('parent_row_ref');
        $new_row.insertBefore($('.extra_parent_row'));
        _.each($new_row.find('td'), function(val) {
            if ($(val).children().data('required') == 'True') {
                $(val).children().attr('required', 'required');
            }
        });
    });

    $("#addmore").click(function (){
        get_parent_row();
    });

    $("#addref").click(function (){
        get_reference_row();
    });

    $("#addschool").click(function (){
        get_previous_row();
    });

    $("#addfamily").click(function (){
        get_family_row();
    });

    $(document).on('click', '.remove_line', function() {
        $(this).parent().parent().remove();
    });
    
    $('.school_admission_register').each(function() {
        this.reset();
    });


    set_disable();

    // student_transcript
    $("#input-academic-year-id").change(function(){
        const termGroup = $("#input-term-ids-group");
        termGroup.html("");
        $.ajax({
                url : "/student/transcript/get_term",
                data: {
                    'academic_year': parseInt($(this).val()),
                },
                type: 'GET',
                }).then(function(result){
                    result = JSON.parse(result);
                    _.each(result, function(item) {
                        let checkBox = "<div class='d-flex align-items-center'><input type='checkbox' id='term-id-"+item.id+"' name='term_ids' value='"+item.id+"'/><label for='term-id-"+item.id+"' class='ml-1 mb-0 font-weight-normal' style='font-size:0.75rem'>"+item.name+"</div>";
                        termGroup.append(checkBox);
                    });
                })
    })

    if($("#input-student-id").val()){
        $("#input-student-id").val("");
    }

    $("#input-student-id").change(function(){
        const programSelect = $("#input-program-id");
        programSelect.html("<option selected disabled value=''></option>");
        programSelect.select2('val','');
        $.ajax({
                url : "/student/transcript/get_program",
                data: {
                    'student_id': parseInt($(this).val()),
                },
                type: 'GET',
                }).then(function(result){
                    result = JSON.parse(result);
                    _.each(result, function(item) {
                        programSelect.append("<option value='"+item.id+"'>"+item.name+"</option>");
                    });
                })

        const intakeSelect = $("#input-intake-id");
        intakeSelect.html("<option selected disabled value=''></option>");
        intakeSelect.select2('val','');
        $.ajax({
                url : "/student/transcript/get_intake",
                data: {
                    'student_id': parseInt($(this).val()),
                    'program_id': parseInt($("#input-program-id").val()),
                },
                type: 'GET',
                }).then(function(result){
                    result = JSON.parse(result);
                    _.each(result, function(item) {
                        intakeSelect.append("<option value='"+item.id+"'>"+item.name+"</option>");
                    });
                })
        
    })

    $("#input-program-id").change(function(){
        const intakeSelect = $("#input-intake-id");
        intakeSelect.html("<option selected disabled value=''></option>");
        intakeSelect.select2('val','');
        $.ajax({
                url : "/student/transcript/get_intake",
                data: {
                    'student_id': parseInt($("#input-student-id").val()),
                    'program_id': parseInt($(this).val()),
                },
                type: 'GET',
                }).then(function(result){
                    result = JSON.parse(result);
                    _.each(result, function(item) {
                        intakeSelect.append("<option value='"+item.id+"'>"+item.name+"</option>");
                    });
                })
        
    })

    function showAcademicSelection(){
        if($("#input-printall").is(":checked")){
            $("#academic-year-row").addClass("d-none");
            $("#term-row").addClass("d-none");
        }else{
            $("#academic-year-row").removeClass("d-none");
            $("#term-row").removeClass("d-none");
        }
    }

    $("#input-printall").change(function(){
        showAcademicSelection();
    })
    
    showAcademicSelection();
});

// function get_intake(school_id=parseInt($('select[name="school_id"]').val()), program_id = parseInt($('select[name="program_id"]').val()), academic_year = parseInt($('select[name="academic_year"]').val()), student_term = parseInt($('select[name="student_term"]').val())){

//     $('#standard_id').html('');
//     var option = $('<option/>');
//     option.attr('value',);
//     option.text('Intake');
//     $('#standard_id').append(option);
//     if (school_id && program_id && academic_year && student_term) {
//         $.ajax({
//             url : "/school/intake",
//             data: {
//                 'school_id': parseInt(school_id),
//                 'program_id': parseInt(program_id),
//                 'academic_year':parseInt(academic_year),
//                 'student_term':parseInt(student_term),
//             },
//             type: 'POST',
//             }).then(function(result){
//                 result = JSON.parse(result);
//                 $('#standard_id').append(option)
//                 _.each(result, function(item) {
//                     option = $('<option/>')
//                     option.attr('value', item.id)
//                     option.text(item.name)
//                     $('#standard_id').append(option)
//                 });
//             })
//     };
// }

// $('select[name="school_id"]').on('change', function(e){
//     $('#school').change();
// })
// $('select[name="program_id"]').on('change', function(e){
//     get_intake();
// })
// $('select[name="student_term"]').on('change', function(e){
//     get_intake();
// })

$('.attendance-row').on('click', function(e){
    window.location.href = '/student/attendance/' + this.getAttribute('data-id');
})

$('.academictracking-row').on('click', function(e){
    window.location.href = '/student/academic/tracking/' + this.getAttribute('data-id');
})

$('.checkbox-no-action').on('click', function(e){
    e.preventDefault();
})

$('.admission-row').on('click', function(e){
    window.location.href = '/student/admission/create/' + this.getAttribute('data-id');
})
$('.readmission-row').on('click', function(e){
    window.location.href = '/student/readmission/create/' + this.getAttribute('data-id');
})

function set_disable(){
    if ($('form').hasClass('input-readonly')){
        $(":disabled").addClass("stay-disabled")
        $('.input-readonly button:not(#admission-form-enable-edit)').prop('disabled', true)
        $('.input-readonly input').prop('disabled', true)
        $('.input-readonly select').prop('disabled', true)
    }
}

function set_enable(){
    $("form button").each(function(){
        if ($(this).hasClass('stay-disabled')){
            $(this).prop('disabled', true)
        }else{
            $(this).prop('disabled', false)
        }
    });
    $("form input").each(function(){
        if ($(this).hasClass('stay-disabled')){
            $(this).prop('disabled', true)
        }else{
            $(this).prop('disabled', false)
        }
    });
    $("form select").each(function(){
        if ($(this).hasClass('stay-disabled')){
            $(this).prop('disabled', true)
        }else{
            $(this).prop('disabled', false)
        }
    });
}

$('#admission-form-enable-edit').on('click', function(e){
    if ($('form').hasClass('hidden-button')){
        $('.hidden-button button#admission-form-enable-edit').prop('hidden', false);
    }
    $('#modal_form_save_as_draft').removeClass('d-none');
    $('#modal_form_submit').removeClass('d-none');
    e.stopPropagation();
    set_enable();
    $(this).remove();
})
    
// $('.admission-row').on('click', function(e){
//     window.location.href = '/student/admission/create/' + this.getAttribute('data-id');
// })

// $('#btn-validate-attendance').on('click', function(e){
//     $.ajax({
//         url : "/attendance/" + this.getAttribute('data-id'),
//         type: 'POST',
//     })
//     .then(function(result){
//         window.location.href = 'attendance';
//     })
// })


// $("#input-term-ids").change(function(){
//     let input = $(this)
//     let values = $(this).val()
//     $(".badge-term").remove();
//     values.forEach(function(item){
//         let termSelector = ".term-option[value=" + item + "]"
//         let termOption = $(termSelector).text()
//         let span = "<span class='badge badge-pill badge-light badge-term' data-value='" + item + "'>" + termOption + "</span>";
//         // let span = "<span class='badge badge-pill badge-light badge-term' data-value='" + item + "'>" + termOption + "<a class='ml-1 term-delete' href='#' data-value='" + item + "'>x</a></span>"
//         input.before(span);
//     })
// })

// $("#input-academic-year-id").change(function(){
//     const termSelect = $('#input-term-ids');
//     termSelect.html('<option selected disabled value=''>Choose Option</option>');
//     $(".badge-term").remove();
//     $.ajax({
//             url : "/student/transcript/get_term",
//             data: {
//                 'academic_year': parseInt($(this).val()),
//             },
//             type: 'GET',
//             }).then(function(result){
//                 result = JSON.parse(result);
//                 console.log(result);
//                 _.each(result, function(item) {
//                     let option = "<option value="+item.id+" class='term-option'>"+item.name+"</option>";
//                     termSelect.append(option);
//                 });
//             })
// })

// $("#input-term-ids").change(function(){
//     let input = $(this)
//     let values = $(this).val()
//     $(".badge-term").remove();
//     values.forEach(function(item){
//         let termSelector = ".term-option[value=" + item + "]"
//         let termOption = $(termSelector).text()
//         let span = "<span class='badge badge-pill badge-light badge-term' data-value='" + item + "'>" + termOption + "</span>";
//         // let span = "<span class='badge badge-pill badge-light badge-term' data-value='" + item + "'>" + termOption + "<a class='ml-1 term-delete' href='#' data-value='" + item + "'>x</a></span>"
//         input.before(span);
//     })
// })

// $(".term-delete").click(function(){
//     console.log('kkkkkkkkkkkkkkkk');
//     let optionSelector = ".term-option[value="+$(this).data('value')+"]";
//     console.log(optionSelector);
//     $(optionSelector).removeAttr("selected");
// })