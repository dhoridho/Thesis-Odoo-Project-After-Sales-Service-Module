odoo.define('awesome_theme_pro.UserProfile', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    var config = require('web.config');
    var framework = require('web.framework');

    var UserProfile = Widget.extend({

        template: 'awesome_theme_pro.user_profile',
        deferredInstallPrompt: undefined,

        events: _.extend({}, Widget.prototype.events, {
            'click [data-menu]': '_on_menu_item_click'
        }),

        init: function () {
            return this._super.apply(this, arguments)
        },

        start: function () {
            var self = this;
            var session = this.getSession();

            return this._super.apply(this, arguments).then(function () {

                if ("serviceWorker" in navigator) {
                    navigator.serviceWorker.register("/awesome-service-worker.js").then(function(reg) {
                        console.log("pwa service worker registered.", reg);
                    })
                }

                window.addEventListener("beforeinstallprompt", self.before_install_prompt_call_back.bind(self));

                var $avatar = self.$('.oe_topbar_avatar');
                if (!session.uid) {
                    $avatar.attr('src', $avatar.data('default-src'));
                    return Promise.resolve();
                }
                var topbar_name = session.name;
                if (config.isDebug()) {
                    topbar_name = _.str.sprintf("%s (%s)", topbar_name, session.db);
                }
                self.$('.oe_topbar_name').text(topbar_name);
                var avatar_src = session.url('/web/image', {
                    model: 'res.users',
                    field: 'image_128',
                    id: session.uid,
                });
                $avatar.attr('src', avatar_src);
            });
        },

        _on_menu_item_click: function (event) {
            event.preventDefault();
            var target = $(event.target)
            var menu = target.data('menu');
            this['_onMenu' + menu.charAt(0).toUpperCase() + menu.slice(1)]();
        },

        _onMenuAccount: function () {
            var self = this;
            this.trigger_up('clear_uncommitted_changes', {
                callback: function () {
                    self._rpc({ route: '/web/session/account' })
                        .then(function (url) {
                            framework.redirect(url);
                        })
                        .guardedCatch(function (result, ev) {
                            ev.preventDefault();
                            framework.redirect('https://accounts.hashmicro.com/account');
                        });
                },
            });
        },

        _onMenuDocumentation: function () {
            window.open('https://www.hashmicro.com/documentation/user', '_blank');
        },

        _onMenuLogout: function () {
            this.trigger_up('clear_uncommitted_changes', {
                callback: this.do_action.bind(this, 'logout'),
            });
        },

        _onMenuSettings: function () {
            var self = this;
            var session = this.getSession();
            this.trigger_up('clear_uncommitted_changes', {
                callback: function () {
                    self._rpc({
                        model: "res.users",
                        method: "action_get"
                    })
                        .then(function (result) {
                            result.res_id = session.uid;
                            self.do_action(result);
                        });
                },
            });
        },

        _onMenuSupport: function () {
            window.open('https://www.hashmicro.com/buy', '_blank');
        },

        _onMenuShortcuts: function () {
            new Dialog(this, {
                size: 'large',
                dialogClass: 'o_act_window',
                title: _t("Keyboard Shortcuts"),
                $content: $(QWeb.render("UserMenu.shortcuts"))
            }).open();
        },

        /**
         * @param {*} evt 
         */
        before_install_prompt_call_back: function (evt) {
            this.deferredInstallPrompt = evt;
            this.$(".pwa_install_button").removeClass('d-none');
        },

        /**
         * install pwa
         */
        _onMenuInstallpwa: function () {
            var self = this
            this.deferredInstallPrompt.prompt();
            this.deferredInstallPrompt.userChoice.then(function (choice) {
                if (choice.outcome === "accepted") {
                    self.$(".pwa_install_button").addClass('d-none');
                    console.log("User accepted the \"Add To Home Screen (A2HS)\"  prompt", choice);
                } else {
                    console.log("User dismissed the \"Add To Home Screen (A2HS)\"  prompt", choice);
                }
                self.deferredInstallPrompt = null;
            });
        },
    });

    return UserProfile;
});
