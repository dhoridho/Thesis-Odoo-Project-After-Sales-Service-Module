odoo.define('equip3_accounting_masterdata.list_controller', function (require) {
    "use strict";

    var ListController = require('web.ListController');
    var rpc = require('web.rpc');

    ListController.include({
        renderButtons: function($node) {
            this._super.apply(this, arguments);
            console.log("renderButtons function is called");
            if (this.$buttons && this.modelName === 'approval.matrix.accounting') {
                var createButton = this.$buttons.find('.o_list_button_add');
                rpc.query({
                    model: 'res.users',
                    method: 'has_group',
                    args: ['account.group_account_user'],
                }).then(function(has_group){
                    console.log("RPC query is completed"); // This will log when the RPC query is completed
                    if(!has_group){
                        console.log("User is not in the group, hiding the button"); // This will log when the user is not in the group
                        createButton.hide();
                    }
                });
            }
        },
    });
});