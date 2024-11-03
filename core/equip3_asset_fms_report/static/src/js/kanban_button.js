odoo.define('equip3_asset_fms_report.kanban_button', function(require) {
    "use strict";

    var KanbanController = require('web.KanbanController');
    var core = require('web.core');

    var _t = core._t;

    var includeDict = {
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            if (this.modelName === "forecast.hour.meter.maintenance") {
                var self = this;
                var createButton = this.$buttons.find('.o-kanban-button-new');
                createButton.before('<button class="btn btn-primary o_list_button_print">Print Excel</button>');

                // Menambahkan jarak antara tombol "Create" dan "Print Excel"
                var printButton = this.$buttons.find('.o_list_button_print');
                printButton.css('margin-right', '3px');

                this.$buttons.find('.o-kanban-button-new').hide();
                this.$buttons.on('click', '.o_list_button_print', function () {
                    self._onPrintButtonClick();
                });
            }
        },
        _onPrintButtonClick: function () {
            // console.log('Button "Print List Kanban" clicked.');
            window.location.href = '/asset_report/forecast_excel_report';
        },
    };
    KanbanController.include(includeDict);
});