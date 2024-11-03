odoo.define("equip3_simpleinven_scanner.FormRenderer", function (require) {
    "use strict";

    var FormRenderer = require("web.FormRenderer");
    var core = require("web.core");
    var Session = require("web.session");

    FormRenderer.include({
        /**
         * @override
         */
        start: function () {
            var result = this._super.apply(this, arguments);
            if (
                this.state !== undefined &&
                this.state.model === "stock.picking"
            ) {
                core.bus.on("barcode_scanned", this, this._onTransferBarcodeScanned);
            }
            return result;
        },

        destroy: function () {
            core.bus.off("barcode_scanned", this, this._onTransferBarcodeScanned);
            this._super();
        },

        _onTransferBarcodeScanned: function (barcode) {
            var self = this;
            $('input[name="sh_stock_barcode_mobile"]').val(barcode);
            $('input[name="sh_stock_barcode_mobile"]').change();
            setTimeout(function () {
                $('input[name="sh_stock_barcode_mobile"]').focus();
                $('input[name="sh_stock_barcode_mobile"]').blur();
            }, 1000);
        },
    });
});
