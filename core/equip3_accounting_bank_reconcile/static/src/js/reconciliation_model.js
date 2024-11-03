odoo.define('equip3_accounting_bank_reconcile.ReconciliationModel', function (require) {
    'use strict';

    var StatementModel = require('account.ReconciliationModel').StatementModel;

    StatementModel.include({
        /**
         * @override
         * @param {Object} prop
         * @returns {Boolean}
         */
        _getDefaultMode: function (handle) {
            var line = this.getLine(handle);
            if (
                line.balance.amount === 0 &&
                (!line.st_line.mv_lines_match_rp ||
                    line.st_line.mv_lines_match_rp.length === 0) &&
                (!line.st_line.mv_lines_match_other ||
                    line.st_line.mv_lines_match_other.length === 0)
            ) {
                return "inactive";
            }
            // if (line.mv_lines_match_rp && line.mv_lines_match_rp.length) {
            //     return "match_rp";
            // }
            if (line.mv_lines_match_other && line.mv_lines_match_other.length) {
                return "match_other";
            }
            return "create";
        },
    });
});