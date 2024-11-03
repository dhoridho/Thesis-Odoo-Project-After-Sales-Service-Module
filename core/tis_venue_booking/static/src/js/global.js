(function ($) {
    'use strict';
    /*==================================================================
        [ Daterangepicker ]*/
    try {
        $('.js-datepicker').daterangepicker({
            "singleDatePicker": true,
            "showDropdowns": true,
            "autoUpdateInput": false,

            locale: {
                format: 'DD/MM/YYYY HH:mm',
                use24hours: true,
            },
        });
    
        var myCalendar = $('.js-datepicker');
        var isClick = 0;
    
        $(window).on('click',function(){
            isClick = 0;
        });
    
        $(myCalendar).on('apply.daterangepicker',function(ev, picker){
            isClick = 0;
            $(this).val(picker.startDate.format('DD/MM/YYYY HH:mm'));
    
        });
    
        $('.js-btn-calendar').on('click',function(e){
            e.stopPropagation();
    
            if(isClick === 1) isClick = 0;
            else if(isClick === 0) isClick = 1;
    
            if (isClick === 1) {
                myCalendar.focus();
            }
        });
    
        $(myCalendar).on('click',function(e){
            e.stopPropagation();
            isClick = 1;
        });
    
        $('.daterangepicker').on('click',function(e){
            e.stopPropagation();
        });
    
    
    } catch(er) {console.log(er);}
    /*[ Select 2 Config ]
        ===========================================================*/
    
    try {
        var selectSimple = $('.js-select-simple');
    
        selectSimple.each(function () {
            var that = $(this);
            var selectBox = that.find('select');
            var selectDropdown = that.find('.select-dropdown');
            selectBox.select2({
                dropdownParent: selectDropdown
            });
        });
    
    } catch (err) {
        console.log(err);
    }

     try {
        $("#amenities").select2({
        placeholder: "Select Amenities."
        });

    } catch (err) {
        console.log(err);
    }

     try {
        $("#venue").select2({
        placeholder: "Select a Venue.."
        });

    } catch (err) {
        console.log(err);
    }
      try {
       $('#datetimepicker1').datetimepicker({format: 'DD/MM/yyyy HH:mm'});

    } catch (err) {
        console.log(err);
    }

  $(document).ready(function () {
    $(".others_div").hide();
    $("#search_venue").click(function () {
        $(".venue").show();
        $(".others_div").hide();
    });
    $("#search_others").click(function () {
        $(".venue").hide();
        $(".others_div").show();
    });
});

 $(document).ready(function () {
    $(".hour_price").hide();
    $("#type_day").click(function () {
        $(".day_price").show();
        $(".hour_price").hide();
    });
    $("#type_hour").click(function () {
        $(".day_price").hide();
        $(".hour_price").show();
    });
});




})(jQuery);
$( document ).ready(function () {
    $('#date_booking_from, #date_booking_to').datetimepicker({
        format: 'MM/DD/YYYY HH:mm:ss',

    });
});
