odoo.define('advanced_web_domain_widget._terabits_field_registry', function (require) {
    "use strict";
    var basic_fields = require('advanced_web_domain_widget.basic_fields');
    // var registry = require('advanced_web_domain_widget.terabits_field_registry');
    const fieldRegistry = require('web.field_registry');

    // Basic fields
    fieldRegistry.add('terabits_domain', basic_fields.TerabitsFieldDomain);
    fieldRegistry.add('terabits_field_domain', basic_fields.TerabitsFieldDomain2);
});


