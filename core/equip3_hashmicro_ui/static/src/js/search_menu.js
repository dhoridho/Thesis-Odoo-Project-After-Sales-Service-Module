odoo.define('equip3_hashmicro_ui.SearchMenu', function (require) {"use strict";
    
    var searchMenu = require('oi_web_search.SearchMenu');
    class SearchMenu extends searchMenu {
        get icon() {
    		return "o-hm-icon o-hm-view-search";
    	}

        get title() {
            return this.env._t("Advanced Search");
        }  
    };
    return SearchMenu;
});