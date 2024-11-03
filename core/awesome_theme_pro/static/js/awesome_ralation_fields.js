
odoo.define("awesome_theme_pro.relational_fields", function (require) {
    "use strict";

    var config = require('web.config')
    var RelationalFields = require('web.relational_fields')

    // change the mobile status
    RelationalFields.FieldStatus.include({
        _setState: function () {
            this._super.apply(this, arguments);
            if (config.device.isMobile) {
                _.map(this.status_information, value => {
                    value.fold = true;
                });
            }
        },
    });
})
