odoo.define('equip3_purchase_operation.purchase_comparison_print', function (require) {
'use strict';
    $(document).ready(function(){
        $("#btn_purchase_comp_print_pdf").click(function (event) {
            var btn_values = $(this).val();
            var btn_id = $(this).attr('id');
            var rpt_type = "pdf";

            document.getElementById('purchase_comp_rpt_type').value = rpt_type
            document.form_purchase_comp_print.submit();
        });
        $("#btn_purchase_comp_print_xls").click(function (event) {
            var btn_values = $(this).val();
            var btn_id = $(this).attr('id');
            var rpt_type = "xls";

            document.getElementById('purchase_comp_rpt_type').value = rpt_type
            document.form_purchase_comp_print.submit();
        });
    });
});