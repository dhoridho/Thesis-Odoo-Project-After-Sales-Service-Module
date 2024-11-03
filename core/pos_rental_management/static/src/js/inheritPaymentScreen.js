/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */
odoo.define("pos_rental_management.inheritPaymentScreen", function (require) {
  var core = require("web.core");
  const PaymentScreen = require("point_of_sale.PaymentScreen");
  const Registries = require("point_of_sale.Registries");
  const { posbus } = require("point_of_sale.utils");
  var _t = core._t;

  const PosResPaymentScreen = (PaymentScreen) =>
    class extends PaymentScreen {
      click_delete_return_order(event) {
        var order = this.env.pos.get_order();
        this.deleteOrder(order);
      }
      async deleteOrder(order) {
        const screen = order.get_screen_data();
        if (
          ["ProductScreen", "PaymentScreen"].includes(screen.name) &&
          order.get_orderlines().length > 0
        ) {
          const { confirmed } = await this.showPopup("ConfirmPopup", {
            title: "Existing orderlines",
            body: `${order.name} has total amount of ${this.getTotal(
              order
            )}, are you sure you want delete this order?`,
          });
          if (!confirmed) return;
        }
        if (order) {
          order.destroy({ reason: "abandon" });
        }
        posbus.trigger("order-deleted");
        this.showScreen("ProductScreen");
      }
      getTotal(order) {
        return this.env.pos.format_currency(order.get_total_with_tax());
      }

      mounted() {
        super.mounted();
        var order = this.env.pos.get_order();
        // return rented product
        if (
          order &&
          order.is_return_order &&
          order.get_total_with_tax() < 0
        ) {
          $(".payment-screen h1").html("Refund");
          $(".button.cancel_refund_order").show();
        } else if (
          order &&
          order.is_return_order &&
          order.get_total_with_tax() > 0
        ) {
          $(".payment-screen h1").html("Payment");
          $(".button.cancel_refund_order").show();
        } else {
          $(".button.cancel_refund_order").hide();
        }

        // partital payment option
        if (order && order.get_total_with_tax() > 0)
          $(".partial-payment-remark").show();
        else $(".partial-payment-remark").hide();
        this.validate_partial_payment_checklist();
      }
      focus_in_description(event) {
        var self = this;
        $("body").off("keypress", self.keyboard_handler);
        $("body").off("keydown", self.keyboard_keydown_handler);
      }
      focus_out_description(event) {
        var self = this;
        $("body").on("keypress", self.keyboard_handler);
        $("body").on("keydown", self.keyboard_keydown_handler);
      }
      keyup_description(event) {
        this.validate_partial_payment_checklist();
      }
      validate_partial_payment_checklist() {
        var self = this;
        var $elvalidate = $(".next");
        var order = self.env.pos.get_order();
        var client = order.get_client();
        if (!self.env.pos.config.partial_payment)
          $elvalidate.removeClass("highlight");
        else if (
          client != null &&
          order.get_due() > 0 &&
          order.is_to_invoice() &&
          $("#partial_payment_description").val() != ""
        ) {
          if (
            client.property_payment_term_id &&
            !client.prevent_partial_payment
          )
            $elvalidate.addClass("highlight");
          else $elvalidate.removeClass("highlight");
        } else if (
          order.is_to_invoice() &&
          $("#partial_payment_description").val() == ""
        )
          $elvalidate.removeClass("highlight");
        else if (order.get_due() != 0) $elvalidate.removeClass("highlight");
        else if (order.get_due() == 0 && order.get_total_with_tax() != 0)
          $elvalidate.addClass("highlight");
      }
      click_invoice() {
        this._super();
        this.validate_partial_payment_checklist();
      }

      async validateOrder(isForceValidate) {
        var self = this;
        var order = self.env.pos.get_order();
        var rentalLineCount = order.orderlines.models.filter(
          (a) => a.is_rental_product == true
        ).length;
        if (self.env.pos.config.partial_payment && rentalLineCount) {
          order.invoice_remark = $("#partial_payment_description").val();
          if (order.get_orderlines().length === 0) {
            this.showPopup("ErrorPopup", {
              title: _t("Empty Order"),
              body: _t(
                "There must be at least one product in your order before it can be validated"
              ),
            });
            return false;
          } else if (!(await self._isOrderValid(isForceValidate))) {
            if (!order.is_paid() && !order.is_to_invoice()) {
              const { confirmed } = await self.showPopup("TextWarningPopUp", {
                title: _t("Cannot Validate This Order!!!"),
                body: _t(
                  "You need to set Invoice for validating Partial Payments."
                ),
              });
              if (confirmed) {
                order.set_to_invoice(true);
              }
              return;
            }
            if (order.is_to_invoice()) {
              if (order.get_client() != null && order.get_due() > 0) {
                if (order.get_client().prevent_partial_payment) {
                  self.showPopup("TextWarningPopUp", {
                    title: _t("Cannot Validate This Order!!!"),
                    body: _t(
                      "Customer's Payment Term does not allow Partial Payments."
                    ),
                  });
                  return false;
                }
              }
              if (
                order.get_client() != null &&
                $("#partial_payment_description").val() == ""
              ) {
                const { confirmed } = await self.showPopup("TextWarningPopUp", {
                  title: _t("Cannot Validate This Order!!!"),
                  body: _t(
                    "You need to add invoice remark for validating Partial Payments."
                  ),
                });
                if (confirmed) {
                  $("#partial_payment_description").css({
                    border: "double",
                    width: "91%",
                  });
                }
                return;
              }
              if ($("#partial_payment_description").val() != "") {
                order.is_partially_paid = true;
                await this._finalizeValidation();
              }
            }
          } else await this._finalizeValidation();
        } else super.validateOrder(isForceValidate);
      }
    };
  Registries.Component.extend(PaymentScreen, PosResPaymentScreen);

  return PaymentScreen;
});
