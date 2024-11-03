 $(document).ready(function(){
   
    $(document).on('click', '#modal_form_submit', function(event) {
        var required = $('input,textarea,select').filter('[required]:visible');
        var allRequired = true;
        required.each(function(){
            if($(this).val() == ''){
                allRequired = false;
            }
        });
        if (allRequired){
            if (!$('#agree_terms_condition').prop('checked')) {
                $("#ok_modal").modal("show");
            } else {
                $('#form_submit').click();
            }
        }
        else {
            $('#form_submit').click();
        }
    });

    $(document).on('click', '.register_privy', function(event) {
        var name = $('input[name="pic_name"]').val();
        var email = $('input[name="pic_email"]').val();
        var phone = $('input[name="pic_phone"]').val();
        var street = $('input[name="pic_street"]').val();
        var city = $('input[name="pic_city"]').val();
        var zipcode = $('input[name="pic_zipcode"]').val();
        var country_id = $('select[name="pic_country_id"]').val();
        var state_id = $('select[name="pic_state_id"]').val();
        var identity_number = $('input[name="pic_identity_number"]').val();
        $.ajax({
            url : "/register/privy",
            data: {
                'name': name,
                'phone': phone,
                'email': email,
                'street': street,
                'city': city,
                'zip': zipcode,
                'identity_number': identity_number,
                'country_id': country_id != '' ? parseInt(country_id) : false,
                'state_id': state_id != '' ? parseInt(state_id) : false,
            },
            type: 'POST',
        }).then(function(result){
            window.location.href = '/customer/signature/2'
        });
    });

    $(document).on('click', '.privy_account', function(event) {
        $.ajax({
            url : "/privy/status",
            type: 'POST',
        }).then(function(result){
            window.location.href = '/customer/signature/6'
        });
    });

    $(document).on('click', '#identity_preview', function(event) {
        Webcam.set({
            width: 320,
            height: 240,
            image_format: 'png',
            jpeg_quality: 90
        });
        $('#identity_preview').addClass('d-none');
        $('#webcam').removeClass('d-none');
        $('#btnCaptureIdentity').removeClass('d-none');
        Webcam.attach('#webcam');
    });

    $(document).on('click', '#btnCaptureIdentity', function(event) {
        Webcam.snap(function (data_uri) {
            $("#identity_image").val(data_uri);
            $("#identity_preview_image")[0].src = data_uri;
            $('#identity_preview_image').removeClass('d-none');
            $("#btnCaptureIdentity").addClass("d-none");
            $('#webcam').addClass('d-none');
        });
        Webcam.reset();
    });

    $(document).on('click', '#selfie_preview', function(event) {
        Webcam.set({
            width: 320,
            height: 240,
            image_format: 'png',
            jpeg_quality: 90
        });
        $('#selfie_preview').addClass('d-none');
        $('#webcam').removeClass('d-none');
        $('#btnCaptureSelfie').removeClass('d-none');
        Webcam.attach('#webcam');
    });

    $(document).on('click', '#btnCaptureSelfie', function(event) {
        Webcam.snap(function (data_uri) {
            $("#selfie_image").val(data_uri);
            $("#selfie_preview_image")[0].src = data_uri;
            $('#selfie_preview_image').removeClass('d-none');
            $("#btnCaptureSelfie").addClass("d-none");
            $('#webcam').addClass('d-none');
        });
        Webcam.reset();
    });

    $(document).on('click', '#last_page', function(event) {
        var required = $('input,textarea,select').filter('[required]:visible');
        var allRequired = true;
        $('.identity_no_warning').addClass('d-none');
        var identity_no = $('input[name="identity_number"]');
        if ($(identity_no).val().length < 16) {
            $('.identity_no_warning').removeClass('d-none');
        }
        required.each(function(){
            if($(this).val() == ''){
                allRequired = false;
            }
        });
        if ($('span.warning:not(.d-none)').length) {
            $('#warning_modal').modal('show');
        }
        else {
            if (allRequired){
                if (allRequired) {
                    $("#submit_modal").modal("show");
                }
            }
            else {
                $("#form_submit").click();
            }
        }
    });

    $(document).on('input', '#identity_no', function(event) {
        if ($(event.target).val().length !== 16) {
            $('.identity_no_warning').removeClass('d-none');
        }
        else {
            $('.identity_no_warning').addClass('d-none');
        }
    });

    $(document).on('input', '#full_name', function(event) {
        if ($(event.target).val().length < 3) {
            $('.full_name_warning').removeClass('d-none');
        }
        else {
            $('.full_name_warning').addClass('d-none');
        }
    });

    $(document).on('input', '#phone_no', function(event) {
        if ($(event.target).val().length < 5) {
            $('.phone_no_warning').removeClass('d-none');
        }
        else {
            $('.phone_no_warning').addClass('d-none');
        }
    });

    $(document).on('input', '#d_o_b', function(event) {
        var current_date = new Date();
        var input_date = new Date($(event.target).val());
        if (moment(input_date).format('YYYY-MM-DD') >= moment(current_date).format('YYYY-MM-DD') ||
            moment().diff(moment(input_date, 'YYYY-MM-DD'), 'years') < 17) {
            $('.birth_date_warning').removeClass('d-none');
        }
        else {
            $('.birth_date_warning').addClass('d-none');
        }
    });

    $(document).on('input', '#email_id', function(event) {
        var user_input = $(event.target).val();
        var pattern = /^\b[A-Z0-9._%-]+@[A-Z0-9.-]+\.[A-Z]{2,4}\b$/i;
        if(!pattern.test(user_input)) {
            $('.email_warning').removeClass('d-none');
        }
        else {
            $('.email_warning').addClass('d-none');
        }
    });

    $(document).on('click', '#modal_done', function(event) {
        $("#form_submit").click();
    }); 
});
