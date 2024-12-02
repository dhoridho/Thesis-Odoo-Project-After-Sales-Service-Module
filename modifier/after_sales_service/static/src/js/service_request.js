odoo.define('your_module.new_service_request', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');

    publicWidget.registry.NewServiceRequest = publicWidget.Widget.extend({
        selector: '#service-request-form',
        start: function () {
            console.log("Service Request Widget Loaded");
            return this._super.apply(this, arguments);
        },
    });

    return publicWidget.registry.NewServiceRequest;
});
