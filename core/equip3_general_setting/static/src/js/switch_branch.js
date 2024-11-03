odoo.define('equip3_general_setting.SwitchBranchMenu', function(require){
    "use strict";

    var switchBranchMenu = require('branch.SwitchBranchMenu');
    var session = require('web.session');

    switchBranchMenu.include({
        willStart: function(){
            console.log('>>>>>>>>>>>>>>')
            console.log(this);
            console.log(session);
            return this._super.apply(this, arguments);   
        }
    })
});