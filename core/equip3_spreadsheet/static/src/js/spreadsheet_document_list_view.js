odoo.define("equip3_spreadsheet.SpreadsheetDocumentListView", function (require) {
    "use strict";

    const ListController = require("web.ListController");
    const ListView = require("web.ListView");
    const viewRegistry = require("web.view_registry");

    const core = require('web.core');
    const _t = core._t;

    const SpreadsheetListController = ListController.extend({
        _onCreateRecord: function (ev) {
            ev.stopPropagation();
            this._createSpreadsheet();
        },

        _onOpenRecord: function (ev) {
            ev.stopPropagation();
            var record = this.model.get(ev.data.id, {raw: true});
            this._editSpreadsheet(record);
        },

        /**
         * Create a new spreadsheet based on a given template and redirect to
         * the spreadsheet.
         * @param {Object} record template
         */
        async _createSpreadsheet() {
            const spreadsheetId = await this._rpc({
                model: "spreadsheet.document",
                method: "create",
                args: [
                    {
                        name: _t("Untitled spreadsheet"),
                        raw: '{}',
                    },
                ],
            });
            this.do_action({
                type: "ir.actions.client",
                tag: "action_open_spreadsheet",
                params: {
                    active_id: spreadsheetId,
                },
            });
        },

        async _editSpreadsheet(record) {
            this.do_action({
                type: "ir.actions.client",
                tag: "action_open_spreadsheet",
                params: {
                    active_id: record.data.id,
                },
            });
        },
    });

    const SpreadsheetListView = ListView.extend({
        config: Object.assign({}, ListView.prototype.config, {
            Controller: SpreadsheetListController,
        }),
    });

    viewRegistry.add("spreadsheet_document_list", SpreadsheetListView);
    
    return {
        SpreadsheetListController: SpreadsheetListController,
        SpreadsheetListView: SpreadsheetListView
    };
});
