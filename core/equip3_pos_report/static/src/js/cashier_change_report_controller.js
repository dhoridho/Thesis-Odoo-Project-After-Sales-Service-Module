odoo.define('equip3_pos_report.CashierChangeReportController', function (require) {
"use strict";
    
    var KanbanController = require("web.KanbanController");
    var ListController = require("web.ListController");
    var FormController = require("web.FormController");
    var core = require('web.core');
    var rpc = require('web.rpc');

    var includeDict = {
        renderButtons: function () {
            var self = this;
            this._super.apply(this, arguments);
            if (this.modelName === "pos.login.history" && this.$buttons) {
                this.$buttons
                    .find(".print_CashierChangeReport")
                    .on("click", function () {

                    window.open('/get-CashierChangeReport-today');


                    });
            }

            if (this.modelName === "pos.profit.and.loss" && this.$buttons) {
                this.$buttons
                    .find(".Load_PL_POS_wizard")          
                    .on("click", function () {
                        self.do_action({
                            type: 'ir.actions.act_window',
                            res_model: 'pos.profit.loss.wizard',
                            name: 'Print Profit and Loss Report',
                            views: [[false,'form']],
                            target: 'new',
                        });
                    });
            }
        },
    };

    KanbanController.include(includeDict);
    ListController.include(includeDict);
    FormController.include(includeDict);

});


