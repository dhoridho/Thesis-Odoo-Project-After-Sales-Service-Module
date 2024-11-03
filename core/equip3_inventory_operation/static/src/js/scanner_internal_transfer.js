odoo.define('equip3_inventory_operation.InternalTransferBarcodeScanner', function(require){
    "use strict";

    var FormRenderer = require("web.FormRenderer");
    var FormController = require("web.FormController");
    var FormView = require("web.FormView");

    var core = require("web.core");
    var viewRegistry = require('web.view_registry');

    var BarcodeFormRenderer = FormRenderer.extend({
        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                core.bus.on("barcode_scanned", self, self._onBarcodeScanned);
            });
        },

        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                // Add 
                // `<a type="button" id="test_trigger_scan" class="btn btn-primary oe_edit_only" data-barcode="1243453">Test Trigger Scan</a>`
                // to your form view to test trigger scan from device.
                var $testTriggerScanButton = self.$el.find('#test_trigger_scan');
                if ($testTriggerScanButton.length){
                    this.testBarcode = $testTriggerScanButton.attr('data-barcode');
                    $testTriggerScanButton.on('click', self, self._onTestTriggerScanClicked.bind(self));
                }
            });
        },

        destroy: function () {
            core.bus.off("barcode_scanned", this, this._onBarcodeScanned);
            this._super();
        },

        _onBarcodeScanned: function(barcode){
            this.trigger_up('field_changed', {
                dataPointID: this.allFieldWidgets[this.state.id][0].dataPointID,
                changes: {sh_it_barcode_mobile: barcode}
            });

            if (this.state.data && this.state.data.sh_stock_bm_is_cont_scan === 'True'){
                this.trigger_up('field_changed', {
                    dataPointID: this.allFieldWidgets[this.state.id][0].dataPointID,
                    changes: {sh_it_barcode_mobile: ""}
                });
            }
        },

        _onTestTriggerScanClicked: function(ev){
            core.bus.trigger('barcode_scanned', this.testBarcode);
        }
    });

    var BarcodeFormController = FormController.extend({
        _barcodeScanned: function (barcode, target) {
            var $barcodeMobile = this.renderer.$el.find('input[name="sh_it_barcode_mobile"]');
            if ($barcodeMobile.length){
                var $barcodeInput = $();
                for (let i=0; i < $barcodeMobile.length; i++){
                    let $input = $($barcodeMobile[i]);
                    if (!$input.closest('.o_invisible_modifier').length){
                        $barcodeInput = $input;
                        break;
                    }
                }
                if ($barcodeInput.length){
                    target = $barcodeInput[0];
                }
            }
            return this._super(barcode, target);
        }
    });

    var BarcodeFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Renderer: BarcodeFormRenderer,
            Controller: BarcodeFormController,
        }),
    });
    
    viewRegistry.add('internal_transfer_barcode_scanner', BarcodeFormView);

    return {
        BarcodeFormRenderer: BarcodeFormRenderer,
        BarcodeFormController: BarcodeFormController,
        BarcodeFormView: BarcodeFormView
    }
});