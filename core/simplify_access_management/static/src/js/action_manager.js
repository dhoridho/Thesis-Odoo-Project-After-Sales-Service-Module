odoo.define('simplify_access_management.action_manager', function (require) {
    "use strict";
    
    var config = require('web.config');
    var ActionManager = require('web.ActionManager');
    var config = require('web.config');
    var view_registry = require('web.view_registry');

    ActionManager.include({
        
        _generateActionViews: function (action, fieldsViews) {
            var views = [];
            _.each(action.views, function (view) {
                // Check it's restricted or not
                if(_.contains(Object.keys(fieldsViews),view[1])){
                    var viewType = view[1];
                    var fieldsView = fieldsViews[viewType];
                    var parsedXML = new DOMParser().parseFromString(fieldsView.arch, "text/xml");
                    var key = parsedXML.documentElement.getAttribute('js_class');
                    var View = view_registry.get(key || viewType);
                    if (View) {
                        views.push({
                            accessKey: View.prototype.accessKey || View.prototype.accesskey,
                            displayName: View.prototype.display_name,
                            fieldsView: fieldsView,
                            icon: View.prototype.icon,
                            isMobileFriendly: View.prototype.mobile_friendly,
                            multiRecord: View.prototype.multi_record,
                            type: viewType,
                            viewID: view[0],
                            Widget: View,
                        });
                    } else if (config.isDebug('assets')) {
                        console.log("View type '" + viewType + "' is not present in the view registry.");
                    }
                }
            });
            return views;
        },
    });
});