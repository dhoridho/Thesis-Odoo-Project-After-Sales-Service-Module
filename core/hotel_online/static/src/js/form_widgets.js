odoo.define('pragtech_product_category_customization.form_widget_extend', function (require) {
    "use strict";

    var core = require('web.core');
    var relational_fields = require('web.relational_fields');

    var FieldSelection = relational_fields.FieldSelection;
    var registry = require('web.field_registry');


    var HideSelectionValueWidget = FieldSelection.extend({
        /**
         * @override
         * to hide the automatic applied promo_code_usage selection.
        */
        _renderEdit: function () {
            this._super.apply(this, arguments);
            console.log($(this.$el[0]));
            $(this.$el[0]).find('option').each(function (index, value) {
                if ($(value).val() == '"no_code_needed"' || $(value).val() == '"on_next_order"') {
                    $(value).remove();
                }
            });
        },
    });

    // register your widget
    registry.add("hide_selection_value", HideSelectionValueWidget);

});
