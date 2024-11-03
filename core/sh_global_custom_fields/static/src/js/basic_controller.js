odoo.define("sh_global_custom_fields.BasicController", function (require) {
    "use strict";

    var BasicController = require("web.BasicController");
    var core = require("web.core");
    var _t = core._t;
    var qweb = core.qweb;
    BasicController.include({
        _CreateCustomField: function (ids) {
            var self = this;
            var actionViews = this.actionViews;
            var view_id = "";
            _.each(actionViews, function (actionView) {
                if (actionView.type == "form") {
                    if (actionView.fieldsView.view_id) {
                        view_id = actionView.fieldsView.view_id;
                        self.do_action({
                            res_model: "sh.custom.field.model",
                            name: _t("Create Custom Field"),
                            views: [[false, "form"]],
                            target: "new",
                            type: "ir.actions.act_window",
                            context: {
                                default_parent_view_id: view_id,
                                default_parent_model: self.modelName,
                            },
                        });
                    }
                }
            });
        },
        _CreateCustomTab: function (ids) {
            var self = this;
            var actionViews = this.actionViews;
            var view_id = "";
            _.each(actionViews, function (actionView) {
                if (actionView.type == "form") {
                    if (actionView.fieldsView.view_id) {
                        view_id = actionView.fieldsView.view_id;
                        self.do_action({
                            res_model: "sh.custom.model.tab",
                            name: _t("Create Custom Tab"),
                            views: [[false, "form"]],
                            target: "new",
                            type: "ir.actions.act_window",
                            context: {
                                default_parent_view_id: view_id,
                                default_parent_model: self.modelName,
                            },
                        });
                    }
                }
            });
        },
    });
});
