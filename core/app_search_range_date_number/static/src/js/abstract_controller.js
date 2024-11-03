odoo.define('app_search_range_date_number.AbstractController', function (require) {
    "use strict";

    var AbstractController = require('web.AbstractController');
    const session = require('web.session');

    AbstractController.include({
        _updateControlPanelProps(state) {
            this._super.apply(this, arguments);
            //增加参数

            var self = this;
            var app_search_range_date_show = session.app_search_range_date_show;
            var app_search_range_number_show = session.app_search_range_number_show;
            var app_fields_date = [];
            var app_fields_number = [];
            if (self.controlPanelProps.withSearchBar && app_search_range_date_show) {
                _.each(self.controlPanelProps.fields, function (value, key, list) {
                    if (value.store && value.type === "datetime" || value.type === "date") {
                        app_fields_date.push([key, value.string, value.type]);
                    }
                });
            };
            //处理number
            if (self.controlPanelProps.withSearchBar && app_search_range_number_show) {
                _.each(self.controlPanelProps.fields, function (value, key, list) {
                    if (value.string && value.string.length > 1 && value.store && (value.type === "integer" || value.type === "float" || value.type === "monetary")) {
                        app_fields_number.push([key, value.string]);
                    }
                });
            };
            Object.assign(this.controlPanelProps, {
                app_fields_date: app_fields_date,
                app_fields_number: app_fields_number,
            });
        },
    });
    return AbstractController;
});
