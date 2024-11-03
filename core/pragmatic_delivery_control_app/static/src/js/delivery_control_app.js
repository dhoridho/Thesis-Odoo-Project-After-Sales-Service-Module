odoo.define("pragmatic_delivery_control_app.delivery_control_app", function(require){
	"use strict";

	$(document).ready(function(){

		var set_filters_arr = new Array();
		var map;
        var service;
        var infowindow;
		var ajax_call_all_time = function(){
//			console.log("AJAX Call......")
			$.ajax({
    		type: "GET",
				url : location.pathname,
//				data : value,
				cache : "false",
				success : function(res) {
					$('#manage_sale_order_delivery').html($(res).find("#manage_sale_order_delivery").html())
					var flag = false;
					for(var i=0; i < set_filters_arr.length; i++){
						if(set_filters_arr[i].value != '' && set_filters_arr[i].value !='select'){
							flag = true;
						}
					}
					if (flag){
						data_filter($(set_filters_arr));
					}
				},Error : function(x, e) {
					alert("Some error");
				}
			});
		}

		//Refresh delivery control panel
		var delivery_control_panel_loading = setInterval(ajax_call_all_time,20000);
		if (!location.pathname.includes('/page/manage/delivery')) {
			clearInterval(delivery_control_panel_loading);
//			console.log("STOP");
		}

		//Filter button click handle for thead disable and enable
//		console.log("filterable  ",$('.filterable .btn-filter'))
		$('.filterable .btn-filter').on('click', function(){
	        var $panel = $(this).parents('.filterable'),
	        $filters = $panel.find('.filters .form-control'),
	        $tbody = $panel.find('.table tbody');
	        if ($filters.prop('disabled') == true) {
	            $filters.prop('disabled', false);
	            $filters.first().focus();
	        } else {
	            $filters.val('').prop('disabled', true);
	            $('.filterable .filters select').each(function(){
	            	$(this).children().first().attr('selected','selected');
	            });
//	            Reset all the filters and remove no-result row if present.
	            $('.no-result').remove();
	            $("#display_sale_orders > tbody > tr").show();
	        }
	    });


	    $('.filterable .filters input').keyup(function(e){
	        /* Ignore tab key */
	        var code = e.keyCode || e.which;
	        if (code == '9') return;
	        var flag=false;
	        if(this.value != ''){
		        if(set_filters_arr.length > 0){
					for(var i=0; i<set_filters_arr.length; i++){
						if(set_filters_arr[i].name == this.name){
							flag = false;
							break;
						}else{
							flag=true;
						}
					}
				}else{
					flag=true;
				}
		        if(flag){
		        	set_filters_arr.push(this);
		        }
		        /* Useful DOM data and selectors */
		        data_filter($(this));
	        }else{
	        	var $panel = $(this).parents('.filterable');
	    		var $table = $panel.find('#display_sale_orders');
	            var $rows = $table.find('tbody tr');
	    		$rows.show();
	    		for(var i=0; i<set_filters_arr.length; i++){
	    			if(set_filters_arr[i].name == this.name){
	    				set_filters_arr.splice(i,1);
	    				break;
	    			}
	    		}
	        }
//	        var $input = $(this),
//	        inputContent = $input.val().toLowerCase(),
//	        $panel = $input.parents('.filterable'),
//	        column = $panel.find('.filters th').index($input.parents('th')),
//	        $table = $panel.find('#display_sale_orders'),
//	        $rows = $table.find('tbody tr');
//	        /* Dirtiest filter function ever */
//	        var $filteredRows = $rows.filter(function(){
//	            var value = $(this).find('td').eq(column).text().toLowerCase();
//	            //Remove hidden class of order complete record
//	            if(value.indexOf(inputContent) != -1 && column === 6){
//	            	$rows.removeClass('hidden');
//	            }
//	            return value.indexOf(inputContent) === -1;
//	        });
//	        /* Clean previous no-result if exist */
//	        $table.find('tbody .no-result').remove();
//	        /* Show all rows, hide filtered ones (never do that outside of a demo ! xD) */
//	        $rows.show();
//	        $filteredRows.hide();
//	        /* Prepend no-result row if all rows are filtered */
//	        if ($filteredRows.length === $rows.length) {
//	            $table.find('tbody').prepend($('<tr class="no-result text-center"><td colspan="'+ $table.find('.filters th').length +'">No result found</td></tr>'));
//	        }
	    });

	    //Reset other filters value on click of select or on focus of input
	    $('.filterable .filters select').off().on('click', function(){
	    	var $sel_filters = $('.filterable .filters select');
	    	var $txt_filters = $('.filterable .filters input');
	    	for(var i=0; i<$sel_filters.length; i++){
				if($sel_filters[i].name != this.name){
					$($sel_filters[i]).children().first().attr('selected','selected');
				}
			}
	    	for(var i=0; i<$txt_filters.length; i++){
				if($txt_filters[i].name != this.name){
					$txt_filters[i].value = '';
				}
			}

	    });

	    $('.filterable .filters input').focus(function(){
	    	var $sel_filters = $('.filterable .filters select');
	    	var $txt_filters = $('.filterable .filters input');
	    	for(var i=0; i<$sel_filters.length; i++){
				if($sel_filters[i].name != this.name){
					$($sel_filters[i]).children().first().attr('selected','selected');
				}
			}
	    	for(var i=0; i<$txt_filters.length; i++){
				if($txt_filters[i].name != this.name){
					$txt_filters[i].value = '';
				}
			}
	    });

	    $('.filterable .filters select').change(function(e){
	    	if($(this).val() != 'select'){
//	    		console.log("On change calling === ",$(this).val())
	    		var flag = false;
	    		if(set_filters_arr.length > 0){
	    			for(var i=0; i<set_filters_arr.length; i++){
	    				if(set_filters_arr[i].name == this.name){
	    					flag = false;
	    					break;
	    				}else{
	    					flag = true;
	    				}
	    			}
	    		}else{
	    			flag = true;
	    		}
	    		if(flag){
	    			set_filters_arr.push(this);
	    		}

	    		data_filter($(this));
	    	}else{
	    		var $panel = $(this).parents('.filterable');
	    		var $table = $panel.find('#display_sale_orders');
	            var $rows = $table.find('tbody tr');
	    		$rows.show();
	    		for(var i=0; i<set_filters_arr.length; i++){
	    			if(set_filters_arr[i].name == this.name){
	    				set_filters_arr.splice(i,1);
	    				break;
	    			}
	    		}
	    	}
	    });

	    function data_filter($element){
//	    	console.log("Calling ...",$element)
//	    	var $input = $(this),
	    	var inputContent = $element.val().toLowerCase();
	    	var $panel = $element.parents('.filterable');
	        var column = $panel.find('.filters th').index($element.parents('th'));
//	        console.log("column=========",column,inputContent);
	        var $table = $panel.find('#display_sale_orders');
	        var $rows = $table.find('tbody tr');
//	        console.log("$rows=========",$rows);
	        /* Dirtiest filter function ever */
	        var $filteredRows = $rows.filter(function(){
	            var value = $(this).find('td').eq(column).text().toLowerCase();
	            //Remove hidden class of order complete record
//	            if(value.indexOf(inputContent) != -1 && column === 6){
//	            	$rows.removeClass('hidden');
//	            }
	            //For Payment status column check for exact match
//	            if(column === 5){
//	            	return value.toString().trim() != inputContent.toString().trim();
//	            }else{
	            return value.indexOf(inputContent) === -1;
//	            }
	        });
//	        console.log("$filteredRows=========",$filteredRows);
	        /* Clean previous no-result if exist */
	        $table.find('tbody .no-result').remove();
	        /* Show all rows, hide filtered ones (never do that outside of a demo ! xD) */
	        $rows.show();
	        $filteredRows.hide();
	        /* Prepend no-result row if all rows are filtered */
	        if ($filteredRows.length === $rows.length) {
	            $table.find('tbody').prepend($('<tr class="no-result text-center"><td colspan="'+ $table.find('.filters th').length +'">No result found</td></tr>'));
	        }
	    }

	    //Delivery panel button click event handlers
		var driver_name_tr;
		$('#manage_sale_order_delivery').on('click', 'a.assign-driver', function() {
			driver_name_tr=$(this).parent().parent()[0].id;
		});

		//Load driver on modal
	    $('#select_driver').on('show.bs.modal', function(e) {
	    	$('#loading-indicator').show();
	        var $modal = $(this);
	        var warehouse_id = e.relatedTarget.id;
	        var order_id = $(e.relatedTarget).attr('order_id');
			var value = {
				"warehouse_id" : warehouse_id,
			}
			$.ajax({
				url : "/get-driver",
				data : value,
				cache : "false",
				success : function(res) {
					var html = '<input type="hidden" name="warehouse_id" value="'+warehouse_id+'"/>'
					var result = $.parseJSON(res);

					$.each(result,function(key,value){
						html +="<input id="+order_id+" type='radio' name='driver_radio' value='"+value['id']+"' data-text='"+value['name']+"'>"+value['name']+"</input><br/>"
					});
					var count = 0;
						$modal.find('.driver-list').html(html);
					$('#loading-indicator').hide();
				},

				Error : function(x, e) {
					alert("Some error");
					$('#loading-indicator').hide();
				}
			});
	    });

		// For Assign drvier
		$('#select_driver .confirm').click(function(e){
			var driver_id = parseInt($('input[name=driver_radio]:checked').val())
			var order_id = parseInt($('input[name=driver_radio]:checked').attr('id'))
			var warehouse_id = parseInt($('input[name=warehouse_id]').val())

			var value = {
					"order_id" : order_id,
					'driver_id' :driver_id,
					'warehouse_id':warehouse_id,
				}
				$.ajax({
					url : "/assign-driver",
					data : value,
					cache : "false",

					success : function(res) {
						var vals = $.parseJSON(res)
						var new_driver_name=$('input[name=driver_radio]:checked').data('text');
						$('#'+driver_name_tr +' > #order_driver_name > span').text(new_driver_name);
						$('#select_driver').modal('hide');
						alert(vals[0]);
//						window.location="/page/manage-sale-order-delivery";
					},

					Error : function(x, e) {
						alert("Some error");
					}
				});

		});

		// Collect Payment
		$('.collect_payment').click(function(e){
			var order_id = $(this).attr('order_id');
			var value = {
				"order_id" : order_id,
			}
			$.ajax({
				url : "/collect-payment",
				data : value,
				cache : "false",

				success : function(res) {
					var vals = $.parseJSON(res);
					window.location.reload();
				},

				Error : function(x, e) {
					alert("Some error");
				}
			});
		});

		// For show issues
		$('#show_issue').on('show.bs.modal', function(e) {
			$('#loading-indicator').show();
		    var $modal = $(this),
		    	order_id = e.relatedTarget.id;
			var value = {
					"order_id" : order_id,
				}
				$.ajax({
					url : "/get-issue",
					data : value,
					cache : "false",
					success : function(res) {
						var $def_obj = $.Deferred();
//						html = ' '
						var result = $.parseJSON(res);
						$("#issue_map").empty();
						$("#longitude").val(result['shipping_longitude']);
						$("#latitude").val(result['shipping_latitude']);
						$("#driver_longitude").val(result['longitude']);
						$("#driver_latitude").val(result['latitude']);
						if(result['issue'])
							$(".modal-header #label").html(result['issue']);
						else
							$(".modal-header #label").empty();
						setTimeout(function() {
							if (!jQuery.isEmptyObject(result)){
								var directionsService = new google.maps.DirectionsService;
								var directionsDisplay = new google.maps.DirectionsRenderer;
							    issue_map = new google.maps.Map(document.getElementById("issue_map"), {
							        zoom: 25,
							        mapTypeId: google.maps.MapTypeId.ROADMAP,
							        center: {lat: result['latitude'], lng: result['longitude']}
							    });
								$def_obj.resolve(issue_map);
							    directionsDisplay.setMap(issue_map);
							    calculateAndDisplayRoute(directionsService, directionsDisplay);
							    function calculateAndDisplayRoute(directionsService, directionsDisplay) {
								    var driver_lat = parseFloat($("#driver_latitude").val());
								    var driver_lng = parseFloat($("#driver_longitude").val());
								    var shipping_lat = parseFloat($("#latitude").val());
								    var shipping_lng = parseFloat($("#longitude").val());
							        directionsService.route({
							       	 origin: {lat:driver_lat, lng: driver_lng},
							       	 destination: {lat: shipping_lat, lng: shipping_lng},
							          travelMode: 'DRIVING'
							        }, function(response, status) {
							          if (status === 'OK') {
							            directionsDisplay.setDirections(response);
							          } else {
							          }
							        });
							      }
							}else{
								$modal.find('.issue-list').html("<p><h1 style='text-align:center'>Order has not an issue at all.<h1></p>");
		//						$('#show_issue').modal('hide');
							}
						}, 1000);

//							$modal.find('.issue-list').html(html);
						$('#loading-indicator').hide();
					},

					Error : function(x, e) {
						alert("Some error");
						$('#loading-indicator').hide();
					}
				});
		});

		//Delivery Boy location update
		var flag = true;
		function initialize() {
			var $def_obj = $.Deferred();
		    var shipping_lat = parseFloat($("#latitude").val());
		    var shipping_lng = parseFloat($("#longitude").val());
		    var map1 = new google.maps.Map(document.getElementById("customer_map"), {
		        zoom: 14,
		        mapTypeId: google.maps.MapTypeId.ROADMAP,
		        center: {lat: shipping_lat, lng: shipping_lng}

		    });
		    directionsDisplay.setMap(map1);
		    calculateAndDisplayRoute(directionsService, directionsDisplay);
		    $def_obj.resolve(map1);
	        return $def_obj;

		}

	    function calculateAndDisplayRoute(directionsService, directionsDisplay) {
		    var driver_lat = parseFloat($("#driver_latitude").val());
		    var driver_lng = parseFloat($("#driver_longitude").val());
		    var shipping_lat = parseFloat($("#latitude").val());
		    var shipping_lng = parseFloat($("#longitude").val());
		    if(!driver_lat && !driver_lng){
		    	driver_lat = shipping_lat;
		    	driver_lng = shipping_lng;
		    }
	        directionsService.route({
	       	 origin: {lat:driver_lat, lng: driver_lng},
	       	 destination: {lat: shipping_lat, lng: shipping_lng},
	          travelMode: 'DRIVING'
	        }, function(response, status) {
	          if (status === 'OK') {
	            directionsDisplay.setDirections(response);
	          } else {
	          }
	        });
	    }
		var ajax_call = function() {
			if (flag==true){
			var driver_id= $("#driver_id").val();
			var order_number = $("#order_number").data('order_id');
			var value = {
					'driver_id' :driver_id,
					'order_number' : order_number,
				}
				$.ajax({
					url : "/get-driver-location",
//					async: false,
					timeout: 4000,
					data : value,
					success : function(res) {
						var vals = $.parseJSON(res)
						if(vals['latitude'] && vals['longitude']){
							$("#driver_latitude").val(vals['latitude']);
							$("#driver_longitude").val(vals['longitude']);
						}
						calculateAndDisplayRoute(directionsService, directionsDisplay);
//						console.log("Map Reloaded");
					},

					Error : function(x, e) {
						alert("Some error");
					}
				});
			};
		};

		if ($("#customer_map")[0]){
			var directionsService = new google.maps.DirectionsService;
		    var directionsDisplay = new google.maps.DirectionsRenderer;
		    $("#customer_map").hover(
					  function() {
						  flag = false;
					  }, function() {
						  flag = true;
					  }
					);
		    setInterval(ajax_call, 5000);
		    initialize();
		}

		if ($("#map")[0]){
		    initMap();
//		    initMap_admin_delivery();
		}

//        function initMap_admin_delivery() {
//        var directionsService = new google.maps.DirectionsService;
//        var directionsRenderer = new google.maps.DirectionsRenderer;
//
//        calculateAndDisplayRoute_H_admin_delivery(directionsService, directionsRenderer);
//      }

//            function calculateAndDisplayRoute_H_admin_delivery(directionsService, directionsRenderer) {
//        let route = JSON.parse(document.getElementById('route_values').value)
//        console.log("route111::::::::",route)
//        var map = new google.maps.Map(document.getElementById('map'), {
//          zoom: 6,
//          center: {lat: route[0][0], lng: route[0][1]}
//        });
//        directionsRenderer.setMap(map);
//        var waypts = [];
//        var checkboxArray = document.getElementById('waypoints');
//
//        for (var i = 1; i < route.length-1; i++)
//        {
//            waypts.push
//            ({
//              location: {lat: route[i][0], lng: route[i][1]},
//              stopover: true,
//            });
//        }
//
//        directionsService.route({
//          origin: {lat: route[0][0], lng: route[0][1]},
//          destination: {lat: route[route.length - 1][0], lng: route[route.length - 1][1] - 0.0001},
//          waypoints: waypts,
//          optimizeWaypoints: true,
//          travelMode: 'DRIVING'
//        }, function(response, status) {
//          if (status === 'OK') {
////          console.log(response)
//            let d = response.routes[0].legs
//            let w = response.routes[0].waypoint_order
//
//            var waypoints_start = []
//
//            var sum = 0
//
//            for (let i = 0; i < response.routes[0].legs.length; i++)
//            {
//                sum+= d[i].distance.value
//            }
//
//            let new_route = []
////            new_route[0] = [0, route[0][0], route[0][1], 'Current Location']
////            console.log(w)
//            for (let j = 0; j < w.length; j++)
//            {
////                console.log(j, w[j])
//                new_route[j+1] = [j+1, route[j+1][0], route[w[j]+1][1], route[w[j]+1][2]]
//            }
//
////            new_route[route.length-1] = [route.length-1, route[route.length-1][0], route[route.length-1][1], 'Destination']
//
////            console.log(new_route)
//            let ww = response.routes[0].waypoint_order
//            let route_a = []
//            route_a[0] = [0, route[0][0], route[0][1],route[0][2]]
//            for (let j = 0; j < ww.length; j++)
//            {
////                console.log(j, w[j])
//                route_a[j+1] = [j+1, route[j+1][0], route[ww[j]+1][1], route[ww[j]+1][2]]
//            }
//
//            route_a[route.length-1] = [route.length-1, route[route.length-1][0], route[route.length-1][1],route[route.length-1][2]]
//
//            let result = route_a.sort()
//            console.log("result:::::",result)
//            let route_order = []
//            for (var i = 0; i < result.length; i++)
//                {
////            route_order[0] += [result[i][2]]
//                route_order += "<b>Order Sequence "+String.fromCharCode(65+i)+": "+ result[i][3] +"</b><br>";
//
//                        console.log("route_order12:::::",route_order)
//
//            }
//                        console.log("route_order:::::",route_order)
//
//            var summaryPanel = document.getElementById("directions-panel_admin");
//            if (summaryPanel)
//            {
//            summaryPanel.innerHTML = route_order
////            for (var j = 0; j < route_order.length; j++)
////            {
////            summaryPanel.innerHTML +=
////                        "<b>Order Sequence "+String.fromCharCode(65+j)+": "+ route_order +"</b><br>";
////                        }
////                summaryPanel.innerHTML = ""; // For each route, display summary information.
////
////                for (var i = 0; i < result.length; i++)
////                {
//////                    if (i==0)
//////                        summaryPanel.innerHTML +=
//////                            "<b>Current Location "+String.fromCharCode(65+i)+": Started</b><br>";
//////                    else if (i== result.length-1)
//////                        summaryPanel.innerHTML +=
//////                            "<b>Destination Location "+String.fromCharCode(65+i)+": Warehouse</b><br>";
//////                    else
////                    summaryPanel.innerHTML +=
////                        "<b>Order Sequence "+String.fromCharCode(65+i)+": "+ result +"</b><br>";
////                }
//            }
//
//            $("#total_distance").val(sum);
//            directionsRenderer.setDirections(response);
//          } else {
//            window.alert('Directions request failed due to ' + status);
//          }
//        });
//      }


//        function initMap_admin_delivery() {
//                let locations = JSON.parse(document.getElementById('route_values').value)
//for (count = 0; count < locations.length; count++) {
//
//         var center = {lat: locations[count][0], lng: locations[count][1]};
//         }
//  var map = new google.maps.Map(document.getElementById('map'), {
//    zoom: 10,
//    center: center
//  });
//  var marker = new google.maps.Marker({
//    position: center,
//    map: map
//  });
//
//        console.log("In map",)
//        var infowindow =  new google.maps.InfoWindow({});
//var marker, count;
//    var summaryPanel = document.getElementById("directions-panel");
//
//for (count = 0; count < locations.length; count++) {
//    marker = new google.maps.Marker({
//      position: new google.maps.LatLng(locations[count][0], locations[count][1]),
//      map: map,
//      title: locations[count][2]
//    });
//
//    if (summaryPanel)
//            {
//                summaryPanel.innerHTML = ""; // For each route, display summary information.
//
////                for (var i = 0; i < result.length; i++)
////                {
//                    if (count==0)
////                        summaryPanel.innerHTML +=
////                            "<b>Current Location "+String.fromCharCode(65+i)+": Started</b><br>";
////                    else if (i== result.length-1)
////                        summaryPanel.innerHTML +=
////                            "<b>Destination Location "+String.fromCharCode(65+i)+": Warehouse</b><br>";
////                    else
//                        summaryPanel.innerHTML +=
//                            "<b>Order Sequence "+String.fromCharCode(65+count)+": "+ locations[count][3] +"</b><br>";
////                }
//            }
//
//google.maps.event.addListener(marker, 'click', (function (marker, count) {
//      return function () {
//        infowindow.setContent(locations[count][2]);
//        infowindow.open(map, marker);
//      }
//    })(marker, count));
//  }
//
//        }
//        var request;
//        console.log("route values: ",route)
////  const sydney = new google.maps.LatLng(-33.867, 151.195);
//    for (let j = 0; j < route.length; j++)
//            {
//                console.log("1111",route[j][0])
//                const new_route = new google.maps.LatLng(route[j][0], route[j][1])
//
////     = new google.maps.LatLng(-33.867, 151.195);
//
//  infowindow = new google.maps.InfoWindow();
//  map = new google.maps.Map(document.getElementById("map"), {
//    center: new_route,
//    zoom: 15
//  });}
//
////  for (var item in route) {
////  console.log("item::::::::",item[][2])
//  const request = {
////    query: "Museum of Contemporary Art Australia",
//    query: "411001",
////    query: route[][2],
//
////    fields: []
//    fields: ["name", "geometry"]
//  };
//  service = new google.maps.places.PlacesService(map);
//  service.findPlaceFromQuery(request, (results, status) => {
//    if (status === google.maps.places.PlacesServiceStatus.OK) {
//
//      for (let i = 0; i < results.length; i++) {
//        console.log("results::::",results[i])
//        createMarker(results[i]);
//      }
//      map.setCenter(results[0].geometry.location);
//    }
//  });
//}
//
//function createMarker(place) {
//  const marker = new google.maps.Marker({
//    map,
//    position: place.geometry.location
//  });
//  google.maps.event.addListener(marker, "click", () => {
//    infowindow.setContent(place.name);
//    infowindow.open(map);
//  });
//}


        function update_driver_location()
        {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(function(position) {
                var pos = {
                    'lat': position.coords.latitude,
                    'lng': position.coords.longitude
                };

                $.ajax({
                        url: "/update-driver-location",
                        async: true,
                        timeout: 4000,
                        data: pos,
                        success: function(res) {
                        let data = JSON.parse(res)
                        $('#route_values').val(JSON.stringify(data['routes']))
                        },
                    });
                });
            }
        }

    function initMap() {
        var directionsService = new google.maps.DirectionsService;
        var directionsRenderer = new google.maps.DirectionsRenderer;

        calculateAndDisplayRoute_H(directionsService, directionsRenderer);
      }

      function calculateAndDisplayRoute_H(directionsService, directionsRenderer) {
        let route = JSON.parse(document.getElementById('route_values').value)
//        console.log("route:::::::::::::::::::::::",route)
        var map = new google.maps.Map(document.getElementById('map'), {
          zoom: 6,
          center: {lat: route[0][0], lng: route[0][1]}
        });
        directionsRenderer.setMap(map);
        var waypts = [];
        var checkboxArray = document.getElementById('waypoints');

        for (var i = 1; i < route.length-1; i++)
        {
            waypts.push
            ({
              location: {lat: route[i][0], lng: route[i][1]},
              stopover: true,
            });
        }

        directionsService.route({
          origin: {lat: route[0][0], lng: route[0][1]},
          destination: {lat: route[route.length - 1][0], lng: route[route.length - 1][1] - 0.0001},
          waypoints: waypts,
          optimizeWaypoints: true,
          travelMode: 'DRIVING'
        }, function(response, status) {
          if (status === 'OK') {
//          console.log(response)
            let d = response.routes[0].legs
            let w = response.routes[0].waypoint_order

            var waypoints_start = []

            var sum = 0

            for (let i = 0; i < response.routes[0].legs.length; i++)
            {
                sum+= d[i].distance.value
            }

            let new_route = []
//                         console.log("route1: ",route)

            new_route[0] = [0, route[0][0], route[0][1], 'Current Location']
//            console.log(w)
            for (let j = 0; j < w.length; j++)
            {
//                console.log(j, w[j])
                new_route[j+1] = [j+1, route[j+1][0], route[w[j]+1][1], route[w[j]+1][2]]
            }
//             console.log("new route2: ",new_route)

            new_route[route.length-1] = [route.length-1, route[route.length-1][0], route[route.length-1][1], 'Destination']

//            console.log("new_route: ",new_route)
            let result = new_route.sort()
//            console.log("result: ",result)
            var summaryPanel = document.getElementById("directions-panel");
            if (summaryPanel)
            {
                summaryPanel.innerHTML = ""; // For each route, display summary information.

                for (var i = 0; i < result.length; i++)
                {
                    if (i==0)
                        summaryPanel.innerHTML +=
                            "<b>Current Location "+String.fromCharCode(65+i)+": Started</b><br>";
                    else if (i== result.length-1)
                        summaryPanel.innerHTML +=
                            "<b>Destination Location "+String.fromCharCode(65+i)+": Warehouse</b><br>";
                    else
                        summaryPanel.innerHTML +=
                            "<b>Order Sequence "+String.fromCharCode(65+i)+": "+ result[i][3] +"</b><br>";
                }
            }

            $("#total_distance").val(sum);
            directionsRenderer.setDirections(response);
          } else {
            window.alert('Directions request failed due to ' + status);
          }
        });
      }

    setInterval(function(){
        if (location.pathname == '/page/route/map')
        {
            update_driver_location()
            setTimeout(function(){
                initMap();
            }, 3000);
        }
        if (location.pathname == '/admin/delivery/routes/details/')
        {
//            console.log("In js admin delivery routes")
            setTimeout(function(){
                initMap_admin_delivery();
            }, 3000);
        }
    }, 17000);



	    $('#start_delivery').click(function(){

	        var pickings = $("#picking_ids").val();

			var value = {
					'pickings' : pickings,
					'total_distance' : $("#total_distance").val(),
				}

	        $.ajax({
					url : "/update_pickings",
					timeout: 4000,
					data : value,
					success : function(res){}
				});

			var value = {
					'start' : 1,
				}

            location.reload()
	        $.ajax({
					url : "/page/job/list/driver",
					timeout: 4000,
					data : value,
					success : function(res){}
				});
        })


		var issue_ajax_call = function() {
			$.ajax({
				url : "/get-issue-notification",
				data : value,
				cache : "false",

				success : function(res) {
					vals = $.parseJSON(res)
					$("#driver_latitude").val(vals['latitude']);
					$("#driver_longitude").val(vals['longitude']);
					calculateAndDisplayRoute(directionsService, directionsDisplay);
				},

				Error : function(x, e) {
					alert("Some error");
				}
			});

		};

		//Order details view events
	    $('#send_message_to_driver').click(function(){
	    	var msg = $('#message_to_driver').val().trim();
	    	var driver = $('#driver_id').val();
	    	if(msg && $('#driver_id').val()){
		    	post_data = {
		    			'title':'SBARRO MESSAGE',
		    			'message': msg,
		    			'driver_user_id':parseInt($('#driver_id').val()),
		    			'sale_order_name': $("[name='order_number']").val(),
		    			'send_to_driver':'True',
		    	}
		    	$.ajax({
		    		url:"/page/send-push-notification",
		    		data:post_data,
		    		success : function(res) {
		    			var res = JSON.parse(res);
		    			if(res.status){
		    				var html = '<tr><td>'+msg+'</td></tr>';
		    				$('#message_to_driver').val('').focus();
//			    				$('#sent-messages').append(html);
		    			}
		    		},
		    		Error : function(x, e) {
		    			alert("Some error");
		    		}
		    	});
	    	}
	    });

	    $('#send_message_to_restaurant').click(function(){

	    	var msg = $('#message_to_driver  ').val().trim();
	    	var order_id = $(this).data('order_id');
	    	if(msg && $(this).data('order_id')){
		    	post_data = {
		    			'title':'SBARRO MESSAGE',
		    			'message': msg,
		    			'order_id' : $(this).data('order_id'),
		    			'sale_order_name': $("[name='order_number']").val(),
		    	}
		    	$.ajax({
		    		url:"/page/send-push-notification-to-restaurant",
		    		data:post_data,
		    		success : function(res) {
		    			var res = JSON.parse(res);
		    				var html = '<tr><td>'+msg+'</td></tr>';
		    				$('#message_to_driver').val('').focus();
		    		},
		    		Error : function(x, e) {
		    			alert("Some error");
		    		}
		    	});
	    	}
	    });

	    //Code added for dyanamically refreshing message box
		var ajax_message_box_refresh_call = function() {
			if(flag==true){
				$("#sent-messages").empty();
				var order_number = $("#order_number").data('order_id');
				if(order_number){
					var data = {
						     'order_id':order_number
						   }
			    	$.ajax({
			    		url:"/page/get-message-details",
//				    		async: false,
			    		timeout: 2000,
			    		data: data,
			    		success : function(res)
			    		{
			    			//parsing code
			    			var res = JSON.parse(res);
			    		    var html = '';
			    		    todays_date_time = new Date();
			    		    todays_date = new Date(todays_date_time.toDateString());
			    		    for (var i=0;i<res.length;i++){
			    		    	msg_date_time = new Date(res[i].create_date);
			    		    	msg_date = new Date(msg_date_time.toDateString());
			    		    	time = moment(msg_date_time).format('hh:mm:ss');
			    		    	if (msg_date.valueOf() == todays_date.valueOf()){
				    		    		html += '<tr>'+
				    		    		'<td><b>'+res[i].partner_id+'</b> : '+res[i].message+'<br/> <span style="color: #aeb0b2; font-size: 08pt">' +time+ '</span> </td>'+
				    		    		'</tr>';
				    		    		$('#sent-messages').html(html).focus();
				    		    	}
				    		    else if (msg_date.valueOf() != todays_date.valueOf())
				    		    {
				    		    	html += '<tr>'+
			    		    		'<td><b>'+res[i].partner_id+'</b> : '+res[i].message+'<br/> <span style="color: #aeb0b2; font-size: 08pt">' +res[i].create_date+ '</span> </td>'+
			    		    		'</tr>';
			    		    		$('#sent-messages').html(html).focus();
				    		    }
			    		    	var rowpos = $('#driver-msg-table tr:last').position();
			    		    	$('#container').scrollTop(rowpos.top);
			    		    }
//			    		    console.log("Message Panel Reloaded");
			    			},
			    		Error : function(x, e) {
			    			alert("Some error");
			    		}
			    	});
				}
			}
	    };
	    if ($("#driver-msg-table")[0]){
		    $("#driver-msg-table").hover(
					  function() {
						  flag = false;
					  }, function() {
						  flag = true;
					  }
					);
		    setInterval(ajax_message_box_refresh_call, 3000);
		}
	    $('.joblist_cancel_order').on('click', function(){
	    	var order_id = $(this).data('order_id');
	    	var data = {
	    		'order_id' : order_id,
	    	}
	    	$.ajax({
	    		url: "/cancel/order",
	    		data: data,
	    		success: function(res) {
	    			var res = JSON.parse(res);
	    			if(res.status){
	    				window.history.back();
	    			}
	    		},
	    		Error : function(x, e) {
	    			alert("Some error");
	    		}
	    	});
	    });

	    $('.joblist_back').on('click', function(){
	    	window.history.back();
	    });
	});

});