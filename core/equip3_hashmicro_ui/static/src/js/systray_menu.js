odoo.define('equip3_hashmicro_ui.SystrayMenu', function (require) {
    "use strict";

    var SystrayMenu = require('web.SystrayMenu');
    var messagingMenu = require('mail/static/src/widgets/messaging_menu/messaging_menu.js');
    var core = require('web.core');

    SystrayMenu.include({
        start: function(){
            return this._super.apply(this, arguments).then(function(){
                core.bus.trigger('DOM_updated');
            });
        }
    });

    messagingMenu.include({
        async on_attach_callback() {
            await this._super(...arguments);
            core.bus.trigger('DOM_updated');
        }
    });

    return {
        SystrayMenu: SystrayMenu,
        messagingMenu: messagingMenu
    }
});
