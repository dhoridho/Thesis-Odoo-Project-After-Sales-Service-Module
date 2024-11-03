odoo.define('google_map_route.FieldsRegistry', function (require) {
    'use strict';

    var registry = require('web.field_registry');
    var GplacesAutocomplete = require('google_map_route.GplaceAutocompleteFields');

    registry.add('gplaces_address_autocomplete', GplacesAutocomplete.GplacesAddressAutocompleteField);
    registry.add('gplaces_autocomplete', GplacesAutocomplete.GplacesAutocompleteField);

});