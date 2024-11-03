
odoo.define('equip3_pos_attendance.CashierName', function (require) {
  'use strict';

  const Registries = require('point_of_sale.Registries');
  const framework = require('web.framework');
  const PosAttendancePopup = require('equip3_pos_attendance.PosAttendancePopup');
  const { Gui } = require('point_of_sale.Gui');

  const CashierName = require('point_of_sale.CashierName');

  const PosAttendanceCashierName = (CashierName) =>
    class extends CashierName {
      async selectCashier() {
        if (!this.env.pos.config.module_pos_hr) return;
        let self = this;
        const list = this.env.pos.allowed_users
          .filter((user) => user.id !== this.env.pos.get_cashier().id)
          .map((user) => {
              return {
                  id: user.id,
                  item: user,
                  label: user.name,
                  isSelected: false,
                  imageUrl: 'data:image/png;base64, ' + user['image_1920'],
              };
          });
        const user = await this.selectEmployee(list);
        if (user) {
            user['is_user'] = true
            if (this.env.pos.config.pos_login_face_recognition){
              this.rpc({
                  model: 'res.users',
                  method: 'is_require_check_in',
                  args: [user.id],
              }).then(function(vals){
                  if(vals.userHaveFaceTables){
                    if(vals.isRequireCheckIn){
                        let popup = new PosAttendancePopup();
                        let isCheckout = false;
                        popup.open(user.id, isCheckout);
                    }else{
                      Gui.showPopup('ConfirmPopup', {
                          title: 'Success',
                          body: 'Already checkin',
                      });
                      self.env.pos.set_cashier(user);
                    };
                  }else{
                    Gui.showPopup('ErrorPopup', {
                      title: 'Error',
                      body: "Selected User/Cashier doesn't have a Face Table yet. Please ask Administrator!",
                    });
                  }
              })
            }else{
              this.env.pos.set_cashier(user);
            }
        }
      }
    }
    Registries.Component.extend(CashierName, PosAttendanceCashierName);

    return PosAttendanceCashierName;
});