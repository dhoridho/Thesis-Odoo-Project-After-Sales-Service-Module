odoo.define('equip3_list_view_manager_extend.Menu', function (require) {
    "use strict";

    var Menu = require('equip3_hashmicro_ui.Menu');

    Menu.include({
        _onCloseSidebar: function(event) {
            this._super.apply(this, arguments);
            if($('.o_cp_switch_buttons_menu .active[aria-label="View list"]').length==1){
                 window.setTimeout(function(){
                    $('.o_cp_switch_buttons_menu .active[aria-label="View list"]').click()
                 },500); 
            }
        },

    });
    return Menu;
});