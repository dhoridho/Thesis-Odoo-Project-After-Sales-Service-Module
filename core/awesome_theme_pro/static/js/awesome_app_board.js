odoo.define('awesome_theme_pro.app_board', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    var utils = require('web.utils')
    var core = require('web.core')
    var config = require('web.config')
    var BackendUserSetting = require('awesome_theme_pro.backend_setting')
    var settings = BackendUserSetting.settings

    var NUMBER_ICONS = 6;

    var AwesomeAppboard = Widget.extend({
        template: 'awesome_theme_pro.app_board',

        apps: [],
        menuItems: [],
        focus: null,
        isComposing: false,

        events: _.extend({}, Widget.prototype.events, {
            "click .board_toggler": "_board_toggle",
            'input input.search_input': '_onMenuSearchInput',
            'click .o_app': '_onAppClicked',
            'click .o_menuitem': '_onMenuitemClick',
        }),

        init: function (parent, menuData) {
            this._super.apply(this, arguments);

            this._menuData = this._processMenuData(menuData);
            this.apps = _.where(this._menuData, { is_app: true })
            this.focus = undefined;
            this.isComposing = false;
            this.drag_drop_inited = false;
        },

        start: function () {
            var self = this;

            core.bus.on('resize', this, _.debounce(this._onResize.bind(this), 200));
            core.bus.on("keydown", this, this._onKeydown);

            return this._super.apply(this, arguments).then(function () {
                self.$board_pannel = self.$('.board-pannel')
                self.$app_container = self.$('.app_container')
                self.$menu_container = self.$('.menu_item_container')
                self.$content_container = self.$('.content_container')
                self.$search_input = self.$('.search_input')
                core.bus.on('click', this, function (event) {
                    if (!$(event.target).is($(".board-pannel, .board-pannel *"))) {
                        self.$board_pannel.addClass('d-none')
                    }
                });
            })
        },

        _onResize: function () {
            var window_width = $(window).width()
            if (window_width < 1200 && !$('body').hasClass('navigation-show')) {
                this.$board_pannel.addClass('d-none')
            }
        },

        _initDragDrop: function () {

            if (!settings.favorite_mode) {
                return
            } 

            if (this.drag_drop_inited) {
                return
            }

            this.drag_drop_inited = true;
            
            var self = this
            var left = this.$el.find('.app_container').get(0)
            var right = this.getParent().$('.navigation-menu-tab-items').get(0)

            dragula([left, right], {

                copy: function (el, source) {
                    return source == left
                },

                accepts: function (el, target) {
                    return target == right
                },

                moves: function (el, source, handle, sibling) {
                    // only when the board is visible
                    if (!self._isBoardVisible()) {
                        return false;
                    }
                    if (source == right) {
                        if ($(el).hasClass('awesome_nav_bar_app_item')) {
                            return true;
                        } else {
                            return false;
                        }
                    } else if (source == left) {
                        if ($(el).hasClass('o_app')) {
                            return true;
                        } else {
                            return false;
                        }
                    }
                    return false; // elements are always draggable by default
                },

                removeOnSpill: function () {
                    return false
                }
            }).on('cloned', function (clone, original, type) {
                if (!$(clone).hasClass('awesome_nav_bar_app_item')) {
                    var $cloneItem = $(clone)
                    var menuID = $cloneItem.data('menu-id')
                    $cloneItem.attr('data-toggle', 'tooltip')
                    $cloneItem.attr('data-placement', 'right')
                    $cloneItem.attr('data-nav-target', '#' + menuID)
                    $cloneItem.attr('href', '#')
                    $cloneItem.find('img').removeClass('o_app_icon').addClass('o-app-icon')
                    $cloneItem.find('.o_caption').addClass('awesome_app_name ')
                    $cloneItem.addClass('awesome_nav_bar_app_item')
                }
            }).on('drop', function (el, target, source, sibling) {
                if (target == right && source == left) {
                    self.trigger_up('awesome_favorite_app_dropped', { el: el });
                } else if (target == right && source == right) {
                    self.trigger_up('awesome_update_favorite');
                }
            }).on('remove', function (el, container, source) {
                if (source == right) {
                    self.trigger_up('awesome_update_favorite');
                }
            });
        },

        _board_toggle: function (event) {
            event.preventDefault();
            event.stopPropagation();

            if (!this._isBoardVisible()) {
                this.$('.board-pannel').removeClass('d-none')
                this._initDragDrop()
            } else {
                this.$('.board-pannel').addClass('d-none')
            }
        },

        _isBoardVisible: function () {
            return !this.$('.board-pannel').hasClass('d-none')
        },

        _processMenuData: function (menuData) {
            var result = [];
            utils.traversePath(menuData, function (menuItem, parents) {
                if (!menuItem.id || !menuItem.action) {
                    return;
                }
                var item = {
                    parents: _.pluck(parents.slice(1), 'name').join(' / '),
                    label: menuItem.name,
                    id: menuItem.id,
                    xmlid: menuItem.xmlid,
                    action: menuItem.action ? menuItem.action.split(',')[1] : '',
                    is_app: !menuItem.parent_id,
                    web_icon: menuItem.web_icon,
                };
                if (!menuItem.parent_id) {
                    if (menuItem.web_icon_data) {
                        item.web_icon_data =
                            ('data:image/png;base64,' + menuItem.web_icon_data).replace(/\s/g, "");
                    } else if (item.web_icon) {
                        var iconData = item.web_icon.split(',');
                        item.web_icon = {
                            class: iconData[0],
                            color: iconData[1],
                            background: iconData[2],
                        };
                    } else {
                        item.web_icon_data = '/web_enterprise/static/src/img/default_icon_app.png';
                    }
                } else {
                    item.menu_id = parents[1].id;
                }
                result.push(item);
            });
            return result;
        },

        getAppIndex: function () {
            return this.focus < this.apps.length ? this.focus : null;
        },

        _onAppClicked: function (event) {
            event.preventDefault();
            event.stopPropagation();
            var current_target = $(event.currentTarget)
            var menu_id = current_target.data('menu-id')
            core.bus.trigger('open_first_leaf_app', menu_id);
            this.$('.board-pannel').addClass('d-none')
        },

        _update: function (data) {
            var self = this;
            if (data.search || data.search == '') {
                var options = {
                    extract: function (el) {
                        return (el.parents + ' / ' + el.label).split('/').reverse().join('/');
                    }
                };
                var searchResults = fuzzy.filter(data.search, this._menuData, options);
                var results = _.map(searchResults, function (result) {
                    return self._menuData[result.index];
                });
                // get the app and the menu items
                this.apps = _.where(results, { is_app: true });
                if (data.search == '') {
                    this.menuItems = []
                } else {
                    this.menuItems = _.where(results, { is_app: false });
                }
                this.focus = results.length ? 0 : null;
            }

            if (this.focus !== null && 'focus' in data) {
                var nbrApps = this.apps.length;
                var nbrMenus = this.menuItems.length;
                // update the focus
                var newIndex = data.focus + (this.focus || 0);
                if (newIndex < 0) {
                    newIndex = nbrApps + nbrMenus - 1;
                }
                if (newIndex >= nbrApps + nbrMenus) {
                    newIndex = 0;
                }
                if (newIndex >= nbrApps && this.focus < nbrApps && data.focus > 0) {
                    if (this.focus + data.focus - (this.focus % data.focus) < nbrApps) {
                        newIndex = nbrApps - 1;
                    } else {
                        newIndex = nbrApps;
                    }
                }
                if (newIndex < nbrApps && this.focus >= nbrApps && data.focus < 0) {
                    newIndex = nbrApps - (nbrApps % NUMBER_ICONS);
                    if (newIndex === nbrApps) {
                        newIndex = nbrApps - NUMBER_ICONS;
                    }
                }
                this.focus = newIndex;
            }
            this._render();
            this._initDragDrop();
        },

        _onKeydown: function (ev) {

            // only when the board is visible
            if (!this._isBoardVisible()) {
                return false;
            }

            var isEditable = ev.target.tagName === "INPUT" ||
                ev.target.tagName === "TEXTAREA" ||
                ev.target.isContentEditable;

            // filter 
            if (isEditable && ev.target !== this.$search_input[0]) {
                return;
            }

            var elemFocused = this.focus !== null;
            var appFocused = elemFocused && this.focus < this.apps.length;
            var delta = appFocused ? NUMBER_ICONS : 1;
            var $input = this.$search_input;
            switch (ev.which) {
                case $.ui.keyCode.DOWN:
                    this._update({ focus: elemFocused ? delta : 0 });
                    ev.preventDefault();
                    break;
                case $.ui.keyCode.RIGHT:
                    if ($input.is(':focus') && $input[0].selectionEnd < $input.val().length) {
                        return;
                    }
                    this._update({ focus: elemFocused ? 1 : 0 });
                    ev.preventDefault();
                    break;
                case $.ui.keyCode.TAB:
                    if ($input.val() === "") {
                        return;
                    }
                    ev.preventDefault();
                    var f = elemFocused ? (ev.shiftKey ? -1 : 1) : 0;
                    this._update({ focus: f });
                    break;
                case $.ui.keyCode.UP:
                    this._update({ focus: elemFocused ? -delta : 0 });
                    ev.preventDefault();
                    break;
                case $.ui.keyCode.LEFT:
                    if ($input.is(':focus') && $input[0].selectionStart > 0) {
                        return;
                    }
                    this._update({ focus: elemFocused ? -1 : 0 });
                    ev.preventDefault();
                    break;
                case $.ui.keyCode.ENTER:
                    if (elemFocused) {
                        var menus = appFocused ? this.apps : this.menuItems;
                        var index = appFocused ? this.focus : this.focus - this.apps.length;
                        var menu_id = menus[index].id
                        var action_id = menus[index].action
                        core.bus.trigger('change_menu_item', menu_id);
                        this.$board_pannel.addClass('d-none')
                        this.trigger_up('menu_clicked', {
                            id: menu_id,
                            action_id: action_id
                        });
                        ev.preventDefault();
                    }
                    return;
                case $.ui.keyCode.PAGE_DOWN:
                case $.ui.keyCode.PAGE_UP:
                case 16: // Shift
                case 17: // CTRL
                case 18: // Alt
                    break;
                case $.ui.keyCode.ESCAPE:
                    // clear text on search, hide it if no content before ESC
                    // hide home menu if there is an inner action
                    this.isSearching = $input.val().length > 0;
                    $input.val("");
                    this._update({ focus: 0, search: $input.val() });
                    if (!this.isSearching) {
                        this.trigger_up('hide_app_board');
                        this._board_toggle(ev);
                    }
                    break;
                case 67: // c
                case 88: // x
                    // keep focus and selection on keyboard copy and cut
                    if (ev.ctrlKey || ev.metaKey) {
                        break;
                    }
                default:
                    if (!$input.is(':focus')) {
                        $input.focus();
                    }
            }
        },

        _onCompositionStart: function (ev) {
            this.isComposing = true;
        },

        _onCompositionEnd: function (ev) {
            this.isComposing = false;
        },

        _onMenuSearchInput: function (ev) {
            if (!ev.target.value) {
                this.isSearching = true;
            }
            this._update({ search: ev.target.value, focus: 0 });
        },

        destroy: function() {
            core.bus.off("keydown", this, this._onKeydown);
            return this._super();
        },
    
        getFocusedAppIndex: function () {
            return this.focus < this.apps.length ? this.focus : null;
        },

        getFocusedMenuIndex: function () {
            return this.focus >= this.apps.length ? this.focus - this.apps.length : null;
        },

        _render: function () {
            // need to rebind the drag drop
            this.$content_container.html(core.qweb.render('awesome_theme_pro.board_content', { widget: this }));
            var $focused = this.$content_container.find('.o_focused');
            if ($focused.length && !config.device.isMobile) {
                if (!this.isComposing) {
                    $focused.focus();
                }
            }
        },

        _onMenuitemClick: function(event) {
            event.preventDefault();

            this.$board_pannel.addClass('d-none')
            var current_target = $(event.currentTarget)
            var menu_id = current_target.data('menu-id')
            var action_id = current_target.data('action-id')
            core.bus.trigger('change_menu_item', menu_id);
            this.trigger_up('menu_clicked', {
                id: menu_id,
                action_id: action_id
            });
        }
    });

    return AwesomeAppboard;
});
