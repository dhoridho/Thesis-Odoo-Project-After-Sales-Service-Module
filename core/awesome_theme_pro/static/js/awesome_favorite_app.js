/**
 * extend menu to support favorite mode
 */
odoo.define('awesome_theme_pro.favorite_app', function (require) {
    "use strict";

    var Menu = require('awesome_theme_pro.vertical_menu')
    var session = require('web.session');
    var core = require('web.core')

    Menu.include({
        favorites: [],

        start: function() {
            this._super.apply(this, arguments);
            core.bus.on('reload_favorite_apps', this,  _.bind(this.reload_favorite_apps, this));
        },

        /**
         * load the favorite
         */
        willStart: function () {
            var self = this
            return this._super.apply(this, arguments).then(function () {
                self._orgin_apps = _.clone(self._apps)
                if (self.user_setting.settings.favorite_mode) {
                    return self._rpc({
                        "model": "awesome_theme_pro.favorite_menu",
                        "method": "search_read",
                        args: [[['user_id', '=', session.uid]]],
                        kwargs: { fields: ['id', 'menu_id', 'user_id', 'sequence'] }
                    }).then(function (favorites) {
                        // save the favorites
                        self.favorites = favorites
                        // store the old apps
                        // change the _apps and sort it
                        self._apps = _.filter(self._apps, function (app) {
                            var favorite = _.find(self.favorites, function (tmpFavorite) {
                                return parseInt(tmpFavorite.menu_id[0]) == app.menuID;
                            })
                            if (!favorite) return false;
                            app['sequence'] = favorite.sequence
                            return true;
                        });
                        // sort the apps
                        self._apps.sort(function (app1, app2) { return app1.sequence - app2.sequence });
                    })
                }
            })
        },

        get_favorite_apps: function () {
            return this._apps;
        },

        _re_render_apps: function() {
            var app_items = $(core.qweb.render('awesome_theme_pro.app_items', {widget: this}))
            var container = this.$('.navigation-menu-tab-body')
            container.empty()
            app_items.appendTo(container);
        },

        reload_favorite_apps: function(favorite_mode) {
            var self = this;
            if (favorite_mode) {
                // get the favorite apps
                return self._rpc({
                    "model": "awesome_theme_pro.favorite_menu",
                    "method": "search_read",
                    args: [[['user_id', '=', session.uid]]],
                    kwargs: { fields: ['id', 'menu_id', 'user_id', 'sequence'] }
                }).then(function (favorites) {
                    // save the favorites
                    self.favorites = favorites
                    // change the _apps and sort it
                    self._apps = _.filter(self._apps, function (app) {
                        var favorite = _.find(self.favorites, function (tmpFavorite) {
                            return parseInt(tmpFavorite.menu_id[0]) == app.menuID;
                        })
                        if (!favorite) return false;
                        app['sequence'] = favorite.sequence
                        return true;
                    });
                    // sort the apps
                    self._apps.sort(function (app1, app2) { return app1.sequence - app2.sequence });
                }).then(function() {
                    // re render the apps
                    self._re_render_apps();
                })
            } else {
                self._apps = self._orgin_apps;
                this._re_render_apps();
            }
        }
    });
});
