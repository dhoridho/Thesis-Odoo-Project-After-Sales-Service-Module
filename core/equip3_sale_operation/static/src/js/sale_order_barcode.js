odoo.define("equip3_sale_operation.SaleOrderBarcodeView", function (require) {
    "use strict";

    var FormRenderer = require("web.FormRenderer");
    var SaleOrderView = require("sale.SaleOrderView");
    var core = require("web.core");
    var viewRegistry = require('web.view_registry');

    var BarcodeFormRenderer = FormRenderer.extend({
        start: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                core.bus.on("barcode_scanned", self, self._onTransferBarcodeScanned);
            });
            
        },

        destroy: function () {
            core.bus.off("barcode_scanned", this, this._onTransferBarcodeScanned);
            this._super();
        },

        _onTransferBarcodeScanned: function (barcode) {
            this.trigger_up('field_changed', {
                dataPointID: this.allFieldWidgets[this.state.id][0].dataPointID,
                changes: {sh_sale_barcode_mobile: barcode}
            });

            if (this.state.data && this.state.data.sh_sale_bm_is_cont_scan === 'True'){
                this.trigger_up('field_changed', {
                    dataPointID: this.allFieldWidgets[this.state.id][0].dataPointID,
                    changes: {sh_sale_barcode_mobile: ""}
                });
            }
        }
    });

    SaleOrderView.prototype.config.Controller.include({
        _barcodeScanned: function (barcode, target) {
            var $barcodeMobile = this.renderer.$el.find('input[name="sh_sale_barcode_mobile"]');
            if ($barcodeMobile.length){
                target = $barcodeMobile[0];
            }
            return this._super(barcode, target);
        }
    });

    var BarcodeFormView = SaleOrderView.extend({
        config: _.extend({}, SaleOrderView.prototype.config, {
            Renderer: BarcodeFormRenderer
        }),
    });

    // js_class for sale.order alreadey declared from basic/sale
    // so this js inherit that instead create a new one.
    viewRegistry.add('sale_discount_form', BarcodeFormView);
    
    return {
        BarcodeFormRenderer: BarcodeFormRenderer,
        BarcodeFormView: BarcodeFormView
    }
});
