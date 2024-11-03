$(document).ready(function () {
    $.get("/get_hr_annoucement_data", function (data) {
        $("#js_id_hr_annoucement_data_tbl_div").replaceWith(data);
    });
});
