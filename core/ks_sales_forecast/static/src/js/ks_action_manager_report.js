odoo.define("ks_sales_forecast.report", function (require) {
    "use strict";

    var Ks_ActionManager = require('web.ActionManager');
    var ks_framework = require('web.framework');
    var ks_session = require('web.session');

    Ks_ActionManager.include({
        ks_executexlsxReportDownloadAction: function (action) {
            ks_framework.blockUI();
            var def = $.Deferred();
            ks_session.get_file({
                url: '/ks_sale_forecast_xlsx_report',
                data: action.data,
                success: def.resolve.bind(def),
                error: (error) => this.call('crash_manager', 'rpc_error', error),
                complete: ks_framework.unblockUI,
            });
            return def;
        },

        _handleAction: function (action, options) {
            if (action.type === 'ks.sales.forecast.report') {
                return this.ks_executexlsxReportDownloadAction(action, options);
            }
            return this._super.apply(this, arguments);
            },
     });
 });