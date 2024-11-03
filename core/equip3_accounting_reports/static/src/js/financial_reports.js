odoo.define('equip3_accounting_reports.financial_reports', function (require) {

    var FinancialReports = require('dynamic_accounts_report.financial_reports');

    FinancialReports.include({
        load_data: function (initial_render = true) {
            $('div.o_action_manager').css('overflow-y', 'auto');
            return this._super.apply(this, arguments);
        }
    });

});