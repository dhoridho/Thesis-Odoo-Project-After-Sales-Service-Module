odoo.define('tis_venue_booking.ajaxCall', function (require) {
"use strict";
 $( document ).ready(function(event) {
    $('#type_days').click(function(event){
    var budget = $('#budget').val();
    var venue_capacity = $('#capacity').val();
    var location = $('#loc_id').val();
    var date_from = $('#start').val();
    var date_to = $('#end').val();
    var select_venue = $('#select_venues').val();
    var type_of_venue = $('#search_type').val();
    var venue_amenity = [];
    var booking_type = $('input[type="radio"]:checked').val();
    $('input[type="checkbox"]:checked').each(function(){
        venue_amenity.push(this.value);
    });
    var v= JSON.stringify(venue_amenity);
    $.ajax({
    url: '/filter/budget',
    type: 'GET',
    data: {budget:budget,
    capacity:venue_capacity,
    venue_amenity:v,
    location:location,
    date_from:date_from,
    date_to:date_to,
    select_venue:select_venue,
    type_of_venue:type_of_venue,
    booking_type:booking_type
    },
    headers: {
    'X-CSRFToken': token
    },
    success: function(response){
        event.preventDefault();
        if(!response){
            $('.card').empty();
            $('.show').empty();
        }
        else{
        $('.static_card').empty();
        var data = JSON.parse(response);
        var c="";
        $.each(data,function(key,value){


        c +="<div class='col-md-4 mb-5'>";
        c +="<div class='card mb-4 h-100'>";
        c +="<a href='/venue/"+value.id+"'>";
        c +="<img style='width: 100%;' src='data:image/png;base64,"+value.image+"'/>";
        c +="</a>";
        c +="<div class='rec_content text-center mt-3 mb-5'>";
        c +="<h2>"+value.venue+"</h2>";
        c +="<p>"+"<span>"+value.charge_per_day+" "+value.currency_id+" / Day</span>";
        c +="<span> - "+value.charge_per_hour+" "+value.currency_id+" / Hour</span></p>";
        c +="<p>Capacity:"+value.capacity+" Units</p>";
        c +="<p>Seating:"+value.seating+" Units</p>";
        c +="<a href='/venue/"+value.id+"/booking'>"
        c +="<button>Request Booking</button>";
        c +="</a>";
        c +="</div>";
        c +="</div>";
        c +="</div>";
        $('.show').append(c);
        });
        $('.show').html(c);
      }
    },
    error:function(error){
       console.log(error);
    },
    });
    });
    $('#type_hours').click(function(event){
    var budget = $('#budget').val();
    var venue_capacity = $('#capacity').val();
    var location = $('#loc_id').val();
    var date_from = $('#start').val();
    var date_to = $('#end').val();
    var select_venue = $('#select_venues').val();
    var type_of_venue = $('#search_type').val();
    var venue_amenity = [];
    var booking_type = $('input[type="radio"]:checked').val();
    $('input[type="checkbox"]:checked').each(function(){
        venue_amenity.push(this.value);
    });
    var v= JSON.stringify(venue_amenity);
    $.ajax({
    url: '/filter/budget',
    type: 'GET',
    data: {budget:budget,
    capacity:venue_capacity,
    venue_amenity:v,
    location:location,
    date_from:date_from,
    date_to:date_to,
    select_venue:select_venue,
    type_of_venue:type_of_venue,
    booking_type:booking_type
    },
    headers: {
    'X-CSRFToken': token
    },
    success: function(response){
        event.preventDefault();
        if(!response){
            $('.card').empty();
            $('.show').empty();
        }
        else{
        $('.static_card').empty();
        var data = JSON.parse(response);
        var c="";
        $.each(data,function(key,value){


        c +="<div class='col-md-4 mb-5'>";
        c +="<div class='card mb-4 h-100'>";
        c +="<a href='/venue/"+value.id+"'>";
        c +="<img style='width: 100%;' src='data:image/png;base64,"+value.image+"'/>";
        c +="</a>";
        c +="<div class='rec_content text-center mt-3 mb-5'>";
        c +="<h2>"+value.venue+"</h2>";
        c +="<p>"+"<span>"+value.charge_per_day+" "+value.currency_id+" / Day</span>";
        c +="<span> - "+value.charge_per_hour+" "+value.currency_id+" / Hour</span></p>";
        c +="<p>Capacity:"+value.capacity+" Units</p>";
        c +="<p>Seating:"+value.seating+" Units</p>";
        c +="<a href='/venue/"+value.id+"/booking'>"
        c +="<button>Request Booking</button>";
        c +="</a>";
        c +="</div>";
        c +="</div>";
        c +="</div>";
        $('.show').append(c);
        });
        $('.show').html(c);
      }
    },
    error:function(error){
       console.log(error);
    },
    });
    });
    $('input[type="checkbox"]').click(function(event){
    var budget = $('#budget').val();
    var venue_capacity = $('#capacity').val();
    var location = $('#loc_id').val();
    var date_from = $('#start').val();
    var date_to = $('#end').val();
    var select_venue = $('#select_venues').val();
    var type_of_venue = $('#search_type').val();
    var venue_amenity = [];
    var booking_type = $('input[type="radio"]:checked').val();
    $('input[type="checkbox"]:checked').each(function(){
        venue_amenity.push(this.value);
    });
    var v= JSON.stringify(venue_amenity);
    $.ajax({
    url: '/filter/budget',
    type: 'GET',
    data: {budget:budget,
    capacity:venue_capacity,
    venue_amenity:v,
    location:location,
    date_from:date_from,
    date_to:date_to,
    select_venue:select_venue,
    type_of_venue:type_of_venue,
    booking_type:booking_type
    },
    headers: {
    'X-CSRFToken': token
    },
    success: function(response){
        event.preventDefault();
        if(!response){
            $('.card').empty();
            $('.show').empty();
        }
        else{
        $('.static_card').empty();
        var data = JSON.parse(response);
        var c="";
        $.each(data,function(key,value){


        c +="<div class='col-md-4 mb-5'>";
        c +="<div class='card mb-4 h-100'>";
        c +="<a href='/venue/"+value.id+"'>";
        c +="<img style='width: 100%;' src='data:image/png;base64,"+value.image+"'/>";
        c +="</a>";
        c +="<div class='rec_content text-center mt-3 mb-5'>";
        c +="<h2>"+value.venue+"</h2>";
        c +="<p>"+"<span>"+value.charge_per_day+" "+value.currency_id+" / Day</span>";
        c +="<span> - "+value.charge_per_hour+" "+value.currency_id+" / Hour</span></p>";
        c +="<p>Capacity:"+value.capacity+" Units</p>";
        c +="<p>Seating:"+value.seating+" Units</p>";
        c +="<a href='/venue/"+value.id+"/booking'>"
        c +="<button>Request Booking</button>";
        c +="</a>";
        c +="</div>";
        c +="</div>";
        c +="</div>";
        $('.show').append(c);
        });
        $('.show').html(c);
      }
    },
    error:function(error){
       console.log(error);
    },
    });
    });

    $('#budget').change(function(event){
    var budget = $('#budget').val();
    var venue_capacity = $('#capacity').val();
     var location = $('#loc_id').val();
    var date_from = $('#start').val();
    var date_to = $('#end').val();
    var select_venue = $('#select_venues').val();
    var type_of_venue = $('#search_type').val();
    var booking_type = $('input[type="radio"]:checked').val();
    $.ajax({
    url: '/filter/budget',
    type: 'GET',
    data: {budget:budget,
    capacity:venue_capacity,
    location:location,
    date_from:date_from,
    date_to:date_to,
    select_venue:select_venue,
    type_of_venue:type_of_venue,
    booking_type:booking_type
    },
    headers: {
    'X-CSRFToken': token
    },
    success: function(response){
        event.preventDefault();
        if(!response){
            $('.card').empty();
            $('.show').empty();
        }
        else{
        $('.static_card').empty();
        var data = JSON.parse(response);
        var c="";
        $.each(data,function(key,value){
        c +="<div class='col-md-4 mb-5'>";
        c +="<div class='card mb-4 h-100'>";
        c +="<a href='/venue/"+value.id+"'>";
        c +="<img style='width: 100%;' src='data:image/png;base64,"+value.image+"'/>";
        c +="</a>";
        c +="<div class='rec_content text-center mt-3 mb-5'>";
        c +="<h2>"+value.venue+"</h2>";
        c +="<p>"+"<span>"+value.charge_per_day+" "+value.currency_id+" / Day</span>";
        c +="<span> - "+value.charge_per_hour+" "+value.currency_id+" / Hour</span></p>";
        c +="<p>Capacity:"+value.capacity+" Units</p>";
        c +="<p>Seating:"+value.seating+" Units</p>";
        c +="<a href='/venue/"+value.id+"/booking'>"
        c +="<button>Request Booking</button>";
        c +="</a>";
        c +="</div>";
        c +="</div>";
        c +="</div>";
        $('.show').append(c);
        });
        $('.show').html(c);
      }

    },
    error:function(error){
       console.log(error);
    }
    });

   });

   $('#capacity').change(function(event){
    var budget = $('#budget').val();
    var venue_capacity = $('#capacity').val();
     var location = $('#loc_id').val();
    var date_from = $('#start').val();
    var date_to = $('#end').val();
    var select_venue = $('#select_venues').val();
    var type_of_venue = $('#search_type').val();
    var booking_type = $('input[type="radio"]:checked').val();
    $.ajax({
    url: '/filter/budget',
    type: 'GET',
    data: {budget:budget,
    capacity:venue_capacity,
    location:location,
    date_from:date_from,
    date_to:date_to,
    select_venue:select_venue,
    type_of_venue:type_of_venue,
    booking_type:booking_type
    },
    headers: {
    'X-CSRFToken': token
    },
    success: function(response){
        event.preventDefault();
        if(!response){
            $('.card').empty();
            $('.show').empty();
        }
        else{
        $('.static_card').empty();
        var data = JSON.parse(response);
        var c="";
        $.each(data,function(key,value){
        c +="<div class='col-md-4 mb-5'>";
        c +="<div class='card mb-4 h-100'>";
        c +="<a href='/venue/"+value.id+"'>";
        c +="<img style='width: 100%;' src='data:image/png;base64,"+value.image+"'/>";
        c +="</a>";
        c +="<div class='rec_content text-center mt-3 mb-5'>";
        c +="<h2>"+value.venue+"</h2>";
        c +="<p>"+"<span>"+value.charge_per_day+" "+value.currency_id+" / Day</span>";
        c +="<span> - "+value.charge_per_hour+" "+value.currency_id+" / Hour</span></p>";
        c +="<p>Capacity:"+value.capacity+" Units</p>";
        c +="<p>Seating:"+value.seating+" Units</p>";
        c +="<a href='/venue/"+value.id+"/booking'>"
        c +="<button>Request Booking</button>";
        c +="</a>";
        c +="</div>";
        c +="</div>";
        c +="</div>";
        $('.show').append(c);
        });
        $('.show').html(c);
      }

    },
    error:function(error){
       console.log(error);
    }
    });

   });
 });
});