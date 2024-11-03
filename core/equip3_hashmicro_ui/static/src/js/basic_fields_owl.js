odoo.define('equip3_hashmicro_ui.basic_fields_owl', function (require) {
    "use strict";

    var BasicFields = require('web.basic_fields_owl');
    class newFieldBadge extends BasicFields.FieldBadge{
        _getClassFromDecoration = function(decoration){
            return `bg-${decoration.split('-')[1]}-hm`;
        }
    }
    return newFieldBadge;
});


odoo.define('equip3_hashmicro_ui._field_registry_owl', function (require) {
    "use strict";

    const newFieldBadge = require('equip3_hashmicro_ui.basic_fields_owl');
    const registry = require('web.field_registry_owl');

    registry.add('badge', newFieldBadge)
});


odoo.define('equip3_hashmicro_ui.basic_fields', function(require){
    "use strict";

    var { HandleWidget, BooleanToggle } = require('web.basic_fields');

    HandleWidget.include({
        template: 'HandleWidget'
    });

    BooleanToggle.include({
        _onClick: function (event) {
            event.stopPropagation();
            if (this.mode === 'edit' || this.viewType == 'kanban'){
                this._super.apply(this, arguments);
            }
        },
    });
    return {
        HandleWidget: HandleWidget,
        BooleanToggle: BooleanToggle
    };
});


odoo.define('equip3_hashmicro_ui.relational_fields', function(require){
    var FieldMany2One = require('web.relational_fields').FieldMany2One;
    FieldMany2One.include({
        _onClick: function(event){
            if (this.value && this.value.res_id){
                this._super.apply(this, arguments);
            } else {
                event.preventDefault();
            }
        }
    });
    return FieldMany2One;
});
