odoo.define('tis_venue_booking.checkDate', function (require) {
"use strict";
$( document ).ready(function(event) {
    $('#search_button').click(function(event){
        var from_date = $('#start').val();
        var to_date = $('#end').val();
        if(from_date > to_date){
        alert("Check in date should be anterior to check out date.");
        event.preventDefault();
        event.stopPropagation();
        }
    });
    $('#booking_submit').click(function(event){
        var booking_from_date = $('#start').val();
        var booking_to_date = $('#end').val();
        if(booking_from_date > booking_to_date){
        alert("Start date should be anterior to end date !!.");
        event.preventDefault();
        event.stopPropagation();
        }
    });
});
});