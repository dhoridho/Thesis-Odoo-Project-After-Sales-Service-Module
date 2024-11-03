odoo.define('equip3_manuf_masterdata.MrpBomDomain', function(require){
    "use strict";

    var { FieldMany2One } = require('web.relational_fields');

    FieldMany2One.include({
        init: function (parent, name, record, options) {
            this._super.apply(this, arguments);
            if (this.field.relation == 'mrp.bom'){
                this.additionalContext.bom_state = 'confirm';
            }
        }
    });
}); 