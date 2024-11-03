odoo.define('pragmatic_website_cash_on_delivery.cash_on_delivery', function (require) {
'use strict';


    $("#cash_on_delivery_form").hide();
    $("#cash_on_delivery_form_pay_now").hide();
    $("#cash_on_delivery_form_return_cart").hide();
    $('#cash_on_delivery_radio').click(function (e) {
        if(document.getElementById("cash_on_delivery_radio").checked == "true") {
                $("#cash_on_delivery_form").show();
            }
        else {
                $("#o_payment_form_pay").hide();
                $("#payment_method").hide();
                $("#payment_method_cash").hide();
                $("#cash_on_delivery_form").show();
                $("#cash_on_delivery_form_pay_now").hide();
                $("#cash_on_delivery_form_return_cart").hide();
            }
      });

     $("#payment_method").hide();
     $("#cash_on_delivery_form_pay_now").hide();
     $("#cash_on_delivery_form_return_cart").hide();
     $("#payment_method_cash").hide();
     $('#o_payment_form_pay_new').click(function (e) {
       if(document.getElementById("o_payment_form_pay_new").checked == "true") {
                $("#o_payment_form_pay").show();
                $("#payment_method").hide();
                //$("#mb24").hide();
                $("#payment_tokens_list").hide();
                $("#payment_method_cash").show();
                $("#cash_on_delivery_form_pay_now").show();
                $("#cash_on_delivery_form_return_cart").show();
            }
              else {
               
                $("#cash_on_delivery_form").hide();
                $("#payment_method").hide();
                //$("#mb24").hide();
                $("#payment_tokens_list").hide();
                $("#payment_method_cash").show();
                $("#o_payment_form_pay").show();
                $("#cash_on_delivery_form_pay_now").show();
                $("#cash_on_delivery_form_return_cart").show();
            }
          

});

});

