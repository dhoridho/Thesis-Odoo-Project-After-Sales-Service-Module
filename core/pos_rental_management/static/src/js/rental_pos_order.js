/* Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */
odoo.define("pos_rental_management.rental_pos_orders", function (require) {
  "use strict";
  var models = require("point_of_sale.models");
  var core = require("web.core");
  var QWeb = core.qweb;
  var SuperPosModel = models.PosModel.prototype;
  const Registries = require("point_of_sale.Registries");
  const PosComponent = require("point_of_sale.PosComponent");
  const ProductScreen = require("point_of_sale.ProductScreen");
  const ClientLine = require("point_of_sale.ClientLine");
  const { useListener } = require("web.custom_hooks");

  class RentalOrdersScreenWidget extends PosComponent {
    get rentalOrder() {
      var self = this;
      var data = self.env.pos.db.rental_orders;
      var filteredData = {};
      if (self.currentCustomer) {
        _.each(data, function (val, key) {
          if (val.partner_id && val.partner_id[0] == self.currentCustomer) {
            filteredData[key] = val;
          }
        });
        return filteredData;
      }
      return self.env.pos.db.rental_orders;
    }

    get currentOrder() {
      return this.env.pos.get_order();
    }
    get currentCustomer() {
      var self = this;
      if (self.props && self.props.customer_id) {
        return self.props.customer_id;
      } else {
        return false;
      }
    }
    constructor() {
      super(...arguments);
      this.props.details_visible = false;
      this.props.selected_tr_element = null;
    }

    clickBack(event) {
      if (this.props.isShown) {
        this.showScreen("ProductScreen");
      } else {
        this.showTempScreen("ClientListScreen", {});
      }
    }
    keyup_rented_search(ev) {
      var $target = $(ev.currentTarget);
      var input = $target.val();
      $(".rental-data-body tr.rental-order-line").each(function () {
        var flag = false;
        $(this).each(function () {
          if ($(this).text().toLowerCase().indexOf(input.toLowerCase()) >= 0) {
            flag = true;
          }
        });
        if (flag) {
          $(this).show();
        } else {
          $(this).hide();
        }
      });
    }
    _onRentalLineClick(ev) {
      var self = this;
      self.line_select(
        ev,
        $(ev.currentTarget),
        parseInt($(ev.currentTarget).attr("data-id"))
      );
    }
    line_select(event, $line, id) {
      var self = this;
      var order = self.env.pos.db.rental_orders[id];
      $(".wk_order_list .lowlight").removeClass("lowlight");
      if ($line.hasClass("highlight")) {
        $line.removeClass("highlight");
        $line.addClass("lowlight");
        self.display_order_details("hide", order);
      } else {
        $(".wk_order_list .highlight").removeClass("highlight");
        $line.addClass("highlight");
        self.props.selected_tr_element = $line;
        var y = event.pageY - $line.parent().offset().top;
        self.display_order_details("show", order, y);
      }
    }
    display_order_details(visibility, order, clickpos) {
      var self = this;
      var contents = $(".order-details-contents");
      var parent = $(".wk_order_list").parent();
      var scroll = parent.scrollTop();
      var height = contents.height();
      var orderlines = [];
      var statements = [];
      var payment_methods_used = [];
      if (visibility === "show") {
        if (order && order.payment_ids)
          order.payment_ids.forEach(function (payment_id) {
            var payment = self.env.pos.db.payment_by_id[payment_id];
            statements.push(payment);
            payment_methods_used.push(payment.journal_id[0]);
          });
        contents.empty();
        contents.append(
          $(
            QWeb.render("OrderDetails", {
              widget: this,
              order: order,
              statements: statements,
            })
          )
        );
        var new_height = contents.height();
        if (!this.props.details_visible) {
          if (clickpos < scroll + new_height + 20) {
            parent.scrollTop(clickpos - 20);
          } else {
            parent.scrollTop(parent.scrollTop() + new_height);
          }
        } else {
          parent.scrollTop(parent.scrollTop() - height + new_height);
        }
        this.props.details_visible = true;
        $("#close_order_details").on("click", function () {
          if ($(".rental-order-line.highlight").is(":visible")) {
            $(".rental-order-line.highlight").removeClass("highlight");
            $(".rental-order-line.highlight").addClass("lowlight");
            self.props.details_visible = false;
            self.display_order_details("hide", null);
          }
        });
        $("#wk_refund").on("click", function () {
          var order_list = self.env.pos.db.rental_orders;
          var order_id = parseInt($(this).attr("data-id"));
          if (order.state == "rented") {
            self.showPopup("RentalReturnPopup", {
              order: order,
              currency_symbol: self.env.pos.currency.symbol,
            });
          }
        });
      }
      if (visibility === "hide") {
        contents.empty();
        if (height > scroll) {
          contents.css({ height: height + "px" });
          contents.animate({ height: 0 }, 400, function () {
            contents.css({ height: "" });
          });
        } else {
          parent.scrollTop(parent.scrollTop() - height);
        }
        this.props.details_visible = false;
      }
    }
  }
  RentalOrdersScreenWidget.template = "RentalOrdersScreenWidget";
  Registries.Component.add(RentalOrdersScreenWidget);

  class POsRentalOrdersButton extends PosComponent {
    constructor() {
      super(...arguments);
      useListener("click", this.onClick);
    }

    load_new_rental_datas(ids) {
      var self = this;
      return new Promise(function (resolve, reject) {
        var fields = _.find(self.env.pos.models, function (model) {
          return model.model === "rental.pos.order";
        }).fields;
        // var domain = [["id", "not in", ids]]; //only new ids
        var domain = [["state", "=", "rented"]];
        self.env.pos
          .rpc(
            {
              model: "rental.pos.order",
              method: "search_read",
              args: [domain, fields],
            },
            {
              timeout: 3000,
              shadow: true,
            }
          )
          .then(
            function (new_data) {
              self.env.pos.db.rental_orders = {};
              if (new_data.length) {
                new_data.map((a) => (self.env.pos.db.rental_orders[a.id] = a));
              }
              resolve();
            },
            function (type, err) {
              reject();
            }
          );
      });
    }

    async onClick() {
      var self = this;
      await self.load_new_rental_datas(
        _.pluck(self.env.pos.db.rental_orders, "id")
      );
      self.showScreen("RentalOrdersScreenWidget", {});
    }
  }
  POsRentalOrdersButton.template = "POsRentalOrdersButton";
  ProductScreen.addControlButton({
    component: POsRentalOrdersButton,
    condition: function () {
      return true;
    },
  });
  Registries.Component.add(POsRentalOrdersButton);

  const PosResClientLine = (ClientLine) =>
    class extends ClientLine {
      click_rental_pos_orders(event) {
        this.showTempScreen("RentalOrdersScreenWidget", {
          customer_id: this.props.partner.id,
        });
      }
    };
  Registries.Component.extend(ClientLine, PosResClientLine);

  return RentalOrdersScreenWidget;
});
