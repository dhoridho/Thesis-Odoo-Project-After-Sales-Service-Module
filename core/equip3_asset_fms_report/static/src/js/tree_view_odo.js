odoo.define('equip3_asset_fms_report.tree_view_odo_button', function (require){
    "use strict";

    var ListController = require('web.ListController');

    ListController.include({
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            var self = this;

            
            if (this.modelName === 'forecast.odo.meter.maintenance') {
                
                this.$buttons.append('<button class="btn btn-primary o_list_button_print">Print List Excel</button>');

                
                this.$buttons.on('click', '.o_list_button_print', function () {
                    self._onPrintButtonClick();
                });
            }
        },

        _onPrintButtonClick: function () {
            
            // console.log('buttton print works')
            window.location.href = '/asset_report/forecast_odo_excel_report';
        },
    });
});