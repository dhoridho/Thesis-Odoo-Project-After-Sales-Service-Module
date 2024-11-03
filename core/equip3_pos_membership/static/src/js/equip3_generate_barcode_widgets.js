odoo.define('equip3_pos_membership.equip3_generate_barcode', function (require) {
    "use strict";

  var basic_fields = require('web.basic_fields');
  var FieldChar = basic_fields.FieldChar;
  var registry = require('web.field_registry');
  var session = require('web.session');

  var Equip3GenerateBarcode = FieldChar.extend({
      _renderEdit: function () {
          let self = this;
          var def = this._super.apply(this, arguments);

          let $btn = $('<div class="btn btn btn-link"><span>Generate Barcode</span></div>');
          $btn.on('click', function () {
            if(!$btn.hasClass('loading')){
              self._rpc({
                model: 'res.partner', 
                method: 'get_partner_barcode', 
                args: [session.partner_id]
              }).then(function (barcode) {
                self.$input.val(barcode); 
                self._setValue(self.$input.val());
                $btn.addClass('oe_hidden');
                $btn.removeClass('loading');
              });
            }
            $btn.addClass('loading');
          });

          setTimeout(() => {
            if(self.$input.length && !self.value){
              self.$input.after($btn);
            }
          }, 1000);
          return def;
      },
  });

  registry.add("equip3_generate_barcode", Equip3GenerateBarcode);
});
