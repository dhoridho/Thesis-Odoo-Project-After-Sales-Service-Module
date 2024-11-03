odoo.define('awesome_theme_pro.theme_editor', function (require) {
    "use strict";

    var Widget = require('web.Widget');
    var Customizer = require('awesome_theme_pro.customizer')

    var AwesomeThemeEdtitor = Customizer.extend({

        template: 'awesome_theme_pro.customizer_panel',
        items: [],

        /**
         * rewrite to prevent use the backend setting
         * @param {} parent 
         */
        init: function (parent, action) {
            var params = action.params
            this.params = params
            // this.company_id = params.company_id;
            this.owner = params.owner;
            this.editor_type = params.editor_type;
            this.mode_id = params.cur_mode_id;
            this.style_id = params.cur_style_id;
            this.user_setting = {
                "theme_modes": params.theme_modes,
                "settings": params.settings
            }
            this.mode_data = params.theme_modes
            return Widget.prototype.init.apply(this, arguments)
        },

        start: function () {
            var self = this;
            Widget.prototype.start.apply(this, arguments)

            // hide customizer
            $(document).on("click", "*", function (event) {
                if (!$(event.target).is($(".customizer, .customizer *"))
                    && !self._is_color_pikcer_click(event)) {
                    self.hide_side_bar()
                }
            });

            this._init_color_picker(this.$el);
            this._init_tab();

            this.$el.addClass('open')
        },

        hide_side_bar: function () {
            this.$el.removeClass('open');
            this.destroy();
        },

        _on_customizer_close_click: function (event) {
            event.preventDefault();
            event.stopPropagation();
            this.hide_side_bar();
        },

        _save_settings: function () {
            var self = this;
            var style_id = this.$('.theme_style_tab.active:visible').data('style-id')

            this._rpc({
                "model": "awesome_theme_pro.theme_setting_manager",
                "method": "save_style_data",
                "args": [style_id, this._get_cur_style_data(), this.editor_type]
            }).then(function (theme_style) {
                // update the style data
                self._replace_style_item(theme_style);
                // hide the pannel
                self.hide_side_bar();
            })
        },

        /**
         * @param {*} event 
         */
        _is_color_pikcer_click: function (event) {
            if (this.$el.is(':visible')
                && $(event.target).is($(".colorpicker-bs-popover, .colorpicker-bs-popover *"))) {
                return true
            } else {
                return false
            }
        },

        /**
         * add a new style
         * @param {*} event 
         */
        _on_add_new_style: function (event) {
            event.preventDefault();

            var mode_id = this.$("input[name='theme_mode_radio']:checked").data('mode-id');
            var style_data = this._get_setting_style_data(mode_id);
            // var owner = 'res.company, ' + this.company_id;

            var self = this;
            this._rpc({
                "model": "awesome_theme_pro.theme_style",
                "method": "add_new_style",
                "args": [mode_id, style_data, this.owner]
            }).then(function (new_style) {
                var mode = _.find(self.user_setting.theme_modes, function (tmp_mode) {
                    return tmp_mode.id == mode_id;
                })
                mode.theme_styles.push(new_style);
                self._add_new_tab(new_style);
            })
        },

        _on_cancel_btn_click: function (event) {
            event.preventDefault();
            event.stopPropagation();

            this.hide_side_bar();
        },

        /**
         * clone and create a new style from the current style
         */
        _clone_style: function (event) {

            var $target = $(event.currentTarget)
            var styleId = parseInt($target.data('style-id'));
            // var owner = 'res.company, ' + this.company_id;

            var self = this;
            var mode_id = this.$("input[name='theme_mode_radio']:checked").data('mode-id');
            this._rpc({
                "model": "awesome_theme_pro.theme_style",
                "method": "clone_style",
                "args": [styleId, this.owner]
            }).then(function (new_style) {
                var mode = _.find(self.user_setting.theme_modes, function (tmp_mode) {
                    return tmp_mode.id == mode_id;
                })
                mode.theme_styles.push(new_style);
                self._add_new_tab(new_style);
            })
        }
    });

    return AwesomeThemeEdtitor;
});
