odoo.define('equip3_pos_masterdata.equip3_field_nowhitespaces', function (require) {
    "use strict";

  var basic_fields = require('web.basic_fields');
  var FieldChar = basic_fields.FieldChar;
  var registry = require('web.field_registry');
  var session = require('web.session');

  var Equip3FieldCharNoWhitespaces = FieldChar.extend({
      _onChange: function () {
          var def = this._super.apply(this, arguments);
          let value = this.$el.val();
          if(value && value != ''){
            this.$el.val(value.trim().replaceAll(' ',''));
          }
          return def;
      },
  });

  registry.add("equip3_field_char_nowhitespaces", Equip3FieldCharNoWhitespaces);
});
