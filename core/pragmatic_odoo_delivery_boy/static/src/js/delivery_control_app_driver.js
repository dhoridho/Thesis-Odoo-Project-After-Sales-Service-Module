odoo.define("pragmatic_odoo_delivery_boy.delivery_control_app_driver", function(require){
	"use strict";

    var rpc = require('web.rpc');

	$(document).ready(function(){
		var set_filters_arr = new Array();
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

	    $('#selectBox').change(function(event){
            var selectBox = document.getElementById("selectBox")
            var order_number = document.getElementById("order_number").value
            var selectedValue = selectBox.options[selectBox.selectedIndex].value;
            var value = {
            'selectedValue': selectedValue,
            'order_number': order_number
            }
            $.ajax({
            url : '/select/payment/status',
            data : value
            })
	    });


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
                            navigator.geolocation.getCurrentPosition(function(position) {

                            $("#driver_latitude").val(position.coords.latitude)
                            $("#driver_longitude").val(position.coords.longitude)
						})
						calculateAndDisplayRoute(directionsService, directionsDisplay);
//						console.log("Map Reloaded");
//}
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
	    $('.joblist_cancel_order_driver').on('click', function(){
	    	var order_id = $(this).data('order_id');
	    	var data = {
	    		'order_id' : order_id
	    	}
	    	$.ajax({
	    		url: "/driver/cancel/order",
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

	    $('.joblist_proceed_to_checkout').on('click', function(){
	    	var order_id = $(this).data('order_id');
	    	var data = {
	    		'order_id' : order_id,
	    	}
	    	$.ajax({
	    		url: "/proceed/checkout",
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

        $('.joblist_delivered_order').on('click', function (){
	     	var elem = document.getElementById("delivered_button");
	    	elem.style.display = "none";
	    	var order_id = $(this).data('order_id');
	    	var data = {
	    		'order_id' : order_id,
	    	}
	    	$.ajax({
	    		url: "/delivered/order",
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

        	$('.confirm_driver').click(function(e){
//        	    console.log("In confirm_driver")
                var picking_order = $("#picking_order_number").val()
                var driver_message = $("#message_driver").val()

    			var value = {
					"picking_order" : picking_order,
					"driver_message" : driver_message,
				}
//				console.log("value console driver message:: ",value)

				$.ajax({
					url : "/driver/issue/message",
					data : value,
					cache : "false",
					success : function(res) {
						window.location = '/page/job/list/driver'
					},
					Error : function(x, e) {
						alert("Some error");
					}
				});
		});

        $('.joblist_pay_now').on('click', function (){
//                    console.log("\n\n")
                    var elem = document.getElementById("pay_now_button");
	     	        var picking_order_number = document.getElementById("picking_order_number").value
                    elem.value = "PAID";
            var payment_status = elem.value
            var value = {
            'payment': 'Paid',
            'picking_order_number': picking_order_number
            }
             $.ajax({
            url : '/paid/status',
            data : value
            })
            setTimeout(function() {location.reload()}, 3000);

            });

		$('.create_backorder').on('click', function (){
//                    console.log("\n\n")
                    var elem = document.getElementById("create_back_order");
	     	        var picking_order_number = document.getElementById("picking_order_number").value;
            // var payment_status = elem.value
            var value = {
            // 'payment': 'Paid',
            'picking_order_number': picking_order_number
            }
             $.ajax({
            url : '/page/create_backorder',
            data : value
            })
            setTimeout(function() {location.reload()}, 1000);
			// window.location.reload();

            });

        $('.joblist_message').on('click', function(){
//              console.log('In joblist_message')

        })

//        $('.joblist_call_driver').on('click', function(){
//              var  driver_mobile_number = document.getElementById("driver_mobile").value
//                window.location.href = 'tel://' + driver_mobile_number;
//
//        })

       $('.joblist_call_customer').on('click', function(){
              var cust_mobile_number = document.getElementById("customer_phone").value
               window.location.href = 'tel://' + cust_mobile_number;

        })

       //Code added by Pooja -->

       $('.joblist_accept_order').on('click',function()
       {
            var order_number = document.getElementById("order_number").value
            var value = {
					"delivery_order_status" : "accept",
					"order_number" : order_number
			}
            $.ajax({
                    url : '/order/driver_accept_reject_status',
                    data : value,
                    success: function(res) {
                        var vals = $.parseJSON(res)
                        if (vals['status'] == true)
                        {
                            window.location.reload();
                        }
                    }
            });
       });

	   //Picked to wizard -->

	   $('.joblist_picked_order_to_wizard').on('click',function()
       {
           	var order_number = document.getElementById("order_number").value
		   	var picking_order = $("#picking_order_number").val()
        	var value = {
					"delivery_order_status" : "picked",
					"order_number" : order_number,
					"picking_order" : picking_order,
			}
            $.ajax({
                    url : '/order/driver_accept_reject_status_in_picked',
                    data : value,
                    success: function(res) {
                        var vals = $.parseJSON(res)
                    }
            });
       });

	//Picked after wizard -->

       $('.joblist_picked_order_after_wizard').on('click',function()
       {
           	var order_number = document.getElementById("order_number").value
		   	var picking_order = $("#picking_order_number").val()
		   	var quantity_done = document.getElementById("quantity_done").value
		   	var quantity_demand = document.querySelector('#quantity_demand').innerHTML
		   	var location_id = document.querySelector('#stocklocation_id').getAttribute("data-id")
		   	var product_id = document.querySelector('#product_id').getAttribute("data-id")
		   	var qty_done_num = parseFloat(quantity_done)
		   	var qty_demand_num = parseFloat(quantity_demand)
		   	rpc.query({
                model: 'picking.order',
                method: 'get_stock_count',
                args: [product_id, location_id],
            }).then(function(data) {
                if (data <= 0) {
                    alert("The product has no quantity available");
                }
            })
		   	if (quantity_done == 0) {
                alert("Done quantity must have Value");
            }
            if (qty_done_num > qty_demand_num) {
                alert("Done quantity is higher than demand quantity");
            }
            else {
                var value = {
                        "delivery_order_status" : "picked",
                        "order_number" : order_number,
                        "picking_order" : picking_order,
                        "qty_done" : quantity_done,
                }
                $.ajax({
                        url : '/order/driver_accept_reject_status',
                        data : value,
                        success: function(res) {
                            var vals = $.parseJSON(res)
                            if (vals['status'] == true)
                            {
                                window.location.reload();
                            }
                        }
                });
            }
       });


       $('.joblist_deny_order').on('click',function()
       {
            var order_number = document.getElementById("order_number").value
            var reject_reason = $("#reject_reason").val()
            var value = {
					"delivery_order_status" : "reject",
					"order_number" : order_number,
					"reject_reason": reject_reason
			}

            $.ajax({
                    url : '/order/driver_accept_reject_status',
                    data : value,
                    success: function(res) {
                        var vals = $.parseJSON(res)
                        if (vals['status'] == false)
                        {
                            window.history.back();
                            window.location.reload();
                        }
                    }
            });
       });


       $('#driver_status').on('click',function(){
            var delivery_boy = $('#delivery_boy').val();
            var delivery_boy_status=$(".driver_status span").text()
//            alert($(".driver_status span").text());
            var value = {
					"delivery_boy_status" : delivery_boy_status,
					"delivery_boy" : delivery_boy
			}
            $.ajax({
                    url : '/change_delivery_boy_status',
                    data : value,
                    success: function(res) {
                        var vals = $.parseJSON(res)
                        if (vals['status_changed'] == false)
                        {
                           alert("We are unable to process your request. Please contact the System Administrator.")
                        }
                        else
                        {
                            if(vals['driver_status'] == 'Not Available')
                            {
                                $('#delivery_boy_change_text').text('Not Available');
//                                $("#delivery_boy_status").val(vals['driver_status'])
                            }
                            else if(vals['driver_status'] == 'Available')
                            {
                                $('#delivery_boy_change_text').text('Available');
//                                $("#delivery_boy_status").val(vals['driver_status']);
                            }

                        }
                    },
                    Error : function(x, e) {
						alert("Something went wrong!!!!!!!!");
					}
            });
       })

              $('select[class=driver_status]').change(function(event){
        if(event){
//                console.log("In Js")
//                console.log("event: ",event)
//                console.log("event.currentTarget: ",event.currentTarget)
//                console.log("event.currentTarget.attributes: ",event.currentTarget.attributes)
//                console.log("event.currentTarget.attributes.my_id: ",event.currentTarget.attributes.my_id)
//                console.log("event.currentTarget.attributes.my_id.value: ",event.currentTarget.attributes.my_id.value)
//                console.log("this: ",$(this))
//                console.log("this: ",$(this))
               var driver_status = $(this).find(":selected").val()
               var id1 = $(this).find(":selected")
//                console.log("id1: ",id1)
//                console.log("driver_status",driver_status)
                var id = event.currentTarget.attributes.my_id.value
//                console.log("Id: ",id)
                var partner_id = document.getElementById('partner_id')
                var warehouse_id = document.getElementById('warehouse_id-'+id)
//                console.log('warehouse_id: ',warehouse_id)

                var driver_status = $(this).find(":selected").val()


                var value = {
            'partner_id': id,
            'driver_status': driver_status,
            'warehouse_id': warehouse_id
            }
             $.ajax({
            url : '/driver/status',
            data : value
            });


//                var selectedValue = selectBox.options[selectBox.selectedIndex].value;
//                console.log("selectedValue: ",selectedValue)
        }

       });

//       document.getElementById("download_receipt").onclick = function myFunction(){

    $('#download_receipt').on('click',function(){
           var order_id = document.getElementById("order_id").value
           $.ajax({
                    url : '/customer/receipt',
                    data : {'order_id': order_id},

            });


    })

	});
});