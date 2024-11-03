odoo.define('tis_venue_booking.option_select', function (require) {
"use strict";

$( document ).ready(function() {
    $('#selected_location').change(function(){
        var location = $('#selected_location').val();
        if (location == '-- select an option --'){
        document.getElementById("dynamic_options").style.display = "none";
        document.getElementById("select_venues").style.display = "block";
        document.getElementById("select_venues").style.position = "relative";
        }
        else{
            document.getElementById("dynamic_options").style.display = "block";
        document.getElementById("select_venues").style.display = "none";
        }
        $.ajax({
        url: '/options',
        type: 'POST',
        data:{location:location},
        headers: {
        'X-CSRFToken': token
        },
        success:function(response){
        var data = JSON.parse(response);
//         $('#select_venues').empty();
        var optionHTML = '<option>-- select an option --</option>';
        $.each(data,function(key,value){
        optionHTML += '<option value="'+value.id+'">'+value.name+'</option>';
        $('.dynamic_options').append(optionHTML);
        });
        $('.dynamic_options').html(optionHTML);
        },
        error:function(error){
        console.log(error);
        },
        });
    });


});

});