odoo.define('equip3_pos_membership.equip3_count_product_redeem', function (require) {
    "use strict";

  var basic_fields = require('web.basic_fields');
  var FieldInteger = basic_fields.FieldInteger;
  var registry = require('web.field_registry');
  var session = require('web.session');

  var Equip3CountProductRedeem = FieldInteger.extend({ 
      _renderReadonly: function () {
          let self = this;
          var res = this._super.apply(this, arguments);
          setTimeout(() => {  self.$el.attr('data_field_integer_value', self.value); }, 100);
          setTimeout(() => {  self.$el.attr('data_field_integer_value', self.value); }, 300);
          return res;
      },
  });

  registry.add("equip3_count_product_redeem", Equip3CountProductRedeem);
});
