odoo.define('equip3_pos_attendance.PosAttendanceButton', function (require) {
  'use strict';

  const PosComponent = require('point_of_sale.PosComponent');
  const Registries = require('point_of_sale.Registries');
  const ProductScreen = require('point_of_sale.ProductScreen');
  const PosAttendancePopup = require('equip3_pos_attendance.PosAttendancePopup');
  const {posbus} = require('point_of_sale.utils');
  const {Gui} = require('point_of_sale.Gui');

  const framework = require('web.framework');

  class PosAttendanceButton extends PosComponent {
      constructor() {
          super(...arguments);
          this.face_recognition = {};
      }

      onClick() {
        console.log("Open recognition POS")
        console.log(this)
        let popup = new PosAttendancePopup();
        let cashier = this.env.pos.get_cashier();
        console.log("Cashier ~ ", cashier);
        let user_id = cashier.id
        if (cashier.user_id !== undefined){
          console.log("Cashier ~ Is Employee");
          user_id = cashier.user_id[0];
        };
        console.log("Cashier ID ~ ", cashier.id);
        let isCheckout = true;
        popup.open(user_id, isCheckout);
      }
  }

  PosAttendanceButton.template = 'PosAttendanceButton';
  ProductScreen.addControlButton({
      component: PosAttendanceButton,
      condition: function() {
          return true;
      },
  });
  Registries.Component.add(PosAttendanceButton);
  return PosAttendanceButton;
});