/* Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>) */
/* See LICENSE file for full copyright and licensing details. */
/* License URL : <https://store.webkul.com/license.html/> */

odoo.define("pos_rental_management.textWarningPopUp", function (require) {
  "use strict";

  const AbstractAwaitablePopup = require("point_of_sale.AbstractAwaitablePopup");
  const Registries = require("point_of_sale.Registries");

  class TextWarningPopUp extends AbstractAwaitablePopup {
    getPayload() {
      return null;
    }
  }
  TextWarningPopUp.template = "TextWarningPopUp";
  TextWarningPopUp.defaultProps = {
    title: "Confirm ?",
    cancelText: "Cancel",
    confirmText: "Ok",

    body: "",
  };

  Registries.Component.add(TextWarningPopUp);

  return TextWarningPopUp;
});
