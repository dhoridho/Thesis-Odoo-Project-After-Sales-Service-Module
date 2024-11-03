/* Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */
odoo.define("pos_rental_management.returnPopup", function (require) {
  "use strict";

  const { useState, useRef } = owl.hooks;
  const AbstractAwaitablePopup = require("point_of_sale.AbstractAwaitablePopup");
  const Registries = require("point_of_sale.Registries");
  var core = require("web.core");
  var _t = core._t;

  class RentalReturnPopup extends AbstractAwaitablePopup {
    constructor() {
      super(...arguments);
    }
      get currencySymbol() {
          var self = this;
          return self.props.currency_symbol
      }
    click_return_rented_product(event) {
      var self = this;
      var refund_security_amount = parseFloat($('.table_data_cells.refund_security_amount').html())
      var extra_refund_amount = parseFloat(
        $(".refund_extra_amount input").val()
      );
        var deducted_amount = parseFloat($(".deducted_amount input").val());
        if (refund_security_amount < 0 || extra_refund_amount < 0 || deducted_amount < 0) {
            $('.warning-message-return').removeClass('d-none');
            return false;
        }else $('.warning-message-return').addClass('d-none');
      self.create_return_order(
        refund_security_amount,
        extra_refund_amount,
        deducted_amount
      );
    }
    create_return_order(
      refund_security_amount,
      extra_refund_amount,
      deducted_amount
    ) {
      var self = this;
      var order = self.props.order;
      self.env.pos.add_new_order();
      this.cancel();
      var refund_order = self.env.pos.get_order();
      refund_order.is_return_order = true;
      refund_order.rental_number = order.id;
      refund_order.refund_security_amount = refund_security_amount;
      refund_order.extra_refund_amount = extra_refund_amount;
      refund_order.deducted_amount = deducted_amount;
      if (order.partner_id)
        refund_order.set_client(
          self.env.pos.db.get_partner_by_id(order.partner_id[0])
        );
      var product = self.env.pos.db.get_product_by_id(order.product_id[0]);
      refund_order.add_product(product, {
        quantity: -1,
        price: 0,
      });
      var refund_product =
        this.env.pos.db.product_by_id[
          this.env.pos.config.rental_security_product_id[0]
        ];
  
      console.log("refund_security_amount===========:",refund_security_amount)
      console.log("deducted_amount===========:",deducted_amount)
      console.log("extra_refund_amount===========:",extra_refund_amount)

      if (refund_security_amount && !deducted_amount && !extra_refund_amount) {
        refund_order.add_product(refund_product, {
          merge: false,
          price: -1 * refund_security_amount,
        });
        var refundSecurityOrderLine = refund_order.get_last_orderline();
        refundSecurityOrderLine.refund_security_amount = refund_security_amount;
        refundSecurityOrderLine.related_product_name =
          "Refund Security Amount Product(" + product.display_name + ")";
      }
      if (extra_refund_amount) {
        refund_order.add_product(refund_product, {
          merge: false,
          price: -1 * (extra_refund_amount +refund_security_amount) ,
        });

        var refundExtraOrderLine = refund_order.get_last_orderline();
        refundExtraOrderLine.extra_refund_amount = extra_refund_amount;
        refundExtraOrderLine.related_product_name =
          "Refund Extra Amount Product(" + product.display_name + ")";
      }
      if (deducted_amount) {
        refund_order.add_product(refund_product, {
          merge: false,
          price: -1*(refund_security_amount - deducted_amount),
        });
        var deductAmountOrderLine = refund_order.get_last_orderline();
        deductAmountOrderLine.deducted_amount = deducted_amount;
        deductAmountOrderLine.related_product_name =
          "Deducted Amount Product(" + product.display_name + ")";
      }
      // self.pos.set_order(refund_order);
      refund_order.save_to_db();
      self.showScreen("PaymentScreen");
    }
  }
  RentalReturnPopup.template = "RentalReturnPopup";
  RentalReturnPopup.defaultProps = { title: "Message", value: "" };
  Registries.Component.add(RentalReturnPopup);
});
