odoo.define("equip3_spreadsheet.PivotDialogTable", function (require) {
    "use strict";

    class PivotDialogTable extends owl.Component {
        _onCellClicked(formula) {
            this.trigger('cell-selected', { formula });
        }
    }
    PivotDialogTable.template = "equip3_spreadsheet.PivotDialogTable";
    return PivotDialogTable;
});
