odoo.define('equip3_hr_dashboard_extend.hr_announcement_popup', function(require) {
	"use strict";
	var core = require('web.core');
	var ajax = require('web.ajax');
	$(document).ready(function() {
		$(document).on("click", ".open-announce", function(ev) {
//			  var announces_id = $('.annoucement_info').data('id');
			var announces_id = $(this).data('id');

			$.ajax({
				url: '/get-popup-announcement',
				method: "GET",
				dataType: 'json',
				data: {announce_id: announces_id},
				success: function(data) {
					$(".modal-header .announce_name").text(data['announcement_name']);
					$(".modal-header .announce_start_date").text(data['date_start']);
					$(".modal-header .announce_end_date").text(data['date_end']);
					$(".modal-body #content").empty();
					$(".modal-body #content").append(data['announcement']);
				},
				error: function(data) {
					console.error("ERROR ", data);
				},
			});
		});
	});
});
