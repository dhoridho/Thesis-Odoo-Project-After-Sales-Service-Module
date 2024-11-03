odoo.define('equip3_pos_membership.equip3_custom_selection', function (require) {
    "use strict";

  var relational_fields = require('web.relational_fields');
  var FieldSelection = relational_fields.FieldSelection;
  var registry = require('web.field_registry');

  var Equip3CustomSelection = FieldSelection.extend({
      _renderEdit: function () {
          this._super.apply(this, arguments);
          let custom_selection = this.attrs.options.custom_selection;
          if(custom_selection){
            let attr_value;
            $(this.$el[0]).find('option').each(function (index, value) {
              attr_value = $(value).attr('value').replaceAll('"','');
              if(attr_value != false){
                if(custom_selection.includes(attr_value) == false){
                  $(value).remove();
                }
              }
            });
          }
      }
  });

  registry.add("equip3_custom_selection", Equip3CustomSelection);
});
