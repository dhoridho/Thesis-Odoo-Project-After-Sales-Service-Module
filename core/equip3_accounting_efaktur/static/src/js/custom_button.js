odoo.define('equip3_accounting_efaktur.custom_button', function (require){
    "use strict";

    var core = require('web.core');
    var ListView = require('web.ListView');
    var ListController = require('web.ListController');
    var rpc = require('web.rpc');

    var IncludeListView = {
        renderButtons: function() {
            this._super.apply(this, arguments);
            if (this.$buttons) {
                    var summary_apply_leave_btn = this.$buttons.find('button.o_nsfp_registration');

                    summary_apply_leave_btn.on('click', this.proxy('nsfp_registration'))
                }


                        },

        nsfp_registration: function() {

            var self = this;
            var action = {
                type: "ir.actions.act_window",
                name: "NSFP Registration",
                res_model: "nsfp.registration.wizard",
                views: [[false, 'form']],
                // context:{'default_sj_type':this.initialState.context.default_sj_type},
                target: 'new',
                view_mode: 'form'
            };
            return this.do_action(action);


        }
    };
    ListController.include(IncludeListView);
});