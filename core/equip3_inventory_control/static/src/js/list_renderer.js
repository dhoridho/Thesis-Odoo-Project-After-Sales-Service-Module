odoo.define("equip3_inventory_control.ListRenderer", function (require) {
    "use strict";

    var ListRenderer = require("web.ListRenderer");
    var core = require("web.core");
    var Session = require("web.session");

    ListRenderer.include({
        start: function () {
            var result = this._super.apply(this, arguments);
            if (
                this.state !== undefined &&
                this.state.model === "stock.inventory.line"
            ) {
                core.bus.on("barcode_scanned", this, this._onInventoryBarcodeScanned);
            }
            return result;
        },

        destroy: function () {
            core.bus.off("barcode_scanned", this, this._onInventoryBarcodeScanned);
            this._super();
        },

        _onInventoryBarcodeScanned: function (barcode) {
            var self = this;
            if (self.state !== undefined && 
                self.state.context !== undefined &&
                self.state.context.active_ids !== undefined &&
                self.getParent().reload !== undefined) {
                Session.rpc("/equip3_inventory_control/scan_add_product_inventory", {
                    barcode: barcode,
                    vals: self.state.context,
                }).then(function (result) {
                    if (result.success) {
                        self.do_notify(result.success);
                        self.getParent().reload();
                    } else if (result.warning) {
                        self.do_warn(result.warning);
                    }
                });
            }
        },
    });
});
