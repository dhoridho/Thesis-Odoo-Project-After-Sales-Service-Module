$(document).ready(function () {
	setTimeout(function () {
		console.log("Light Slider");
		$('.image-gallery-cls').lightSlider({
			gallery: true,
			item: 1,
			thumbItem: 4,
			slideMargin: 0,
			speed: 500,
			auto: true,
			loop: true,
			onSliderLoad: function () {
				$('.image-gallery-cls').removeClass('cS-hidden');
			}

		});
	}, 1000);


	$("#room_form").submit(function (e) {

		var checkboxlist = []
		$(this).find('.roomspercoloumn').each(function (i, el) {
			if ($(this).find('select#noofroomselect :selected') && $(this).find('#noofroomselect').val() != '0') {
				checkboxlist.push($(this).find('#noofroomselect').val());
			}
		});
		if (checkboxlist.length < 1) {
			alert("Please select any one room type");
			e.preventDefault();
		}
	});
});

function onchange_tax(val) {
	tot = parseFloat($("#total").val()) + parseFloat($("#tax").val())
	$("#grand_total").val(tot)
}
