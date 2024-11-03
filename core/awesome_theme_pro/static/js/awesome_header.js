odoo.define('awesome_theme_pro.header', function (require) {
    "use strict";

    const core = require('web.core')
    const SystrayMenu = require('web.SystrayMenu');
    const Widget = require('web.Widget');
    const overLay = require('awesome_theme_pro.overlay');
    const { ComponentWrapper } = require('web.OwlCompatibility');

    var localStorage = require('web.local_storage');
    var session = require('web.session');
    var config = require('web.config')

    var BackendUserSetting = require('awesome_theme_pro.backend_setting')

    var AwesomeHeader = Widget.extend({

        template: 'awesome_theme_pro.header',

        overlay: undefined,
        RESIZE_DELAY: 200,

        events: _.extend({}, Widget.prototype.events, {
            "click .navigation-toggler": "_on_toggle_click",
            "click .mobile_toggler": "_on_mobile_toggler_click",
            'click .navigation-logo img': '_onLogoClick',
        }),

        custom_events: _.extend({}, Widget.prototype.custom_events, {
            'awesome_overlay_clicked': '_on_overlay_clicked'
        }),

        init: function (parent) {
            this._super.apply(this, arguments);
            this.searchBars = {};
        },

        /**
         * toggle the vertical menu type
         * @param {} event 
         */
        _on_toggle_click: function (event) {

            event.preventDefault();
            event.stopPropagation();

            var self = this;
            var $body = $('body');

            // create overlay when the size is below 1200
            if (config.device.size_class <= config.device.SIZES.SM) {
                self.createOverlay();
                $body.addClass("navigation-show");
            } else {
                if ($body.hasClass("navigation-toggle-one")) {
                    $body.removeClass("navigation-toggle-one");
                    $body.removeClass("navigation-show");
                    $body.addClass("navigation-toggle-none");
                    localStorage.setItem('awesome_menu_mode', 'navigation-toggle-none')
                } else if ($body.hasClass("navigation-toggle-two")) {
                    // jump one to none
                    if (!$body.hasClass('no-sub-menu')) {
                        $body.removeClass("navigation-toggle-two");
                        $body.removeClass("navigation-show");
                        $body.addClass("navigation-toggle-one");
                        localStorage.setItem('awesome_menu_mode', 'navigation-toggle-one')
                    } else {
                        $body.removeClass("navigation-toggle-two");
                        $body.removeClass("navigation-show");
                        $body.addClass("navigation-toggle-none");
                        localStorage.setItem('awesome_menu_mode', 'navigation-toggle-one')
                    }
                } else if ($body.hasClass("navigation-toggle-none")) {
                    $body.removeClass("navigation-toggle-none");
                    $body.removeClass("navigation-show");
                    $body.addClass("navigation-toggle-two");
                    localStorage.setItem('awesome_menu_mode', 'navigation-toggle-two')
                } else {
                    // if nothing
                    $body.removeClass("navigation-toggle-two");
                    $body.removeClass("navigation-show");
                    $body.addClass("navigation-toggle-one");
                    localStorage.setItem('awesome_menu_mode', 'navigation-toggle-one')
                }
            }
        },

        createOverlay: function () {
            if (!this.overlay) {
                this.overlay = new overLay(this)
                var $body = $("body");
                this.overlay.appendTo($body)
            } else {
                this.overlay.show()
            }
        },

        start: async function () {
            this.systray_menu = new SystrayMenu(this);
            var systrayMenuProm = this.systray_menu.attachTo(this.$('.awesome_theme_systray'))
            core.bus.on('resize', this, _.debounce(this._onResize.bind(this), this.RESIZE_DELAY));
            this.$('.oe_logo_edit').toggleClass('oe_logo_edit_admin', session.is_superuser);
            return Promise.all([this._super.apply(this, arguments), systrayMenuProm]);
        },

        _onResize: function () {
            var window_width = $(window).width();
            if (window_width < 1200 && $('body').hasClass('navigation-show')) {
                this.createOverlay();
            }
        },

        _on_overlay_clicked: function () {
            if (this.overlay) {
                var $body = $("body");
                $body.removeClass('navigation-show')
                this.overlay.hide();
            }
        },

        _onMenuItemClicked: function () {
            if (this.overlay && this.overlay.is_visible()) {
                var $body = $("body");
                $body.removeClass('navigation-show')
                this.overlay.hide();
            }
        },

        _init_search_bar: async function (controllerID, controlPanelProps) {
            if (!controllerID) {
                return
            }
            const searchBarEl = this.el.querySelector('.awesome_search_bar');
            var tmpWrapper = new ComponentWrapper(this, SearchBar, controlPanelProps);
            tmpWrapper.mount(searchBarEl, { position: 'first-child' });
            this.searchBars[controllerID] = {
                "component": tmpWrapper,
                "isInDOM": true,
                "controlPanelProps": controlPanelProps
            }
        },

        _remove_search_bar: function (controllerID) {
            var tmp_info = this.searchBars[controllerID] || undefined
            if (tmp_info) {
                tmp_info.component.unmount();
                delete tmp_info[controllerID];
            }
        },

        _hide_search_bar: function (controllerID) {
            if (!controllerID) {
                return
            }
            var tmp_info = this.searchBars[controllerID] || undefined
            if (tmp_info) {
                // just detach the el
                $(tmp_info.component.el).detach()
                tmp_info.isInDOM = false;
            }
        },

        _show_awesome_search_bar: function (controllerID) {
            if (!controllerID) {
                return
            }
            var tmp_info = this.searchBars[controllerID] || undefined
            if (tmp_info && !tmp_info.isInDOM) {
                // just detach the el
                const searchBarEl = this.el.querySelector('.awesome_search_bar');
                $(tmp_info.component.el).appendTo($(searchBarEl))
                tmp_info.isInDOM = true;
            }
        },

        _on_mobile_toggler_click: function (event) {

            event.stopPropagation();
            event.preventDefault();

            var right_part = this.$('.header_right_part');
            if (right_part.is(':visible')) {
                right_part.addClass('d-none')
            } else {
                right_part.removeClass('d-none')
            }
        },

        _onLogoClick: function (ev) {
            ev.preventDefault();

            if (!BackendUserSetting.is_admin) {
                return
            }

            var self = this;
            this._rpc({
                model: 'res.users',
                method: 'read',
                args: [[session.uid], ['company_id']],
            }).then(function (data) {
                self._rpc({
                    route: '/web/action/load',
                    params: { action_id: 'base.action_res_company_form' },
                })
                    .then(function (result) {
                        result.res_id = data[0].company_id[0];
                        result.target = "new";
                        result.views = [[false, 'form']];
                        result.context = '{"form_view_ref": "awesome_theme_pro.awesome_view_company_pop_form"}'
                        result.flags = {
                            action_buttons: true,
                            headless: true,
                        };
                        self.do_action(result, {
                            on_close: self.update_logo.bind(self, true),
                        });
                    });
            });

            return false;
        },

        update_logo: function (reload) {
            var company = session.company_id;
            var img = session.url('/web/binary/company_logo' + '?db=' + session.db + (company ? '&company=' + company : ''));
            this.$('.navigation-logo a img').attr('src', '').attr('src', img + (reload ? "&t=" + Date.now() : ''));
            this.$('.oe_logo_edit').toggleClass('oe_logo_edit_admin', session.is_superuser);
        }
    });

    return AwesomeHeader;
});
