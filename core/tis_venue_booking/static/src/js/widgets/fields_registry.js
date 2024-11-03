odoo.define('tis_venue_booking.FieldsRegistry', function(require) {
    'use strict';

    var registry = require('web.field_registry');
    var GplacesAutocomplete = require('tis_venue_booking.GplaceAutocompleteFields');

    registry.add('gplaces_address_autocomplete', GplacesAutocomplete.GplacesAddressAutocompleteField);
    registry.add('gplaces_autocomplete', GplacesAutocomplete.GplacesAutocompleteField);

});