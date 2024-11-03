$(document).ready(function (e) {
    $("#btn_update_bid").click(function (e) {
        $.ajax({
            url: "/rfq/update",
            data: { order_id: $("#order_id").val() },
            type: "post",
            cache: false,
            success: function (result) {
                $("#update_message").show();
                $("#error_message").show();
            },
        });
    });
});
