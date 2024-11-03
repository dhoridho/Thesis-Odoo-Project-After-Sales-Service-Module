odoo.define('equip3_hashmicro_ui.FavoriteMenu', function (require) {
    "use strict";

    const FavoriteMenu = require('web.FavoriteMenu');
    class equipFavoriteMenu extends FavoriteMenu {
        get title() {
            return this.env._t("Saved Filters");
        }
    }
    return equipFavoriteMenu;
});
