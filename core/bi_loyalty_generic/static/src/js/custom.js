odoo.define('bi_loyalty_generic.custom', function(require) {
	"use strict";
	var core = require('web.core');
	var ajax = require('web.ajax');
	$( document ).ready(function() {
		$(document).on("click", ".open-redeem", function (ev) {
			var order_id = $('.coupon_info').data('id');
			
			$.ajax({
				url: '/get-loyalty-points',
				method: "GET",
				dataType: 'json',
				data: {order_id :order_id },
				success: function (data) {
					$(".modal-body .redeem_name").text(data['partner'] );
					$(".modal-body .redeem_points").text(data['points']);
					$(".modal-body .redeem_total").text(data['loyalty_amount']);
					$(".modal-body .redeem_value").text(data['redeem_value']);
					$(".modal-body .order_id").text(order_id);
					$(".modal-body .amount_total").text(data['amount_total']);
					$(".modal-body .order_redeem_points").text(data['order_redeem_points']);
				},
				error: function (data) {
					console.error("ERROR ", data);
				},
			});	
		});
		$(document).on("click", ".redeem_ok", function (ev) {
			var order_redeem_points = parseFloat($(".modal-body .order_redeem_points").text());
			var amount_total = parseFloat($(".modal-body .amount_total").text());
			var points = parseFloat($(".modal-body .redeem_points").text());
			var entered_points = parseFloat($(".modal-body #entered_points").val());
			var order_id = $(".modal-body .order_id").text();
			var redeem_value = parseFloat($(".modal-body .redeem_value").text());
			var redeem_amount = redeem_value * entered_points;
			if(order_redeem_points > 0)
			{
				alert("you can not redeem more than one time")
				$("#redeem_modal").modal("hide");
			}
			else if(!entered_points){
				alert("Please enter valid points amount")
			}
			else if(entered_points < 0){
				alert("Please enter valid points amount")
			}
			else if(entered_points > points){
				alert("Please enter valid points amount")
			}
			else if(redeem_amount > amount_total){
				alert("You can not redeem more than total amount")
			}
			else{
				$.ajax({
					url: '/redeem-loyalty-points',
					method: "GET",
					dataType: 'json',
					data: {order_id :order_id, entered_points : entered_points , redeem_value : redeem_value},
					success: function (data) {
						if(data){
							window.location.href="/shop/cart";
						}
					},
					error: function (data) {
						console.error("ERROR ", data);
					},
				});	
				$("#redeem_modal").modal("hide");
			}
		});	
	});
});
