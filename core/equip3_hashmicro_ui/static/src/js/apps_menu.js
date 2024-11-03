odoo.define('equip3_hashmicro_ui.AppsMenu', function (require) {
    "use strict";

    var AppsMenu = require('web.AppsMenu');
    var session = require('web.session');
    var rpc = require('web.rpc');

    var userTheme;
    rpc.query({
        model: 'res.users',
        method: 'search_read',
        domain: [['id', '=', session.uid]],
        fields: ['equip_theme_color']
    }).then(function (result) {
        userTheme = result.length ? result[0].equip_theme_color : 'black';
    });

    AppsMenu.include({
        init: function (parent, menuData) {
            this._super.apply(this, arguments);
            this.menuCategories;
            this.userTheme = userTheme;
            this._apps = _.map(menuData.children, function (appMenuData) {
				return {
					actionID: parseInt(appMenuData.action.split(',')[1]),
                    complete_name: appMenuData.complete_name,
					menuID: appMenuData.id,
					name: appMenuData.name,
					xmlID: appMenuData.xmlid,
					parent: appMenuData.parent_id,
					children: appMenuData.children,
					appdata: appMenuData,
				};
			});
        },
        
        start: function () {
            var self = this;
            var categoriesProm = this._rpc({
                model: 'ir.ui.menu.category',
                method: 'search_read',
                args: [[], ['id', 'name', 'color', 'sequence']]
            }).then(function(categories) {
                self.menuCategories = {}
                $.each(categories, function(index, category){
                    self.menuCategories[category.id] = category;
                });
            });
            return Promise.all([this._super.apply(this, arguments),  categoriesProm]).then(function(){
                $('.parent_menu_select').find("option:selected").change();
            });
        },

    });
    return AppsMenu;
});
