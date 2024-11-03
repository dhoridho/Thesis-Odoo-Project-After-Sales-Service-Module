/* Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

odoo.define("pos_rental_management.inheritPosModels", function (require) {
  "use strict";

  var models = require("point_of_sale.models");
  const { Gui } = require("point_of_sale.Gui");
  var SuperOrder = models.Order;
  var SuperOrderline = models.Orderline;
  var concurrency = require("web.concurrency");
  const Orderline = require("point_of_sale.Orderline");
  const Registries = require("point_of_sale.Registries");
  var utils = require("web.utils");
  var field_utils = require("web.field_utils");
  var Mutex = concurrency.Mutex;
  var round_di = utils.round_decimals;
  var round_pr = utils.round_precision;
  var core = require("web.core");
  var _t = core._t;
  const NumpadWidget = require("point_of_sale.NumpadWidget");

  const NewNumpadWidget = (NumpadWidget) => class extends NumpadWidget {
    sendInput(key) {
      if (this.env.pos.get_order().selected_orderline) {
        if (this.env.pos.get_order().selected_orderline.related_product_name) {
          if (key == "Backspace") {
            Gui.showPopup("ErrorPopup", {
              title: _t("Security Product"),
              body: _t("It's and security product and it can't be remove as it depends on a rental product"),
            });
          } 
          else if(this.props.activeMode === "discount"){
            Gui.showPopup("ErrorPopup", {
              title: _t("Security Product"),
              body: _t("Cannot add discount to this Product as this is a Security Product"),
            });
          }
          else if(this.props.activeMode === "price"){
            Gui.showPopup("ErrorPopup", {
              title: _t("Security Product"),
              body: _t("Price of this Product cannot be Modified as this is a Security Product"),
            });
          }
          else {
            this.trigger("numpad-click-input", { key });
          }
        } 
        else {
          this.trigger("numpad-click-input", { key });
        }
      }
    }
  };
  Registries.Component.extend(NumpadWidget, NewNumpadWidget);

  models.load_fields("product.product", [
    "available_for_rent",
    "is_security_required",
    "rental_security_amount",
    "rental_tenure_ids",
  ]);

  models.load_fields("res.partner", [
    "property_payment_term_id",
    "prevent_partial_payment",
  ]);

  models.load_models(
    [
      {
        model: "rental.product.tenure",
        loaded: function (self, rental_tenure) {
          self.db.rental_tenure_data = {};
          if (rental_tenure.length)
            _.each(rental_tenure, function (res) {
              self.db.rental_tenure_data[res.id] = res;
            });
        },
      },
      {
        model: "rental.pos.order",
        loaded: function (self, rental_order) {
          self.db.rental_orders = {};
          if (rental_order.length)
            _.each(rental_order, function (res) {
              self.db.rental_orders[res.id] = res;
            });
        },
      },
    ],
    {
      after: "product.product",
    }
  );

  models.Order = models.Order.extend({
    initialize: function (attributes, options) {
      SuperOrder.prototype.initialize.call(this, attributes, options);
      this.invoice_remark = "";
      this.is_partially_paid = false;
      this.is_return_order = false;
      this.rental_number = false;
      this.deducted_amount = 0;
      this.refund_security_amount = 0;
      this.extra_refund_amount = 0;
    },
    export_as_JSON: function () {
      var self = this;
      var json = SuperOrder.prototype.export_as_JSON.call(self);
      json.invoice_remark = self.invoice_remark;
      json.is_partially_paid = self.is_partially_paid;
      json.is_return_order = self.is_return_order;
      json.rental_number = self.rental_number;
      json.deducted_amount = self.deducted_amount;
      json.extra_refund_amount = self.extra_refund_amount;
      json.refund_security_amount = self.refund_security_amount;
      return json;
    },
    init_from_JSON: function (json) {
      SuperOrder.prototype.init_from_JSON.call(this, json);
      var self = this;
      self.is_return_order = json.is_return_order;
      self.rental_number = json.rental_number;
      self.is_partially_paid = json.is_partially_paid;
    },

    _returnSecurityProduct: function () {
      return self.pos.db.product_by_id[
        self.pos.config.rental_security_product_id[0]
      ];
    },

    // remove rental line which has no tenure
    add_orderline: function (line) {
      this.assert_editable();
      if (line.order) {
        line.order.remove_orderline(line);
      }
      line.order = this;
      if (
        !(
          line.product.available_for_rent &&
          !line.added_tenure_count &&
          line.quantity > 0
        )
      ) {
        this.orderlines.add(line);
      }
      this.select_orderline(this.get_last_orderline());
    },

    add_product: function (product, options) {
      var self = this;
      if (product.available_for_rent && !self.is_return_order) {
        if (options) options.merge = false;
        else options = { merge: false };
        SuperOrder.prototype.add_product.call(self, product, options);
        var updated_last_orderline = self.get_last_orderline();

        updated_last_orderline.is_rental_product = product.available_for_rent;
        product.tenure_data = updated_last_orderline._returnTenureData(
          product.rental_tenure_ids
        );
        product.isTenureOptionsPopup = true;
        product.isRangeSelectionPopup = false;
        Gui.showPopup("WkRentSelectionPopUp", {
          product: product,
          line: updated_last_orderline,
        });
      } else SuperOrder.prototype.add_product.call(self, product, options);
    },
    getOrderReceiptEnv: function () {
      var result = SuperOrder.prototype.getOrderReceiptEnv.call(this);
      result.receipt.order = this;
      return result;
    },
    get_due: function (paymentline) {
      var self = this;
      if (self.is_return_order && this.get_total_with_tax() < 0) {
        if (!paymentline) {
          var due = Math.abs(this.get_total_with_tax()) - this.get_total_paid();
        } else {
          var due = Math.abs(this.get_total_with_tax());
          var lines = this.paymentlines.models;
          for (var i = 0; i < lines.length; i++) {
            if (lines[i] === paymentline) {
              break;
            } else {
              due -= lines[i].get_amount();
            }
          }
        }
        return round_pr(Math.max(0, due), this.pos.currency.rounding);
      } else return SuperOrder.prototype.get_due.call(self, paymentline);
    },
    get_change: function (paymentline) {
      var self = this;
      if (self.is_return_order && this.get_total_with_tax() < 0) {
        if (!paymentline) {
          var change =
            this.get_total_paid() - Math.abs(this.get_total_with_tax());
        } else {
          var change = -Math.abs(this.get_total_with_tax());
          var lines = this.paymentlines.models;
          for (var i = 0; i < lines.length; i++) {
            change += lines[i].get_amount();
            if (lines[i] === paymentline) {
              break;
            }
          }
        }
        return round_pr(Math.max(0, change), this.pos.currency.rounding);
      } else return SuperOrder.prototype.get_change.call(self, paymentline);
    },
  });

  models.Orderline = models.Orderline.extend({
    initialize: function (attr, options) {
      var self = this;
      self.selected_tenure_string = "";
      self.is_rental_product = false;
      self.rental_price = 0.0;
      self.security_price = 0.0;
      self.deducted_amount = 0.0;
      self.extra_refund_amount = 0.0;
      self.refund_security_amount = 0.0;
      self.rental_note = "";
      self.added_tenure_count = 0;
      self.selectedTenure = {};
      self.rental_security_line_id = false;
      self.related_product_name = false;
      SuperOrderline.prototype.initialize.call(self, attr, options);
    },
    export_for_printing: function () {
      var self = this;
      var data = SuperOrderline.prototype.export_for_printing.call(this);
      data.is_rental_product = self.is_rental_product;
      data.selected_tenure_string = self.selected_tenure_string;
      data.rental_price = self.rental_price;
      data.rental_note = self.rental_note;
      data.added_tenure_count = self.added_tenure_count;
      data.selectedTenure = self.selectedTenure;
      data.related_product_name = self.related_product_name;
      return data;
    },
    export_as_JSON: function () {
      var self = this;
      var json = SuperOrderline.prototype.export_as_JSON.call(this);
      json.is_rental_product = self.is_rental_product;
      json.selected_tenure_string = self.selected_tenure_string;
      json.rental_price = self.rental_price;
      json.security_price = self.security_price;
      json.refund_security_amount = self.refund_security_amount;
      json.extra_refund_amount = self.extra_refund_amount;
      json.deducted_amount = self.deducted_amount;
      json.rental_note = self.rental_note;
      json.added_tenure_count = self.added_tenure_count;
      json.selectedTenure = self.selectedTenure;
      json.rental_security_line_id = self.rental_security_line_id;
      json.related_product_name = self.related_product_name;
      return json;
    },
    init_from_JSON: function (json) {
      SuperOrderline.prototype.init_from_JSON.call(this, json);
      if (json && json.is_rental_product) {
        this.is_rental_product = json.is_rental_product;
        this.selected_tenure_string = json.selected_tenure_string;
        this.rental_price = json.rental_price;
        this.rental_note = json.rental_note;
        this.added_tenure_count = json.added_tenure_count;
        this.selectedTenure = json.selectedTenure;
        this.related_product_name = json.related_product_name;
      }
      this.rental_security_line_id = json.rental_security_line_id;
      this.related_product_name = json.related_product_name;
      this.security_price = json.security_price;
      this.refund_security_amount = self.refund_security_amount;
      this.extra_refund_amount = self.extra_refund_amount;
      this.deducted_amount = self.deducted_amount;
    },

    set_unit_price: function (price) {
      var self = this;
      if (
        self.is_rental_product &&
        self.rental_price &&
        self.rental_price != price
      )
        price = self.rental_price;
      if (self.security_price) price = self.security_price;
      if (self.refund_security_amount) price = -1 * self.refund_security_amount;
      if (self.extra_refund_amount) price = -1 * self.extra_refund_amount;
      if (self.deducted_amount) price = self.deducted_amount;
      SuperOrderline.prototype.set_unit_price.call(self, price);
    },
    _returnTenureData(rental_tenure_ids) {
      var tenure_data = [];
      var self = this;
      _.each(rental_tenure_ids, function (data) {
        if (self.pos.db.rental_tenure_data[data] != undefined) {
          tenure_data.push(self.pos.db.rental_tenure_data[data]);
        }
      });
      return tenure_data;
    },

    set_quantity: function (quantity, keep_price) {
      var self = this
      this.order.assert_editable();
      if (quantity === "remove") {
        if (this.rental_security_line_id)
          this.order.remove_orderline(
            this.order.orderlines._byId[this.rental_security_line_id]
          ); // remove lined security product and vice
        this.order.remove_orderline(this);
        return;
      } else {
        var quant =
          typeof quantity === "number"
            ? quantity
            : field_utils.parse.float("" + quantity) || 0;
        var unit = this.get_unit();
        if (
          this.product.id === this.pos.config.rental_security_product_id[0] &&
          this.quantity !== undefined
        ) {
          var rental_qty_restriction = true;
        } else {
          if (unit) {
            var security_line;
            var security_line_id = this.rental_security_line_id
            $.each(this.order.orderlines.models, function(index, value) {
              if(value.id === security_line_id){
                security_line = value
              }
            }); 
            if (unit.rounding) {
              var decimals = this.pos.dp["Product Unit of Measure"];
              var rounding = Math.max(unit.rounding, Math.pow(10, -decimals));
              this.quantity = round_pr(quant, rounding);
              this.quantityStr = field_utils.format.float(this.quantity, {
                digits: [69, decimals],
              });
              if(security_line){
                security_line.quantity    = round_pr(quant, rounding);
                security_line.quantityStr = field_utils.format.float(security_line.quantity, {digits: [69, decimals]});
              }
            } else {
              this.quantity = round_pr(quant, 1);
              this.quantityStr = this.quantity.toFixed(0);
              if(security_line){
                security_line.quantity    = round_pr(quant, 1);
                security_line.quantityStr = security_line.quantity.toFixed(0);
              }  
            }
          } else {
            this.quantity = quant;
            this.quantityStr = "" + this.quantity;
            if(security_line){
              security_line.quantity    = quant;
              security_line.quantityStr = "" + security_line.quantity;
            }
          }
        }
      }
      // just like in sale.order changing the quantity will recompute the unit price
      if (!keep_price && !this.price_manually_set) {
        this.set_unit_price(
          this.product.get_price(this.order.pricelist, this.get_quantity()) +
            this.get_price_extra()
        );
        this.order.fix_tax_included_price(this);
      }
      this.trigger("change", this);
    },
  });

  const PosResOrderline = (Orderline) =>
    class extends Orderline {
      open_rental_popup(orderline) {
        var self = this;
        orderline.product.isTenureOptionsPopup = true;
        orderline.product.isRangeSelectionPopup = false;
        orderline.product.tenure_data = orderline._returnTenureData(
          orderline.product.rental_tenure_ids
        );
        self.showPopup("WkRentSelectionPopUp", {
          product: orderline.product,
          line: orderline,
        });
      }
    };

  Registries.Component.extend(Orderline, PosResOrderline);

  return {
    'Orderline' : Orderline,
    'NumpadWidget' : NumpadWidget,
  };
});
