odoo.define('aspl_vehicle_rental.main', function (require) {
    "use strict";
    var ajax = require('web.ajax');

    $(document).ready(function (){
        if($('.rate_option').val() == 'per_day'){
            $('.total_km').hide();
            $('.total_days').show();
        }
        if($('.rate_option').val() == 'per_km'){
            $('.total_km').show();
            $('.total_days').hide();
        }
        var select_value=$('.rate_option').val();
        if(!select_value){
            $('.none_of_this').show();
            $('.total_days').hide();
            $('.total_km').hide();
            $('.rate_total_km').hide();
            $('.js_check_product').addClass('btn-disable');
        }
        else{
            $('.none_of_this').hide();
            $('.calculate_total').show();
            $('.js_check_product').removeClass('btn-disable');

        }
        var to_date = $('input[name=date_to]').val()
        var from_date = $('input[name=date_from]').val()
        var days_between_date = Math.floor(( Date.parse(to_date) - Date.parse(from_date) ) / 86400000);
        $('input[name=enter_days]').value = days_between_date

        $('.total_days').hide();
        var error = $('#error').val();
        if(error=="True"){
           $("#myModal").modal();
        }

        $('#date_from').datepicker({
            dateFormat: "dd-mm-yy"
        });

        $('#date_to').datepicker({
            dateFormat: "dd-mm-yy"
        });

        $('#class_type').on('click',function(){
            ajax.jsonRpc('/get_vehicle_type', 'call', {
                'type_id':$(this).val(),
            }).then(function (result) {
                if (result){
                    var html = '';
                    for(var i=0;i<result.length;i++){
                        html += "<option>"+result[i]+"</option>";
                    }
                    $('#vehicle_type_data').html(html);
                }
            });
        });

        $('.rate_option').on('change',function(){
            console.log("Call onchange")
            var select_value = $('.rate_option').val();
            console.log(select_value.length)
            var qty = $(this).parent().parent().find('.qty').val()
            var km= $(this).parent().parent().find('.enter_km').val()
            var day = days_between_date;
            $('input[name=enter_days]').html(day);
            var total_day = $(this).parent().find('.total_day')
            ajax.jsonRpc('/get_rate_details', 'call', {
                'vehicle_id':$(document).find('.vehicle_id').val(),
                'units':$('.rate_option').val(),
            }).then(function (vehicle_details) {
                var rate = parseInt(vehicle_details['rate'])
                var total_day = parseInt(vehicle_details['total_days'])
                var from_date = (vehicle_details['from_date'])
                var to_date = (vehicle_details['to_date'])
                if (select_value == 'per_day'){
                    $('.js_check_product').removeClass('btn-disable');
                    var html = '';
                    var day = '';
                    $('.total_km').hide();
                    $('.enter_km').val('');
                    $('.rate_total_km').hide();
                    $('.total_day').show();
                    $('.total_days').show();
                    var a = $(document).find('.total_day').text()
                    html += "<td>"+rate+"</td>";
                    day += total_day
                    from_date +="<td>"+from_date+"</td>"
                    to_date +="<td>"+to_date+"</td>"
                    $('.rate_value').html(html);
                    $('.total_day').html(day)
                    $('.rate_value').addClass('rate_cls');
                    $('.total_day').addClass('day_cls');
                    $('.date_from').html(from_date)
                    $('.date_to').html(to_date)
                    $('.calculate_total').show();
                    calculate_total(rate*total_day);
                    $('.none_of_this').hide();
                }
                else if (select_value == 'per_km'){
                    $('.js_check_product').removeClass('btn-disable');
                    var html = '';
                    $('.total_km').show();
                    $('.enter_km').val(0);
                    $('.rate_total_km').show();
                    $('.total_day').show();
                    $('.total_days').show();
                    html += "<td>"+rate+"</td>";
                    day += "<td>"+total_day+"</td>"
                    from_date +="<td>"+from_date+"</td>"
                    to_date +="<td>"+to_date+"</td>"
                    $('.rate_value').html(html);
                    $('.total_day').html(day)
                    $('.rate_value').addClass('rate_cls');
                    $('.total_day').addClass('day_cls');
                    $('.date_from').html(from_date)
                    $('.date_to').html(to_date)
                    calculate_total(rate*total_day);
                    $('.total_day').hide();
                    $('.total_days').hide();
                    $('.total_dwebsite_rental_order[ays').hide();
                    $('.rate_value').html(html);
                    $('.rate_value').addClass('rate_cls');
                    $('.total_km').addClass('day_km');
                    $('.calculate_total').show();
                    $('.calculate_total').html(rate * km)
                    $('.none_of_this').hide();
                }
                else if (!select_value){
                    $('.none_of_this').show();
                    $('.total_days').hide();
                    $('.total_km').hide();
                    $('.rate_total_km').hide();
                    $('.total_day').hide();
                    $('.calculate_total').hide();
                    $('.js_check_product').addClass('btn-disable');
                }
            });
        });

        $('.quantity').on('change',function () {
            var numberPattern = /\d+/g;
            var rate_value=parseInt($('.rate_cls').html().match( numberPattern ));
            var km=parseInt($('.enter_km').val());
            var total_day=parseInt($('.day_cls').html().match( numberPattern ));
            if ($(this).parent().parent().parent().find('.rate_option').val() == 'per_km'){
                calculate_total(rate_value*$(this).val()*km);
            }
            else{
                calculate_total(rate_value*total_day*$(this).val())
            }
        });

        $('.enter_km').on('change',function () {
            var km= $(this).parent().parent().find('.enter_km').val()
            ajax.jsonRpc('/get_rate_details', 'call', {
                'vehicle_id':$(document).find('.vehicle_id').val(),
                'units':$('.rate_option').val(),
            }).then(function (vehicle_details) {
                var rate = parseInt(vehicle_details['rate'])
                $('.calculate_total').html(rate * km)
            });
        });

        $('.js_delete_product').on('click', function(e){
            if(e.currentTarget.getAttribute('data_id')){
                ajax.jsonRpc("/vehical_ordel_line/remove", 'call', {
                    'id': e.currentTarget.getAttribute('data_id')
                }).then(function(e) {
                    var currentObj = $('.js_delete_product');
                    currentObj[0].closest('.vehical_order_line').remove();
                });
            }

        });
    });

    function calculate_total(calculated_value) {
        $('.calculate_total').html("<td>"+calculated_value+"</td>");
    }

});
