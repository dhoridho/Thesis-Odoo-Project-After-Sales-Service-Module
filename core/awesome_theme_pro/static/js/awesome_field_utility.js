odoo.define('awesome.field_utils', function (require) {
    "use strict";
    
    var dom = require('web.dom');
    var field_utils = require('web.field_utils')

    var core = require('web.core');
    var dom = require('web.dom');
    
    var _t = core._t;
    
    /**
     * rewrite to keep the check box align center
     * @param {*} value 
     * @param {*} field 
     * @param {*} options 
     */
    function formatBoolean(value, field, options) {
        if (options && options.forceString) {
            return value ? _t('True') : _t('False');
        }
        var $check_box =  dom.renderCheckbox({
            prop: {
                checked: value,
                disabled: true,
            },
        });
        return $("<div class='d-flex align-items-center awesome-check-box' />").append($check_box);
    }

    field_utils.format.boolean = formatBoolean;
})
    