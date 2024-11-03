$(document).ready(function () {
    $.get("/get_employee_birhday_data", function (data) {
        $("#js_id_sh_birthday_data_tbl_div").replaceWith(data);
    });

    $.get("/get_employee_anniversary_data", function (data) {
        $("#js_id_sh_anniversary_data_tbl_div").replaceWith(data);
    });

    $.get("/get_annoucement_data", function (data) {
        $("#js_id_sh_annoucement_data_tbl_div").replaceWith(data);
    });

    $.get("/get_employee_payslip_data", function (data) {
        $("#js_id_sh_paylsip_data_tbl_div").replaceWith(data);
    });

    $.get("/get_employee_expense_data", function (data) {
        $("#js_id_sh_expense_data_tbl_div").replaceWith(data);
    });

    $.get("/get_employee_attendance_data", function (data) {
        $("#js_id_sh_attendance_data_tbl_div").replaceWith(data);
    });

    $.get("/get_employee_leave_data", function (data) {
        $("#js_id_sh_leave_data_tbl_div").replaceWith(data);
    });
});
