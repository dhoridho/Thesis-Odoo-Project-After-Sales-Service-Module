/**
 * awesome_theme action manager
 */
odoo.define('awesome_theme_pro.view_dialog', function (require) {
    "use strict";

    var core = require('web.core');
    var view_registry = require('web.view_registry');
    var select_create_controllers_registry = require('web.select_create_controllers_registry');

    var ViewDialg = require('web.view_dialogs');
    var SelectCreateDialog = ViewDialg.SelectCreateDialog

    var _t = core._t;

    var AwsomeViewDialog = SelectCreateDialog.include({

        /**
         * setup controller
         * @param {*} fieldsViews 
         */
        setup: function (fieldsViews) {

            var self = this;
            var fragment = document.createDocumentFragment();

            var domain = this.domain;
            if (this.initialIDs) {
                domain = domain.concat([['id', 'in', this.initialIDs]]);
            }
            var ViewClass = view_registry.get(this.viewType);
            var viewOptions = {};
            var selectCreateController;
            if (this.viewType === 'list') { // add listview specific options
                _.extend(viewOptions, {
                    hasSelectors: !this.options.disable_multiple_selection,
                    readonly: true,

                }, this.options.list_view_options);
                selectCreateController = select_create_controllers_registry.SelectCreateListController;
            }

            if (this.viewType === 'kanban') {
                _.extend(viewOptions, {
                    noDefaultGroupby: true,
                    selectionMode: this.options.selectionMode || false,
                });
                selectCreateController = select_create_controllers_registry.SelectCreateKanbanController;
            }

            var view = new ViewClass(fieldsViews[this.viewType], _.extend(viewOptions, {
                action: {
                    controlPanelFieldsView: fieldsViews.search,
                    help: _.str.sprintf("<p>%s</p>", _t("No records found!")),
                },
                action_buttons: false,
                dynamicFilters: this.options.dynamicFilters,
                context: this.context,
                domain: domain,
                modelName: this.res_model,
                withBreadcrumbs: false,
                withSearchPanel: false,
            }));

            // set up controller
            view.setController(selectCreateController);
            return view.getController(this).then(function (controller) {

                // mark it is execute in dialog
                controller.executeInDialog = true;
                self.viewController = controller;
                
                // render the footer buttons
                self._prepareButtons();

                // call callback, call start here
                return self.viewController.appendTo(fragment);
            }).then(function () {
                return fragment;
            });
        }
    })

    return AwsomeViewDialog
});

