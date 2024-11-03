odoo.define('awesome_theme_pro.widget', function(require) {
    "use strict";

    var Widget = require('web.Widget');
    var web_client = require('web.web_client');

    var AwesomeWidget = Widget.include({
        has_group: function(xml_id) {
            return web_client.has_group(xml_id)
        },

        has_any_group_or_assignee: function(group_ids, assignees) {
            return web_client.has_any_group_or_assignee(group_ids, assignees)
        }
    });

    return AwesomeWidget;
});