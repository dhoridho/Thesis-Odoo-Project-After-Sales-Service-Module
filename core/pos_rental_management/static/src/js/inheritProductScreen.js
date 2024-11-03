/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */
odoo.define("pos_rental_management.inheritProductScreen", function (require) {
  var core = require("web.core");
  const ProductScreen = require("point_of_sale.ProductScreen");
  const ClientListScreen = require("point_of_sale.ClientListScreen");
  const Registries = require("point_of_sale.Registries");
  const { posbus } = require("point_of_sale.utils");
  var _t = core._t;

  const PosProductScreen = (ProductScreen) =>
    class extends ProductScreen {
      click_cancel_refund_order(event) {
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
        this.freeze_screen_action();
      }
      getTotal(order) {
        return this.env.pos.format_currency(order.get_total_with_tax());
      }
      freeze_screen_action() {
        var self = this;
        var current_order = self.env.pos.get_order();
        if (current_order != null && current_order.is_return_order) {
          $(".product").css("pointer-events", "none");
          $(".product").css("opacity", "0.4");
          $(".category-simple-button").css("pointer-events", "none");
          $(".category-simple-button").css("opacity", "0.4");
          $(".header-cell").css("pointer-events", "none");
          $(".header-cell").css("opacity", "0.4");
          $("#refund_order_notify").show();
          $("#cancel_refund_order").show();
          $(".numpad-backspace").css("pointer-events", "none");
          $(".numpad").addClass("return_order_button");
          $(".numpad button").addClass("return_order_button");
          $(".button.set-customer").addClass("return_order_button");
          $("#pos_rental_orders").addClass("return_order_button");
        } else {
          $(".product").css("pointer-events", "");
          $(".product").css("opacity", "");
          $(".category-simple-button").css("pointer-events", "");
          $(".category-simple-button").css("opacity", "");
          $(".header-cell").css("pointer-events", "");
          $(".header-cell").css("opacity", "");
          $("#refund_order_notify").hide();
          $("#cancel_refund_order").hide();
          $(".numpad-backspace").css("pointer-events", "");
          $(".numpad").removeClass("return_order_button");
          $(".numpad button").removeClass("return_order_button");
          $(".button.set-customer").removeClass("return_order_button");
          $("#pos_rental_orders").removeClass("return_order_button");
        }
      }
      mounted() {
        var self = this;
        super.mounted();
        self.freeze_screen_action();
      }
    };

  Registries.Component.extend(ProductScreen, PosProductScreen);

  const PosResClientListScreen = (ClientListScreen) =>
    class extends ClientListScreen {
      constructor() {
        super(...arguments);
        var self = this;
        var current_order = self.env.pos.get_order();
        setTimeout(function () {
          if (current_order != null && current_order.is_return_order) {
            self.back();
          }
        }, 50);
      }
    };
  Registries.Component.extend(ClientListScreen, PosResClientListScreen);
});
