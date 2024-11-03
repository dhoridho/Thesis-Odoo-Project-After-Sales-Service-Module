odoo.define('tis_venue_booking.view_registry', function (require) {
    "use strict";

    var MapView = require('tis_venue_booking.MapView');
    var view_registry = require('web.view_registry');

    view_registry.add('map', MapView);


});
