/* Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */
odoo.define("pos_rental_management.productRentalPopUp", function (require) {
  "use strict";

  const { useState, useRef } = owl.hooks;
  const AbstractAwaitablePopup = require("point_of_sale.AbstractAwaitablePopup");
  const Registries = require("point_of_sale.Registries");
  var core = require("web.core");
  var _t = core._t;

  class WkRentSelectionPopUp extends AbstractAwaitablePopup {
    constructor() {
      super(...arguments);
      this.state = useState({ product_price: 0.0 });
    }

    mounted() {
      var self = this;
      super.mounted();
      $(".popups").on("change", "#startdatepicker", function (ev) {
        var endDate = $("#enddatepicker").val();
        var startDate = $(ev.currentTarget).val();
        var today = new Date();
        var dd = String(today.getDate()).padStart(2, '0');
        var mm = String(today.getMonth() + 1).padStart(2, '0'); //January is 0!
        var yyyy = today.getFullYear();
        var currentDate = mm + '/' + dd + '/' + yyyy;
        
        if (Date.parse(currentDate) > Date.parse(startDate)){
          $(".popupWarningMessage").text(
            "Start date cannot be before current date"
          );
          $(".popupWarningMessage").show();
          setTimeout(function () {
            $(".popupWarningMessage").hide();
          }, 3000);
          $(ev.currentTarget).val("");
        }
        if (endDate) {
          if (Date.parse(endDate) <= Date.parse(startDate)) {
            $(".popupWarningMessage").text(
              "Start date should be smaller than End date"
            );
            $(".popupWarningMessage").show();
            setTimeout(function () {
              $(".popupWarningMessage").hide();
            }, 3000);
            $(ev.currentTarget).val("");
          } else {
            var tenureCount = 0;
            if (
              self.props.product.selectedTenure &&
              self.props.product.selectedTenure.tenure_uom_id[1] === "Day(s)"
            )
              tenureCount = self._getNumberOfDays(startDate, endDate);
            else if (
              self.props.product.selectedTenure &&
              self.props.product.selectedTenure.tenure_uom_id[1] === "Week(s)"
            )
              tenureCount = self._getNumberOfWeeks(startDate, endDate);
            else if (
              self.props.product.selectedTenure &&
              self.props.product.selectedTenure.tenure_uom_id[1] === "Month(s)"
            )
              tenureCount = self._getNumberOfMonths(startDate, endDate);
            else if (
              self.props.product.selectedTenure &&
              self.props.product.selectedTenure.tenure_uom_id[1] === "Year(s)"
            )
              tenureCount = self._getNumberOfYears(startDate, endDate);
            $(self.el).find(".tenure_count").val(tenureCount);
          }
        }
      });
      $(".popups").on("change", "#enddatepicker", function (ev) {
        var startDate = $("#startdatepicker").val();
        var endDate = $(ev.currentTarget).val();
        if (startDate) {
          if (Date.parse(endDate) <= Date.parse(startDate)) {
            $(".popupWarningMessage").text(
              "End date should be greater than Start date"
            );
            $(".popupWarningMessage").show();
            setTimeout(function () {
              $(".popupWarningMessage").hide();
            }, 3000);
            $(ev.currentTarget).val("");
          } else {
            var tenureCount = 0;
            if (
              self.props.product.selectedTenure &&
              self.props.product.selectedTenure.tenure_uom_id[1] === "Day(s)"
            )
              tenureCount = self._getNumberOfDays(startDate, endDate);
            else if (
              self.props.product.selectedTenure &&
              self.props.product.selectedTenure.tenure_uom_id[1] === "Week(s)"
            )
              tenureCount = self._getNumberOfWeeks(startDate, endDate);
            else if (
              self.props.product.selectedTenure &&
              self.props.product.selectedTenure.tenure_uom_id[1] === "Month(s)"
            )
              tenureCount = self._getNumberOfMonths(startDate, endDate);
            else if (
              self.props.product.selectedTenure &&
              self.props.product.selectedTenure.tenure_uom_id[1] === "Year(s)"
            )
              tenureCount = self._getNumberOfYears(startDate, endDate);
            $(self.el).find(".tenure_count").val(tenureCount);
          }
        } else {
          $(".popupWarningMessage").text("Add start date first");
          $(".popupWarningMessage").show();
          setTimeout(function () {
            $(".popupWarningMessage").hide();
          }, 3000);
          $(ev.currentTarget).val("");
        }
      });

      $(".popups").on("change", ".tenure_count", function (ev) {
        var inputVal = $(ev.currentTarget).val();
        if (
          inputVal &&
          inputVal < self.props.product.selectedTenure.tenure_start_count
        ) {
          $(".popupWarningMessage").text(
            "tenure count should be greater/equal than minimum required count"
          );
          $(".popupWarningMessage").show();
          setTimeout(function () {
            $(".popupWarningMessage").hide();
          }, 3000);
          $(ev.currentTarget).val("");
        } else {
          if ($("#startdatepicker").val() || $("#enddatepicker").val()) {
            $("#startdatepicker").val("");
            $("#enddatepicker").val("");
          }
        }
      });
    }

    cancel() {
      if (!this.props.line.added_tenure_count)
        this.props.line.order.remove_orderline(this.props.line); // remove last line after cancel
      this.props.resolve({ confirmed: false, payload: null });
      this.trigger("close-popup");
    }

    back() {
      this.trigger("close-popup");
      this.props.product.isTenureOptionsPopup = true;
      this.props.product.isRangeSelectionPopup = false;
      this.showPopup("WkRentSelectionPopUp", this.props);
    }

    _getNumberOfDays(startDate, endDate) {
      var Date1 = new Date(startDate);
      var Date2 = new Date(endDate);
      var getTimeDiff = Date2.getTime() - Date1.getTime(); //return total millisec
      return Math.round(getTimeDiff / (1000 * 60 * 60 * 24)); //Divide by one day millisec
    }

    _getNumberOfMonths(startDate, endDate) {
      var startDate = new Date(startDate);
      var endDate = new Date(endDate);
      var Months = (endDate.getFullYear() - startDate.getFullYear()) * 12;
      Months -= startDate.getMonth();
      Months += endDate.getMonth();
      return Months <= 0 ? 0 : Months;
    }

    _getNumberOfYears(startDate, endDate) {
      var Date1 = new Date(startDate);
      var Date2 = new Date(endDate);
      var getTimeDiff = Date2.getTime() - Date1.getTime(); //return total millisec
      return Math.round(getTimeDiff / (1000 * 60 * 60 * 24 * 365)); //Divide by whole year millisec
    }

    _getNumberOfWeeks(startDate, endDate) {
      var Date1 = new Date(startDate);
      var Date2 = new Date(endDate);
      var getTimeDiff = Date2.getTime() - Date1.getTime(); //return total millisec
      return Math.round(getTimeDiff / (1000 * 60 * 60 * 24 * 7)); //Divide by a week millisec
    }

    async _open_range_selection_popup(ev) {
      this.trigger("close-popup");
      var line = this.props.line;
      var product = this.props.product;
      product.isTenureOptionsPopup = false;
      product.isRangeSelectionPopup = true;
      var currentOrder = this.env.pos.get_order();
      product.selectedTenure = product.tenure_data.filter(
        (a) => a.id === parseInt($(ev.currentTarget).attr("tenure-id"))
      )[0];
      const { confirmed, payload } = await this.showPopup(
        "WkRentSelectionPopUp",
        this.props
      );
      if (confirmed) {
        line.selected_tenure_string = payload.tenure_string;
        line.rental_price = payload.product_price;
        line.set_unit_price(line.rental_price);
        line.rental_note = payload.rental_note;
        line.added_tenure_count = payload.addedtenureCount;
        line.startDate = payload.startDate;
        line.endDate = payload.endDate;
        line.selectedTenure = product.selectedTenure;
        if (
          product.is_security_required &&
          product.rental_security_amount &&
          !line.rental_security_line_id
        ) {
          var security_product =
            this.env.pos.db.product_by_id[
              this.env.pos.config.rental_security_product_id[0]
            ];
          currentOrder.add_product(security_product, {
            merge: false,
            price: 0,
          });
          var securityOrderLine = currentOrder.get_last_orderline();
          securityOrderLine.set_unit_price(product.rental_security_amount);
          securityOrderLine.related_product_name =
            "Security Amount Product(" + product.display_name + ")";
          line.rental_security_line_id = securityOrderLine.id;
          securityOrderLine.rental_security_line_id = line.id;
          securityOrderLine.security_price = product.rental_security_amount;
          currentOrder.save_to_db();
        }
      }
    }

    return_product_price() {
      var self = this;
      var tenureCount = $(self.el).find(".tenure_count").val();
      var startDate = $("#startdatepicker").val();
      var endDate = $("#enddatepicker").val();
      if (
        tenureCount > 0 &&
        tenureCount >= self.props.product.selectedTenure.tenure_start_count
      ) {
        var addedtenureCount = tenureCount;
        var rentalNote = $(self.el).find(".rental_note").val();
        var selectedTenure = self.props.product.selectedTenure;
        self.state.product_price = self._calculate_rent_price(
          addedtenureCount,
          selectedTenure,
          startDate,
          endDate
        );
        var tenure_string =
          selectedTenure.name +
          ",@" +
          self.env.pos.format_currency(selectedTenure.tenure_amount) +
          "/" +
          selectedTenure.tenure_uom_id[1].replace("(s)", "") +
          ",";
        if (startDate && endDate) {
          tenure_string += startDate + "=>" + endDate;
        } else
          tenure_string +=
            addedtenureCount + " " + selectedTenure.tenure_uom_id[1];
        self.props.resolve({
          confirmed: true,
          payload: {
            product_price: self.state.product_price,
            tenure_string: tenure_string,
            rental_note: rentalNote,
            addedtenureCount: addedtenureCount,
            startDate: startDate,
            endDate: endDate,
          },
        });
        self.trigger("close-popup");
      } else {
        $(".popupWarningMessage").text(
          "tenure count should be greater/equal than minimum required count."
        );
        $(".popupWarningMessage").show();
        setTimeout(function () {
          $(".popupWarningMessage").hide();
        }, 3000);
      }
    }

    _calculate_rent_price(
      addedtenureCount,
      selectedTenure,
      startDate,
      endDate
    ) {
      var self = this;
      if (startDate && endDate) {
        var totalDays = self._getNumberOfDays(startDate, endDate);
        if (selectedTenure.tenure_uom_id[1] === "Day(s)")
          return selectedTenure.tenure_amount * addedtenureCount;
        else if (selectedTenure.tenure_uom_id[1] === "Week(s)")
          return (selectedTenure.tenure_amount / 7) * totalDays;
        else if (selectedTenure.tenure_uom_id[1] === "Month(s)")
          return (selectedTenure.tenure_amount / 30) * totalDays;
        else if (selectedTenure.tenure_uom_id[1] === "Year(s)")
          return (selectedTenure.tenure_amount / 365) * totalDays;
      } else return selectedTenure.tenure_amount * addedtenureCount;
    }
  }
  WkRentSelectionPopUp.template = "WkRentSelectionPopUp";
  WkRentSelectionPopUp.defaultProps = {
    title: "",
    body: "",
  };

  Registries.Component.add(WkRentSelectionPopUp);

  return WkRentSelectionPopUp;
});
