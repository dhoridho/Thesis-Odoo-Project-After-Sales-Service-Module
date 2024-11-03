odoo.define('custom_fields.loader', function (require) {
'use strict';

    var publicWidget = require('web.public.widget');

    function _redefineVisibility(InstanceType) {
        // The method to change attributes of input fields when type is changed
        var FieldsCheckIDS = document.querySelectorAll('.type_visibility_depend');       
        for (var i = 0; i < FieldsCheckIDS.length; ++i) {
            var field = FieldsCheckIDS[i];
            var inputs = field.getElementsByClassName("s_website_form_input");
            
            if (inputs && inputs.length != 0) {
                var input = inputs[0];
                var AvailableTypes = input.getAttribute("invisible");

                if (AvailableTypes) {
                    var AvailableTypesArray = AvailableTypes.split(',');
                    if (AvailableTypesArray.indexOf(InstanceType) > -1) {
                        field.removeAttribute("style");
                        // In case of double change a field should become required back
                        if (input.getAttribute("needrequired") == "True") {
                            input.setAttribute("required", "True");
                        };
                    }
                    else {
                        field.setAttribute("style", "display: none;");
                        if (input.getAttribute("required") == "True") {
                            input.removeAttribute("required");
                            input.setAttribute("needrequired", "True");
                        }
                    };
                };
            };
        };
    };

    publicWidget.registry.contactTypeForm = publicWidget.Widget.extend({
        selector: '.select_type_input',
        start: function () {
            var customTypes = document.querySelectorAll('select.select_type_input');
            if (customTypes.length !== 0) {
                _redefineVisibility(customTypes[0].value);
                customTypes[0].addEventListener('change', function (ev) {
                    var InstanceType = ev.currentTarget.value;
                    _redefineVisibility(InstanceType);
                });
            }
            else {_redefineVisibility(0);};
        },
    });

});
