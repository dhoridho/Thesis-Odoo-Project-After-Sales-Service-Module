odoo.define('eqiup3_purchase_vendor_portal.VendorPortal', function (require) {
    "use strict";

    var publicWidget = require('web.public.widget');

    publicWidget.registry.vendorPortal = publicWidget.Widget.extend({
        selector: '.o_portal_search_panel',

        start: function () {
            var self = this;
            var vendor_pricelist = window.location.href.indexOf('my/vendor_pricelist') !== -1;
            if (this.$el.length && !vendor_pricelist) {
                this.$el.removeClass("ml-lg-4").addClass("ml-lg-5");
                this.$el.removeClass("col-xl-4").addClass("col-xl-5");
            }
            return this._super.apply(this, arguments);
        },
    });
});
