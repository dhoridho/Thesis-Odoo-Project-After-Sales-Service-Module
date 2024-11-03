$(document).ready(function (e){
    $("#btn_retreat_subcon_tender").click(function (e) {
        console.log('------------ inside my retrive JS -------------')
        e.stopPropagation();
        e.preventDefault();
        $.ajax({
            url: "/subcon/tender/retreat?is_subcon_tender=True",
            data: {order_id: $("#order_id").val() },
            type: "post",
            cache: false,
            success: function (result) {
                window.location.href = result;
            },
        });
    });
});