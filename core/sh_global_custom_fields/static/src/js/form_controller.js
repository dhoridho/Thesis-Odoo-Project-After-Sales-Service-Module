odoo.define("sh_global_custom_fields.FormController", function (require) {
    "use strict";

    var FormController = require("web.FormController");
    var core = require("web.core");
    var dialogs = require("web.view_dialogs");
    var Dialog = require('web.Dialog');
    var session = require("web.session");

    var _t = core._t;
    var qweb = core.qweb;

    var can_create_custom_field = false;
    session.user_has_group("sh_global_custom_fields.group_global_custom_field").then(function (has_group) {
        can_create_custom_field = has_group;
    });

    FormController.include({
        _getActionMenuItems: function (state) {
            if (!this.hasActionMenus || this.mode === "edit") {
                return null;
            }
            const props = this._super(...arguments);
            const activeField = this.model.getActiveField(state);
            const otherActionItems = [];
            if (this.archiveEnabled && activeField in state.data) {
                if (state.data[activeField]) {
                    otherActionItems.push({
                        description: _t("Archive"),
                        callback: () => {
                            Dialog.confirm(this, _t("Are you sure that you want to archive this record?"), {
                                confirm_callback: () => this._toggleArchiveState(true),
                            });
                        },
                    });
                } else {
                    otherActionItems.push({
                        description: _t("Unarchive"),
                        callback: () => this._toggleArchiveState(false),
                    });
                }
            }
            if (this.activeActions.create && this.activeActions.duplicate) {
                otherActionItems.push({
                    description: _t("Duplicate"),
                    callback: () => this._onDuplicateRecord(this),
                });
            }
            if (this.activeActions.delete) {
                otherActionItems.push({
                    description: _t("Delete"),
                    callback: () => this._onDeleteRecord(this),
                });
            }
            if (can_create_custom_field) {
                otherActionItems.push({
                    description: _t("Create Custom Field"),
                    callback: () => this._onCreateCustomField(this),
                });
                otherActionItems.push({
                    description: _t("Create Custom Tab"),
                    callback: () => this._onCreateCustomTab(this),
                });
            }
            return Object.assign(props, {
                items: Object.assign(this.toolbarActions, { other: otherActionItems }),
            });
        },

        _onCreateCustomField: function () {
            this._CreateCustomField([this.handle]);
        },
        _onCreateCustomTab: function () {
            this._CreateCustomTab([this.handle]);
        },
    });
});
