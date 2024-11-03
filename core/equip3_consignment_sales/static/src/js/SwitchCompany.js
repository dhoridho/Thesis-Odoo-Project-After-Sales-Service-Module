odoo.define('equip3_consignment_sales.HideMenuSection', function (require) {
    "use strict";

    var SwitchCompanyMenu = require('web.SwitchCompanyMenu');
    var session = require('web.session');
    var ajax = require('web.ajax');
    var core = require('web.core');

    var _t = core._t;

    SwitchCompanyMenu.include({
        /**
         * Customize the default _onSwitchCompanyClick method.
         *
         * @private
         * @param {Event} ev - The click event.
         */
        _onSwitchCompanyClick: function (ev) {
            // console.log("========= SwitchCompany ========");
            if (session.user_context.allowed_company_ids && session.user_context.allowed_company_ids.length > 0) {
                ev.preventDefault();
                ev.stopPropagation();

                var dropdownItem = $(ev.currentTarget).parent();
                var companyID = dropdownItem.data('company-id');
                ajax.jsonRpc("/switch/user/company", 'call', {
                    'company_id': companyID,
                });
            }
            this._super.apply(this, arguments);
        },
    });
});
