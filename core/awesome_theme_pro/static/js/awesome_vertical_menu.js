odoo.define('awesome_theme_pro.vertical_menu', function(require) {
    "use strict";

    var core = require('web.core');
    var Widget = require('web.Widget');
    var UserProfile = require('awesome_theme_pro.UserProfile');
    var AwesomeAppBoard = require('awesome_theme_pro.app_board')
    var config = require('web.config')

    var $body = $("body");
    var $window = $(window);

    var AwsomeVerticalMenu = Widget.extend({

        template: 'awesome_theme_pro.vertical_menu',
        current_menu_id: undefined,
        current_primary_menu: undefined,
        app_board: undefined,

        events: {
            'click .navigation-menu-group ul li>a': '_onMenuItemClick',
            'click [data-nav-target]': '_onAppNameClicked',
            "mouseenter .awesome_nav_bar_app_item": "_mouse_enter_nav_app_item",
            "mouseleave": "_mouse_leave_navigation"
        },

        custom_events: _.extend({}, Widget.prototype.custom_events, {
            'awesome_favorite_app_dropped': '_onAppDropped',
            'awesome_update_favorite': '_updateFavorites'
        }),

        getApps: function() {
            return this._apps;
        },

        _onAppDropped: function(event) {
            var $dropedEl = $(event.data.el)

            var menuID = $dropedEl.data('menu-id')
            var app = _.find(this._apps, function(tmpApp) {
                return tmpApp.menuID == menuID
            })
            if (app) {
                var $app = this.$('.navigation-menu-tab-body [data-menu-id="' + menuID + '"]').not($dropedEl)
                if ($app) {
                    $app.remove()
                }
            }
            this._updateFavorites()
        },

        getCurrentPrimaryMenu: function() {
            return this.current_primary_menu;
        },

        init: function(parent, menu_data, user_setting) {
            this._super.apply(this, arguments);

            this.$menu_sections = {};
            this.menu_data = menu_data;
            this.user_setting = user_setting || {}

            this._apps = _.map(this.menu_data.children, function(appMenuData) {
                return {
                    actionID: parseInt(appMenuData.action.split(',')[1]),
                    menuID: appMenuData.id,
                    name: appMenuData.name,
                    xmlID: appMenuData.xmlid,
                    web_icon_data: appMenuData.web_icon_data
                };
            });

            // hide the side bar 
            core.bus.on('click', this, function(event) {
                if (!$(event.target).is($(".navigation, .navigation *, .navigation-toggler *")) &&
                    $body.hasClass("navigation-toggle-one")) {
                    $body.removeClass("navigation-show")
                }
            });

            // change menu item accored the state chagne
            core.bus.on('change_menu_item', this, this.change_menu_item);
            core.bus.on('change_action_item', this, this.change_action_item);
            core.bus.on('open_first_leaf_app', this, this._open_first_leaf_app);
        },

        start: function() {
            var self = this
            return this._super.apply(this, arguments).then(function() {

                // place the user profile
                self.userProfile = new UserProfile(self)
                self.userProfile.appendTo(self.$(".navigation-menu-tab-header"))

                // add the sub item arrow
                self.$(".navigation-menu-body ul li a").each(function() {
                    var item = $(this);
                    if (item.next("ul").length) {
                        item.append('<i class="sub-menu-arrow fa fa-angle-down"></i>')
                    }
                });

                self.$(".navigation-menu-body ul li.open > a > .sub-menu-arrow")
                    .removeClass("fa fa-angle-down")
                    .addClass("fa fa-angle-up").addClass("rotate-in")

                // just show when above 992
                if (992 <= $window.width()) {
                    self.$(".navigation-menu-body").niceScroll()
                }

                self.$('[data-toggle="tooltip"]').tooltip({
                    container: "body"
                })

                self._initMenuBoard();
            });
        },

        _open_first_leaf_app: function(menu_id) {
            var app = _.find(this.menu_data.children, function(tmp_data) {
                return tmp_data.id == menu_id
            })
            this.openFirsetLeafApp(app);
        },

        // data-nav-target
        _onAppNameClicked: function(event) {
            event.preventDefault();
            var item = $(event.currentTarget)
            this._openApp(item)
        },

        _onMenuItemClick: function(event) {
            event.preventDefault()
            var click_link = $(event.currentTarget)
            if (click_link.next("ul").length == 0) {
                core.bus.trigger('awesome_menu_item_clicked')
            }
            this._onLinkClicked(click_link)
        },

        _onLinkClicked: function(click_link) {
            // deal the ui
            if (click_link.next("ul").length) {
                var arrow = click_link.find(".sub-menu-arrow");
                if (arrow.hasClass("fa-angle-down")) {
                    setTimeout(function() {
                        arrow.removeClass("fa-angle-down").addClass("fa fa-angle-up")
                    }, 200)
                } else {
                    arrow.removeClass("fa-angle-up").addClass("fa fa-angle-down");
                }
                arrow.toggleClass("rotate-in")
                click_link.next("ul").toggle(200)

                click_link.parent("li").siblings().find("ul").not(click_link.parent("li").find("ul")).slideUp(200)
                click_link.next("ul").find("li ul").slideUp(200);

                // update sub arrows
                var arrows = click_link.next("ul").find("li>a").find(".sub-menu-arrow")
                arrows.removeClass("fa-angle-up").addClass("fa-angle-down").removeClass("rotate-in")

                // update next block arrows
                arrows = click_link.parent("li").siblings().not(click_link.parent("li").find("ul")).find(">a").find(".sub-menu-arrow")
                arrows.removeClass("fa-angle-up").addClass("fa-angle-down").removeClass("rotate-in")

                var $body = $("body");
                var $window = $(window);
                if (!$body.hasClass("horizontal-side-menu") && 1200 <= $window.width()) {
                    setTimeout(function() {
                        self.$(".navigation-menu-body").getNiceScroll().resize()
                    }, 300)
                }
            } else {
                // trigger the action
                var menu_id = click_link.data("menu")
                this.current_menu_id = menu_id
                this.$('.navigation-menu-group a').removeClass('active')
                click_link.addClass('active')
                    // trigger menu click action
                var action_id = click_link.data('action-id');
                if (action_id) {
                    this._trigger_menu_clicked(menu_id, action_id);
                }
            }
        },

        // check whether the action id is in the subtree
        _action_id_in_subtree: function(root, action_id) {
            // action_id can be a string or an integer
            if (root.action && root.action.split(',')[1] === String(action_id)) {
                return true;
            }
            var found;
            for (var i = 0; i < root.children.length && !found; i++) {
                found = this._action_id_in_subtree(root.children[i], action_id);
            }
            return found;
        },

        /**
         * get app data
         * @param {*} menu_id 
         */
        _get_app_data: function(menu_id) {
            var app = undefined
            for (var i = 0; i < this.menu_data.children.length; i++) {
                if (this.menu_data.children[i].id == menu_id) {
                    app = this.menu_data.children[i]
                    break;
                }
            }
            return app
        },

        openFirstApp: function() {
            if (!this.menu_data.children ||
                this.menu_data.children.length == 0) {
                return
            }
            var firstApp = this.menu_data.children[0]
            if (!firstApp.children || firstApp.children.length == 0) {
                $('body').addClass('no-sub-menu')
                this._open_menu_section(firstApp.id);
                var action_id = firstApp.action.split(',')[1];
                this._trigger_menu_clicked(firstApp.id, action_id);
                this.current_menu_id = firstApp.id;
            } else {
                $('body').removeClass('no-sub-menu')
                var firstLeafApp = this.getFirstLeafApp(firstApp)
                if (firstLeafApp) {
                    this.change_menu_item(firstLeafApp.id, false, firstLeafApp)
                    var action_id = firstLeafApp.action.split(',')[1];
                    this._trigger_menu_clicked(firstLeafApp.id, action_id);
                    this.current_menu_id = firstLeafApp.id;
                }
            }
        },

        openFirsetLeafApp: function(secApp) {
            var targetApp = secApp;
            if (!targetApp.children || targetApp.children.length == 0) {
                $('body').addClass('no-sub-menu')
                this._open_menu_section(targetApp.id);
            } else {
                $('body').removeClass('no-sub-menu')
                targetApp = this.getFirstLeafApp(targetApp)
                this.change_menu_item(targetApp.id, false, secApp)
            }

            var action_id = targetApp.action.split(',')[1];
            this._trigger_menu_clicked(targetApp.id, action_id);
            this.current_menu_id = targetApp.id;
        },

        _trigger_menu_clicked: function(menu_id, action_id) {
            this.trigger_up('menu_clicked', {
                id: menu_id,
                action_id: action_id,
                previous_menu_id: this.current_menu_id
            });
        },

        getFirstLeafApp: function(app) {
            // if has no sub app
            var subApps = app.children || false
            if (!subApps) {
                return app
            }
            for (var i = 0; i < subApps.length; i++) {
                var tmp_app = subApps[i]
                if (!tmp_app.children || tmp_app.children.length == 0) {
                    return tmp_app
                } else {
                    return this.getFirstLeafApp(tmp_app)
                }
            }
        },

        action_id_to_primary_menu_id: function(action_id) {
            var primary_menu_id = undefined;
            var found = false;
            for (var i = 0; i < this.menu_data.children.length; i++) {
                found = this._action_id_in_subtree(this.menu_data.children[i], action_id);
                if (found) {
                    primary_menu_id = this.menu_data.children[i].id;
                    break
                }
            }
            return primary_menu_id;
        },

        menu_id_to_action_id: function(menu_id, root) {

            if (!root) {
                root = $.extend(true, {}, this.menu_data);
            }

            if (root.id === menu_id) {
                return root.action.split(',')[1];
            }
            for (var i = 0; i < root.children.length; i++) {
                var action_id = this.menu_id_to_action_id(menu_id, root.children[i]);
                if (action_id !== undefined) {
                    return action_id;
                }
            }
            return undefined;
        },

        _get_menu_data: function(menu_id) {
            return _.find(this.menu_data.children, function(data) {
                return data.id == menu_id
            });
        },

        _openApp: function(item) {
            var menu_id = parseInt(item.data("menu-id"))
            var app = _.find(this.menu_data.children, function(tmp_data) {
                return tmp_data.id == menu_id
            })
            this.openFirsetLeafApp(app);
        },

        // just change the ui
        _open_menu_section: function(menu_id) {

            if (menu_id == this.primary_menu_id) {
                return
            }

            var app = this._get_app_data(menu_id)
            var item = this.$('[data-nav-target="#' + menu_id + '"]')

            // set the app name
            this.$('.awesome_sub_menu_app_name').text(app.name).css("text-align", "left")

            var $body = $("body");
            if (app.children && app.children.length > 0) {
                $body.removeClass('no-sub-menu')

                // open the tab
                if ($body.hasClass("navigation-toggle-one")) {
                    $body.addClass("navigation-show")
                }

                // close the active item
                this.$(".navigation-menu-body .navigation-menu-group > div").removeClass("open")

                // open the active item
                var menuBody = this.$(".navigation-menu-body .navigation-menu-group #" + menu_id).addClass("open")
            } else {
                $body.addClass('no-sub-menu')
            }

            // set the status
            this.$("[data-nav-target]").removeClass("active")

            // addd the active status
            item.addClass("active")

            // add the tooltip
            item.tooltip("hide")

            // set the primary menuid to avoid renter
            this.current_primary_menu = menu_id;

            return menuBody
        },

        /**
         * change the menu item by menu id
         * @param {*} menu_id 
         */
        change_menu_item: function(menu_id, disable_click, app) {
            var action_id = this.menu_id_to_action_id(menu_id)
            if (action_id) {
                this.change_action_item(parseInt(action_id), disable_click, app)
            }
        },

        change_action_item: function(action_id, disable_click, app) {
            var app_id = undefined;
            if (app) {
                app_id = app.id;
            } else {
                app_id = this.action_id_to_primary_menu_id(action_id, app)
            }
            if (app_id) {
                // change the menu section
                var menuBody = this._open_menu_section(app_id)
                if (!menuBody) {
                    return
                }
                var link = menuBody.find('[data-action-id="' + action_id + '"]')
                    // expand parent
                var parents = link.parents('ul')
                _.each(parents, function(ul) {
                        ul = $(ul).show()
                        var prev_link = ul.prev('a')
                        if (prev_link.length) {
                            var arrow = prev_link.find(".sub-menu-arrow")
                            arrow.removeClass("fa-angle-down").addClass("fa-angle-up")
                        }
                    })
                    // disable click
                if (!disable_click) {
                    this._onLinkClicked(link)
                }
            }
        },

        _initMenuBoard: function() {
            this.app_board = new AwesomeAppBoard(this, this.menu_data)
            this.app_board.appendTo(this.$('.awesome-nav-footer'))
        },

        _isMenuExsits: function(menuID) {
            return _.find(this._apps, function(tmpApp) {
                return tmpApp.menuID == menuID
            })
        },

        _updateFavorites: function() {
            var favorites = this.$('.awesome_nav_bar_app_item')
            var datas = []
            for (var index = 0; index < favorites.length; index++) {
                var favorite = $(favorites[index]);
                datas.push({
                    'sequence': parseInt(favorite.index()),
                    'menu_id': parseInt(favorite.attr('data-menu-id'))
                })
            }
            if (datas.length > 0) {
                this._rpc({
                    "model": "awesome_theme_pro.favorite_menu",
                    "method": "update_favorite_menu",
                    "args": [datas]
                })
            }
        },

        _mouse_enter_nav_app_item: function(event) {
            var $target = $(event.currentTarget);

            // disable on mobile device
            if (config.device.size_class <= config.device.SIZES.SM) {
                return
            }

            if ($("body").hasClass('navigation-toggle-one')) {
                var menu_id = $target.data('menu-id');
                this._open_menu_section(menu_id);
            }
        },

        /**
         * mouse leave
         */
        _mouse_leave_navigation: function(event) {

            // disable on mobile device
            if (config.device.size_class <= config.device.SIZES.SM) {
                return
            }

            if ($("body").hasClass('navigation-toggle-one')) {
                $("body").removeClass('navigation-show');
            }
        }
    });

    return AwsomeVerticalMenu;
});