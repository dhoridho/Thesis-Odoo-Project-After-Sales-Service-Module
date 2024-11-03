odoo.define('awesome_theme_pro.web_client', function(require) {
    "use strict";

    var WebClient = require('web.WebClient');
    var core = require('web.core');
    var session = require('web.session');
    var AwesomeVerticalMenu = require('awesome_theme_pro.vertical_menu')
    var BackendUserSetting = require('awesome_theme_pro.backend_setting')
    var DebugManager = require('web.DebugManager');
    var localStorage = require('web.local_storage');

    var AwesomeHeader = require('awesome_theme_pro.header')
    var AwesomeFooter = require('awesome_theme_pro.footer')
    var config = require('web.config');
    var dom = require('web.dom');
    var KeyboardNavigationMixin = require('web.KeyboardNavigationMixin');
    var utils = require('web.utils');

    const { ComponentWrapper } = require('web.OwlCompatibility');

    var _t = core._t;

    WebClient.include({

        custom_events: _.extend({}, WebClient.prototype.custom_events, {}),

        user_setting: {},

        init: function() {
            this._super.apply(this, arguments);
            // save the user setting
            this.user_setting = BackendUserSetting || {};
            this.set('title_part', { "zopenerp": this.user_setting.window_default_title || "Awesome Odoo" });
        },

        /**
         * check use has group
         */
        has_group: function(xml_id) {
            return this.user_groups[xml_id] || false
        },

        get_user_group_ids: function() {
            return this.user_group_ids;
        },

        /**
         * check user has any group or assigness
         * @param {*} group_ids 
         * @param {*} assignee_ids 
         * @returns 
         */
        has_any_group_or_assignee: function(group_ids, assignee_ids) {

            if ((!group_ids || group_ids.length == 0) &&
                (!assignee_ids || assignee_ids.length == 0)) {
                return true;
            }

            var self = this;
            var index = _.findIndex(group_ids, function(group_id) {
                return _.contains(self.user_group_ids, group_id);
            })

            if (index != -1) {
                return true;
            }

            if (_.contains(assignee_ids, this.user_id)) {
                return true;
            }

            return false;
        },


        /**
         * @override
         */
        start: function() {

            // update setting
            this.update_setting();

            KeyboardNavigationMixin.start.call(this);

            var self = this;

            core.bus.on('hide_portal_content', this, function() {
                self.$('.awesome_search_bar > div').detach()
                self.$('.awesome_switcher_box > div').detach()
                self.$('.awesome_pager_box > div').detach()
            })

            // we add the o_touch_device css class to allow CSS to target touch
            // devices.  This is only for styling purpose, if you need javascript
            // specific behaviour for touch device, just use the config object
            // exported by web.config
            this.$el.toggleClass('o_touch_device', config.device.touch);
            this.on("change:title_part", this, this._title_changed);
            this._title_changed();

            var state = $.bbq.getState();

            // If not set on the url, retrieve cids from the local storage
            // of from the default company on the user
            var current_company_id = session.user_companies.current_company[0]
            if (!state.cids) {
                state.cids = utils.get_cookie('cids') !== null ? utils.get_cookie('cids') : String(current_company_id);
            }

            // If a key appears several times in the hash, it is available in the
            // bbq state as an array containing all occurrences of that key
            const cids = Array.isArray(state.cids) ? state.cids[0] : state.cids;
            let stateCompanyIDS = cids.split(',').map(cid => parseInt(cid, 10));
            var userCompanyIDS = _.map(session.user_companies.allowed_companies, function(company) { return company[0] });

            // Check that the user has access to all the companies
            if (!_.isEmpty(_.difference(stateCompanyIDS, userCompanyIDS))) {
                state.cids = String(current_company_id);
                stateCompanyIDS = [current_company_id]
            }

            // Update the user context with this configuration
            session.user_context.allowed_company_ids = stateCompanyIDS;
            $.bbq.pushState(state);

            // Update favicon
            $("link[type='image/x-icon']").attr('href', '/web/image/res.company/' + String(stateCompanyIDS[0]) + '/favicon/')

            return session.is_bound
                .then(function() {

                    var group_infos = session.group_infos

                    self.user_groups = group_infos.groups
                    self.user_group_ids = group_infos.group_ids
                    self.user_id = group_infos.user_id

                    self.$el.toggleClass('o_rtl', _t.database.parameters.direction === "rtl");
                    self.bind_events();
                    return Promise.all([
                        self.instanciate_header_widget(), // set header here
                        self.set_action_manager(),
                        self.instanciate_footer_widget(),
                        self.set_loading()
                    ]);
                }).then(function() {
                    if (session.session_is_valid()) {
                        // monitor doc click
                        self._bind_doc_click();
                        // show application
                        return self.show_application();
                    } else {
                        // database manager needs the webclient to keep going even
                        // though it has no valid session
                        return Promise.resolve();
                    }
                });
        },

        is_control_pannel_need_footer: function() {
            return this.user_setting.settings.control_panel_mode != 'mode3'
        },

        instanciate_footer_widget: function() {
            if (this.is_control_pannel_need_footer()) {
                var self = this
                var fragment = document.createDocumentFragment();
                this.footer = new ComponentWrapper(this, AwesomeFooter);
                return this.footer.mount(fragment, { position: 'last-child' }).then(function() {
                    // here will call the on_attach_call_back
                    dom.append(self.$el, fragment, {
                        in_DOM: true,
                        callbacks: [{ widget: self.footer }],
                    });
                });
            }
        },

        /**
         * ignore if horizon mode
         */
        instanciate_header_widget: function() {
            var self = this
            this.header = new AwesomeHeader(this)
            var fragment = document.createDocumentFragment();
            return this.header.appendTo(fragment).then(function() {
                // here will call the on_attach_call_back
                dom.prepend(self.$el, fragment, {
                    in_DOM: true,
                    callbacks: [{ widget: self.header }],
                });
            });
        },

        /**
         * set the user setting
         */
        update_setting: function() {

            // update the style txt 
            this._update_style();

            // set the app nme
            if (!this.user_setting.settings.show_app_name) {
                $('body').addClass('hide_awesome_app_name')
            }

            // set the layout mode
            var layout_mode = this.user_setting.settings.layout_mode
            if (layout_mode) {
                $('body').addClass(layout_mode)
            }

            // set the button style
            var button_style = this.user_setting.settings.button_style
            if (button_style) {
                $('body').addClass(button_style)
            }

            // set theme menu mode from local storage
            var awesome_menu_mode = localStorage.getItem('awesome_menu_mode')
            if (awesome_menu_mode) {
                $('body').removeClass('navigation-toggle-two');
                $('body').removeClass('navigation-toggle-one');
                $('body').removeClass('navigation-toggle-none');
                $('body').addClass(awesome_menu_mode);
            }

            //  set current theme mode
            if (this.user_setting) {
                var cur_mode_id = this.user_setting.cur_mode_id
                var theme_modes = this.user_setting.theme_modes
                var cur_mode = _.find(theme_modes, function(theme_mode) {
                    return theme_mode.id == cur_mode_id;
                })
                _.each(theme_modes, function(tmp_mode) {
                    $('body').removeClass(tmp_mode.name)
                })
                $('body').addClass(cur_mode.name)
            }

            // set the rtl mode
            if (this.user_setting.settings.rtl_mode) {
                $('body').addClass('rtl_mode')
            }
        },

        _bind_doc_click: function() {
            var $body = $('body')
            $(document).on("click", "*", function(event) {
                var width = $(window).width();
                if (!$(event.target).is($(".navigation, .navigation *, .navigation-toggler *")) &&
                    ($body.hasClass("navigation-toggle-one") || width < 1200)) {
                    $body.removeClass("navigation-show");
                }
            });
        },

        current_action_updated: function(action, controller) {
            // this._super.apply(this, arguments);
            var debugManager = _.find(this.header.systray_menu.widgets, function(item) {
                return item instanceof DebugManager;
            });
            if (debugManager) {
                debugManager.update('action', action, controller && controller.widget);
            }
        },

        createOverlay: function() {
            var $body = $('body')
            if ($(".awesome_overlay").length < 1) {
                $body.addClass("no-scroll").append('<div class="awesome_overlay"></div>')
            }
            $(".awesome_overlay").addClass("show")
        },

        removeOverlay: function() {
            var $body = $('body')
            $body.removeClass("no-scroll");
            $(".awesome_overlay").remove()
        },

        /**
         * update the style txt
         */
        _update_style: function() {
            var $body = $('body')
            if (this.user_setting.style_txt) {
                var style_id = 'awesome_theme_pro_style_id';
                var styleText = this.user_setting.style_txt
                var style = document.getElementById(style_id);
                if (style.styleSheet) {
                    style.setAttribute('type', 'text/css');
                    style.styleSheet.cssText = styleText;
                } else {
                    style.innerHTML = styleText;
                }
                style && $body[0].removeChild(style);
                $body[0].appendChild(style);
            }

            if (this.user_setting.mode_style_css) {
                var style_id = 'awesome_theme_mode_style_id';
                var styleText = this.user_setting.mode_style_css
                var style = document.getElementById(style_id);
                if (style.styleSheet) {
                    style.setAttribute('type', 'text/css');
                    style.styleSheet.cssText = styleText;
                } else {
                    style.innerHTML = styleText;
                }
                style && $body[0].removeChild(style);
                $body[0].appendChild(style);
            }
        },

        on_hashchange: function(event) {

            if (this._ignore_hashchange) {
                this._ignore_hashchange = false;
                return Promise.resolve();
            }

            var self = this;
            return this.clear_uncommitted_changes().then(function() {
                var stringstate = $.bbq.getState(false);
                if (!_.isEqual(self._current_state, stringstate)) {
                    var state = $.bbq.getState(true);
                    if (state.action || (state.model && (state.view_type || state.id))) {
                        // load the action here
                        return self.menu_dp.add(self.action_manager.loadState(state, !!self._current_state)).then(function() {
                            if (state.menu_id) {
                                if (state.menu_id != self.menu.current_menu_id) {
                                    self.menu.change_menu_item(state.menu_id, true)
                                }
                            } else {
                                var action = self.action_manager.getCurrentAction();
                                if (action) {
                                    var menu_id = self.menu.action_id_to_primary_menu_id(action.id);
                                    if (state.menu_id != self.menu.current_menu_id) {
                                        self.menu.change_menu_item(menu_id, true)
                                    }
                                }
                            }
                        });
                    } else if (state.menu_id) {
                        var action_id = self.menu.menu_id_to_action_id(state.menu_id);
                        return self.menu_dp.add(self.do_action(action_id, { clear_breadcrumbs: true })).then(
                            function() {
                                self.menu.change_menu_item(state.menu_id, true)
                            });
                    } else {
                        self.menu.openFirstApp();
                    }
                }
                self._current_state = stringstate;
            }, function() {
                if (event) {
                    self._ignore_hashchange = true;
                    window.location = event.originalEvent.oldURL;
                }
            });
        },

        show_application: function() {
            var self = this;

            this.set_title();
            return this.menu_dp.add(this.instanciate_menu_widgets()).then(function() {

                // notify the systemtray menu, maybe there i a bug of odoo
                self.header.systray_menu.on_attach_callback();

                // show tab
                self.action_manager.show_awesome_tab();

                // bind has change method
                $(window).bind('hashchange', self.on_hashchange);

                // If the url's state is empty, we execute the user's home action if there is one (we
                // show the first app if not) 
                var state = $.bbq.getState(true);
                if (_.keys(state).length === 1 && _.keys(state)[0] === "cids") {
                    return self.menu_dp.add(self._rpc({
                            model: 'res.users',
                            method: 'read',
                            args: [session.uid, ["action_id"]],
                        }))
                        .then(function(result) {
                            var data = result[0];
                            if (data.action_id) {
                                return self.do_action(data.action_id[0]).then(function() {
                                    self.menu.change_action_item(data.action_id[0], true);
                                });
                            } else {
                                self.menu.openFirstApp();
                            }
                        });
                } else {
                    return self.on_hashchange();
                }
            });
        },

        /**
         * use AwesomeVerticalMenu to replace menu
         */
        instanciate_menu_widgets: function() {
            var self = this;
            var proms = [];
            return this.load_menus().then(function(menuData) {
                self.menu_data = menuData;
                // Here, we instanciate every menu widgets and we immediately append them into dummy
                // document fragments, so that their `start` method are executed before inserting them
                // into the DOM.
                if (self.menu) {
                    self.menu.destroy();
                }
                self.menu = new AwesomeVerticalMenu(self, menuData, self.user_setting);
                // append the vertical menu to the side bar area
                proms.push(self.menu.prependTo(self.$el));
                return Promise.all(proms);
            });
        },

        _openMenu: function(action, options) {
            action["menu_click"] = true;
            return this.do_action(action, options);
        },
    });

    return WebClient;
});