odoo.define("pragmatic_delivery_acknowledgement.broadcast_order", function(require){
	"use strict";
	$(document).ready(function(){
	    $('.broadcast_accept_order').on('click',function(){
            var order_number = document.getElementById("order_number").value
            var value = {
					"delivery_order_status" : "accept",
					"order_number" : order_number
			}
            $.ajax({
                url : '/broadcast/accept_broadcast_order',
                data : value,
                success: function(res) {
                    var vals = $.parseJSON(res)
                    if (vals['status'] == true)
                    {vals
                        window.location.reload();
                    }
                }
            });
        });
	});
});
