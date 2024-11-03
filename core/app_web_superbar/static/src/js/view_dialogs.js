odoo.define('app_web_superbar.view_dialogs', function (require) {
    "use strict";

    /**
     *扩展13 searchpanel 和 superbar 类似
     */
    
    var core = require('web.core');
    var view_dialogs = require('web.view_dialogs');
    var view_registry = require('web.view_registry');
    var select_create_controllers_registry = require('web.select_create_controllers_registry');

    var _t = core._t;

    view_dialogs.SelectCreateDialog.include({
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
            withSearchPanel: true,
        }));
        view.setController(selectCreateController);
        return view.getController(this).then(function (controller) {
            self.viewController = controller;
            // render the footer buttons
            self._prepareButtons();
            return self.viewController.appendTo(fragment);
        }).then(function () {
            return fragment;
        });
    },
    });

});