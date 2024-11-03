odoo.define('awesome.basic_fields_owl', function (require) {
    "use strict";
    
    const CustomCheckbox = require('web.CustomCheckbox')
    
    // need to require to change the template
    require('web.basic_fields')

    CustomCheckbox.template = 'awesome.CustomCheckbox';
})