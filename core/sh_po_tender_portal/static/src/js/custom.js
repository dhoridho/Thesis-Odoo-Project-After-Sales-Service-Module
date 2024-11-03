$(document).ready(function (e) {
    $(".btn_add_bid").click(function (e) {
    	var $el = $(e.target).parents("tr").find("#tender_id").attr("value");
        var tender_id = parseInt($el);
        console.log(tender_id);
        $.ajax({
            url: "/rfq/create",
            data: { tender_id: tender_id },
            type: "post",
            cache: false,
            success: function (result) {
                var datas = JSON.parse(result);
                if (datas.url) {
                    window.location.href = datas.url;
                }
            },
        });
    });
    $("#btn_add_bid_form").click(function (e) {
        $.ajax({
            url: "/rfq/create",
            data: { tender_id: $(this).attr("data-value") },
            type: "post",
            cache: false,
            success: function (result) {
                var datas = JSON.parse(result);
                if (datas.url) {
                    window.location.href = datas.url;
                }
            },
        });
    });
});
