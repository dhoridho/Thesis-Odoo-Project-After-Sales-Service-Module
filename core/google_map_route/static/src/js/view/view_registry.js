odoo.define('google_map_route.view_registry', function (require) {
    "use strict";

    var MapView = require('google_map_route.MapView');
    var view_registry = require('web.view_registry');

    view_registry.add('google_map', MapView);

});
