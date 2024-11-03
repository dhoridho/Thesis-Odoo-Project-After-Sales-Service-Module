odoo.define("equip3_pos_general.backend_views", function (require) {
    "use strict";

    var KanbanController = require("web.KanbanController");
    var ListController = require("web.ListController");
    var FormController = require("web.FormController");
    var core = require('web.core');
    var _t = core._t;

    var includeDict = {
        renderButtons: function () {
            this._super.apply(this, arguments);
            var self = this
            if (this.modelName === "pos.config" && this.$buttons) {
                this.$buttons
                    .find(".o_button_remote_session_pos")
                    .on("click", function () {
                        self.do_action(
                            {
                                name: _t('Remote sessions'),
                                res_model: 'pos.remote.session',
                                type: 'ir.actions.act_window',
                                view_type: 'form',
                                view_mode: 'form',
                                views: [[false, 'form']],
                                target: 'new',
                            }
                        );
                    });
            }
        },
    };

    KanbanController.include(includeDict);
    FormController.include(includeDict);
});
