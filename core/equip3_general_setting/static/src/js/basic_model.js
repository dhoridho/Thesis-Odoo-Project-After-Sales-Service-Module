odoo.define('equip3_general_setting.basic_model', function(require){
    "use strict";

    var BasicModel = require('web.BasicModel');
    var session = require('web.session');

    BasicModel.include({
        _getEvalContext: function (element, forDomain) {
            var evalContext = this._super.apply(this, arguments);

            let current_branch_id;
            if (session.user_context.allowed_branch_ids) {
                current_branch_id = session.user_context.allowed_branch_ids[0];
            } else {
                current_branch_id = session.user_branches ?
                    session.user_branches.current_branch[0] :
                    false;
            }
            evalContext.current_branch_id = current_branch_id;
            return evalContext;
        }
    });
    return BasicModel;
})