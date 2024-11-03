odoo.define('awesome_theme_pro.customizer', function (require) {
    "use strict";

    var SystrayMenu = require('web.SystrayMenu');
    var Widget = require('web.Widget');
    var core = require('web.core')
    var BackendUserSetting = require('awesome_theme_pro.backend_setting')
    var framework = require('web.framework');
    var config = require('web.config');
    var theme_bus = require('awesome_theme_pro.bus')

    var AwesomeCustomizer = Widget.extend({
        template: 'awesome_theme_pro.customizer',
        sequence: 0,
        items: [],
        is_company_theme_editing: false,
        is_in_action: false,
        $pannel: undefined,

        init_color: {
            'black': '#000000',
            'gray': '#888888',
            'white': '#ffffff',
            'red': 'red',
            'default': '#777777',
            'primary': '#337ab7',
            'success': '#5cb85c',
            'info': '#5bc0de',
            'warning': '#f0ad4e',
            'danger': '#d9534f'
        },

        events: _.extend({}, Widget.prototype.events, {

            "click .customizer-toggler": "_on_customizer_toggler_click",
            "click .customizer-close": "_on_customizer_close_click",
            "click .operation-toolbar .delete_style": "_on_delete_theme_style",
            "click .save-btn": "_on_save_btn_click",
            "click .cancel-btn": "_on_cancel_btn_click",
            "click .preview-btn": "_on_preview_btn_click",
            "click .reset-preview-btn": "_on_reset_preview_btn_click",
            "click .add_new_style": "_on_add_new_style",
            "click .export_style": "_export_style",
            "click .colone_style": "_clone_style",
            "click .add_sub_group": "_add_sub_group",
            "click .add_style_item": "_add_style_item",
            "click .add_item_group": "_add_item_group",
            "click .delete_item_group": "_delete_item_group",
            "click .delete_style_item": "_delete_style_item",
            "click .edit_style_item": "_edit_style_item",
            "click .sub_group_toggler": "_on_click_group_toggler",
            "click .add_new_group": "_on_add_new_group",
            "click .edit_item_var": "_on_edit_item_var",
            "click .delete_sub_group": "_on_delete_sub_group",
            "click .import_new_style": "_on_import_style",
            "click .delete_group": "_on_delete_group",
            "click .create_new_theme_mode": "_create_new_theme_mode",
            "click .change_mode_setting": "_change_mode_setting",
            "click .delete_mode": "_on_delete_mode",

            "change .theme-mode-radio": "_onchange_theme_mode_radio"
            
        }),

        init: function (parent) {
            this._super.apply(this, arguments);

            this.user_setting = BackendUserSetting;

            // keep the current mode and style
            this.mode_id = this.user_setting.cur_mode_id;
            this.style_id = this.user_setting.cur_style_id;

            this.owner = false
            this.editor_type = 'system'
        },

        start: function () {
            this._super.apply(this, arguments)
            
            // hide customizer
            this.bind_window_click(true);

            // listen teh preivew button click
            theme_bus.on('preview_creating_mode', this, this._on_creating_mode_preview)
            theme_bus.on('reset_preview_creating_mode', this, this._on_reset_mode_preview)
        },

        bind_window_click: function (enable) {
            if (enable) {
                $(document).on("click", this._on_window_click.bind(this));
            } else {
                $(document).unbind("click", this._on_window_click.bind(this))
            }
        },

        _init_customizer: function () {
            if (!this.$pannel) {
                this.$pannel = $(core.qweb.render('awesome_theme_pro.customizer_panel', {
                    "widget": this
                }));
                this.$pannel.appendTo(this.$el);

                this._init_tab();
                this._init_theme_mode();
            }
        },

        _on_window_click: function (event) {
            var self = this;

            if (this.is_in_action) {
                return
            }

            if (!$(event.target).is($(".customizer, .customizer *"))
                && !self._is_color_pikcer_click(event)) {
                if (self.is_company_theme_editing) {
                    self.$el.removeClass('open');
                } else {
                    self.$('.customizer').removeClass('open');
                }
            }
        },

        /**
         * hide side bar
         */
        hide_side_bar: function () {
            self.$('.customizer').removeClass('open');
        },

        _init_theme_mode: function () {
            var self = this;
            // init theme mode
            _.each(this.user_setting.theme_modes, function (tmp_mode) {
                $('body').removeClass(tmp_mode.name)
                if (tmp_mode.id == self.mode_id) {
                    $('body').addClass(tmp_mode.name)
                }
            })
        },

        /**
         * 
         * @param {*} event 
         */
        _is_color_pikcer_click: function (event) {
            if (this.$('.customizer').is(':visible')
                && $(event.target).is($(".colorpicker-bs-popover, .colorpicker-bs-popover *"))) {
                return true
            } else {
                return false
            }
        },

        _init_tab: function () {
            this.$(".theme-mode-radio [data-mode-id=" + this.mode_id + "]").attr("checked", "checked");
            this.$(".theme-mode-container[data-mode-id=" + this.mode_id + "]").removeClass("d-none")

            this._active_theme_style(this.style_id);
        },

        _on_customizer_toggler_click: function (event) {
            event.preventDefault();
            event.stopPropagation();
            this._init_customizer();
            this.$('.customizer').addClass('open')
        },

        _on_customizer_close_click: function (event) {
            event.preventDefault();
            event.stopPropagation();
            this.$('.customizer').removeClass('open')
        },

        _on_preview_btn_click: function (event) {
            event.preventDefault();
            event.stopPropagation();

            // preview the style
            this._inner_preview();
        },

        _on_reset_preview_btn_click: function (event) {
            event.preventDefault();
            event.stopPropagation();

            this._remove_mode_bk_flag();
            $('body').removeClass('mode_preview')
        },

        _update_cur_style: function () {

            // remove all the preview mode
            $('body').removeClass('mode_preview')
            $('body').removeClass('awesome_creating_mode')

            // update current mode
            this._update_mode();
            this._update_style();
        },

        _inner_preview: function () {
            this._update_preview_mode();
            // set true to preview
            this._update_style(true);
        },

        /**
         * delete theme style
         * @param {*} event 
         */
        _on_delete_theme_style: function (event) {
            event.stopPropagation()

            var self = this;
            var $target = $(event.currentTarget);
            var style_id = parseInt($target.data('style-id'));

            this._rpc({
                "model": "awesome_theme_pro.theme_style",
                "method": "delete_style",
                "args": [style_id]
            }).then(function () {

                // remove the nave item and tab pane
                self.$(".theme-style-nav-item[data-style-id=" + style_id + "]").remove();
                self.$(".theme-style-tab_pane[data-style-id=" + style_id + "]").remove();

                var modes = self.user_setting.theme_modes;
                for (var index = 0; index < modes.length; index++) {
                    var mode = modes[index];
                    var theme_styles = mode.theme_styles;
                    var style_index = _.findIndex(theme_styles, function (style) {
                        return style.id == style_id;
                    })
                    if (style_index != -1) {
                        theme_styles.splice(style_index, 1);
                        var prev_index = style_index - 1;
                        if (prev_index <= 0) {
                            prev_index = theme_styles.length - 1;
                        }
                        if (prev_index >= 0) {
                            var new_theme_style = theme_styles[prev_index];
                            self._select_style(new_theme_style.id);
                        }
                        break;
                    }
                }
            })
        },

        _update_mode: function () {
            var mode = this.$("input[name='theme_mode_radio']:checked").data('mode-name');
            // remove all the mode
            _.each(this.user_setting.theme_modes, function (tmp_mode) {
                $('body').removeClass(tmp_mode.name)
                $('body').removeClass(tmp_mode.name + '_bk')
            })
            $('body').addClass(mode)
        },

        _set_mode_bk_flag: function () {
            var $body = $('body')
            // remove all the mode
            _.each(this.user_setting.theme_modes, function (tmp_mode) {
                if ($body.hasClass(tmp_mode.name)) {
                    $body.removeClass(tmp_mode.name)
                    $body.addClass(tmp_mode.name + '_bk')
                }
            })
        },

        _remove_mode_bk_flag: function () {
            var $body = $('body')
            // remove all the mode
            _.each(this.user_setting.theme_modes, function (tmp_mode) {
                if ($body.hasClass(tmp_mode.name)) {
                    $body.removeClass(tmp_mode.name)
                    $body.addClass(tmp_mode.name + '_bk')
                }
            })
        },


        _update_preview_mode: function () {

            var $el = this.$("input[name='theme_mode_radio']:checked")
            var mode_id = $el.data('mode-id')

            // remove all the mode
            var $body = $('body')

            $body.removeClass('mode_preview')
            $body.addClass('mode_preview')

            this._set_mode_bk_flag()

            // get the preview mode data
            return this._rpc({
                "model": "awesome_theme_pro.theme_mode",
                "method": "get_mode_preview_data",
                "args": [mode_id]
            }).then(function (mode_style_txt) {
                var style = document.getElementById("awesome_theme_pro_preview_mode_style_id");
                if (style.styleSheet) {
                    style.setAttribute('type', 'text/css');
                    style.styleSheet.cssText = mode_style_txt;
                } else {
                    style.innerHTML = mode_style_txt;
                }
                style && $body[0].removeChild(style);
                $body[0].appendChild(style);
            })
        },

        _add_new_tab: function (theme_style) {
            // add nav item
            this._add_new_style_nav_item(theme_style);
            // add tab pane
            this._add_new_style_tab_pane(theme_style);
            // show the item
            this.$(".theme_style_tab[data-style-id=" + theme_style.id + "]").tab('show')
        },

        _add_new_style_nav_item: function (theme_style) {
            var mode_id = this._get_cur_model_id();
            var $theme_mode_container = this.$('.theme-mode-container[data-mode-id=' + mode_id + ']')
            var $add_new = $theme_mode_container.find('.theme_style_tool_bar')
            var $nav_item = $(core.qweb.render('awesome_theme_pro.theme_style_tab', { theme_style: theme_style }))
            $nav_item.insertBefore($add_new)
        },

        // init color picker
        _add_new_style_tab_pane: function (theme_style) {
            var mode_id = this._get_cur_model_id();
            var $theme_mode_container = this.$('.theme-mode-container[data-mode-id=' + mode_id + ']');
            var $tab_pane = $(core.qweb.render('awesome_theme_pro.theme_style_tab_pane', { theme_style: theme_style }));
            var $tab_container = $theme_mode_container.find('.tab-content');
            $tab_pane.appendTo($tab_container);
            this._init_color_picker($tab_pane);
        },

        // remove tab and tab pane
        _remove_new_tab: function (style_id) {
            this.$(".theme_style_tab[data-style-id=" + style_id + "]").parent().remove()
            this.$(".theme-style-tab-pane[data-style-id=" + style_id + "]").remove()
        },

        _active_theme_style: function (style_id) {
            // show the style tab
            this.$(".theme_style_tab[data-style-id=" + style_id + "]").addClass('active')
            this.$(".theme-style-tab-pane[data-style-id=" + style_id + "]").addClass('show').addClass('active')
        },

        /**
         * get the current style text
         */
        _get_style_txt: function () {

            var result = {}
            var mode_id = this._get_cur_model_id();
            var style_id = this._get_cur_style_id();

            var mode_data = _.find(this.user_setting.theme_modes, function (mode_data) {
                return mode_data.id == mode_id
            })

            var mode_prefix = mode_data.name == 'normal' ? '' : 'body.' + mode_data.name + " ";
            var theme_styles = mode_data.theme_styles
            var theme_style = _.find(theme_styles, function (tmp_style) {
                return tmp_style.id == style_id
            })

            var style_item_cache = {}
            _.each(theme_style.groups, function (group) {
                var sub_groups = group["sub_groups"]
                _.each(sub_groups, function (sub_group) {
                    var style_items = sub_group["style_items"]
                    _.each(style_items, function (style_item) {
                        style_item_cache[style_item.id] = style_item
                    })
                })
            })

            var $style_item_container = this.$(
                '.style_item_container[data-style-id=' + style_id + ']')
            var $style_items = $style_item_container.find('.style_item')
            _.each($style_items, function (style_item) {
                var $tmp_style_item = $(style_item)
                var style_item_id = parseInt($tmp_style_item.data('style-item-id'))
                if (!style_item_cache[style_item_id]) {
                    return
                }

                // get all the var value
                if (!style_item_id in style_item_cache) {
                    return
                }

                var style_item_info = style_item_cache[style_item_id]
                if (!style_item_info.selectors) {
                    return
                }

                var var_infos = style_item_info.vars
                var val_template = style_item_info.val_template
                _.each(var_infos, function (var_info) {
                    var var_name = var_info.name;
                    var var_type = var_info.type;
                    switch (var_type) {
                        case 'color':
                            var $color_value = $tmp_style_item.find('input[var-name=' + var_name + ']');
                            var color = $color_value.val();
                            var_info.color = color;
                            val_template = val_template.replace('{' + var_name + '}', color)
                            break;
                        case 'image':
                            var $color_value = $tmp_style_item.find('input[var-name=' + var_name + ']');
                            var color = $color_value.val();
                            var_info.color = color;
                            // replace the color
                            val_template = val_template.replace('{' + var_name + '}', color)
                            break;
                        case 'image_url':
                            var $color_value = $tmp_style_item.find('input[var-name=' + var_name + ']');
                            var color = $color_value.val();
                            var_info.color = color;
                            // replace the color
                            val_template = val_template.replace('{' + var_name + '}', color)
                            break;
                        case 'svg':
                            var $color_value = $tmp_style_item.find('input[var-name=' + var_name + ']');
                            var color = $color_value.val();
                            var_info.color = color;
                            // replace the color
                            val_template = val_template.replace('{' + var_name + '}', color)
                            break;
                    }
                })

                // gen the style content
                if (!style_item_info.selectors) {
                    return;
                }

                try {
                    var selectors = style_item_info.selectors.join(',')
                } catch (error) {
                    console.log('selector error', error);
                    return
                }

                var tmp_txt = mode_prefix + " " + selectors + " {" + val_template + " }"
                result[style_item_id] = tmp_txt
            })

            return result;
        },

        _get_font_info: function () {
            var font_name = this.user_setting.settings.font_name;
            var font_type_css = "*:not(.fa) {font-family: " + font_name + ", sans-serif !important;}";
            return font_type_css;
        },

        _get_cur_style_id: function () {
            var style_id = this.$('.theme_style_tab.active:visible').data('style-id');
            return style_id;
        },

        _get_cur_model_id: function () {
            var mode_id = this.$("input[name='theme_mode_radio']:checked").data('mode-id');
            return mode_id;
        },

        _get_cur_style_data: function () {
            var result = []
            var style_id = this._get_cur_style_id();
            var $style_item_container = this.$(
                '.style_item_container[data-style-id=' + style_id + ']')
            var $style_items = $style_item_container.find('.style_item')
            _.each($style_items, function (style_item) {
                var $tmp_style_item = $(style_item)
                var $var_items = $tmp_style_item.find('.style_item_var')
                _.each($var_items, function (var_item) {
                    var $var_item = $(var_item)
                    var var_id = $var_item.data('var-id')
                    var var_type = $var_item.data('var-type')
                    switch (var_type) {
                        case 'color':
                            var color = $var_item.val()
                            result.push({
                                "id": var_id,
                                "color": color
                            })
                            break;
                    }
                })
            })
            return result;
        },

        _clear_preview_data: function () {
            // clear the mode style data
            var style = document.getElementById('awesome_theme_pro_preview_mode_style_id');
            if (style.styleSheet) {
                style.setAttribute('type', 'text/css');
                style.styleSheet.cssText = '';
            }
            // clear the style data
            style = document.getElementById('awesome_theme_pro_preview_style_id');
            if (style.styleSheet) {
                style.setAttribute('type', 'text/css');
                style.styleSheet.cssText = '';
            }
        },

        _update_style: function (preview) {
            var self = this;
            var $body = $('body')

            // get the current style infos
            var style_infos = self._get_style_txt();
            var font_info = self._get_font_info();
            var style_id = this._get_cur_style_id();

            this._rpc({
                "model": "awesome_theme_pro.theme_style",
                "method": "post_deal_preview_data",
                "args": [style_id, style_infos, font_info]
            }).then(function (styleText) {
                var style = undefined;
                if (preview) {
                    style = document.getElementById('awesome_theme_pro_preview_style_id');
                    styleText = styleText.replace(/body\.[\w]+/i, '')
                } else {
                    style = document.getElementById('awesome_theme_pro_style_id');
                }
                if (style.styleSheet) {
                    style.setAttribute('type', 'text/css');
                    style.styleSheet.cssText = styleText;
                } else {
                    style.innerHTML = styleText;
                }
                style && $body[0].removeChild(style);
                $body[0].appendChild(style);
            })
        },

        _init_color_picker: function (item) {
            var self = this;
            item.find('.style_color_item')
                .colorpicker({
                    format: 'rgba',
                    extensions: [
                        {
                            name: 'swatches',
                            options: {
                                colors: this.init_color,
                                namesAsValues: false
                            }
                        }
                    ]
                }).on('colorpickerChange', function (e) {
                    self._color_chagned(e)
                });
        },

        /**
         * when var change, change the preview
         * @param {} e 
         */
        _color_chagned: function (e) {
            var style_id = $(e.currentTarget).parents('.style_item_container').first().data('style-id')
            var $color_item = $(e.currentTarget)
            var identity = $color_item.data('identity')
            if (identity) {
                var color = $color_item.find('input').val()
                var $theme_style = self.$('.theme-style-nav-item[data-style-id=' + style_id + ']');

                switch (identity) {

                    case 'side_bar_background':
                        $theme_style.find('.sidebar-box').css("background-color", color);
                        break;

                    case 'header_background':
                        $theme_style.find('.preview-header-box').css("background-color", color);
                        break;

                    case 'body_background':
                        $theme_style.find('.preview-body-box').css("background-color", color);
                        break;

                    case 'footer_background':
                        $theme_style.find('.preview-footer-box').css("background-color", color);
                        break;
                }
            }
        },

        _save_style_data: function () {
            var self = this;
            var style_id = this._get_cur_style_id();
            this._rpc({
                "model": "awesome_theme_pro.theme_setting_manager",
                "method": "save_style_data",
                "args": [style_id, this._get_cur_style_data(), this.editor_type]
            }).then(function (theme_style) {
                // refresh style items
                self._refresh_style_items(theme_style);
                // hide the pannel
                self.hide_side_bar();
            })
        },

        _refresh_style_preview: function (theme_style) {
            var $theme_style = this.$('.theme-style-nav-item[data-style-id=' + theme_style.id + ']');
            var $nav_item = $(core.qweb.render('awesome_theme_pro.theme_style_tab', { theme_style: theme_style }))
            $nav_item.replaceWith($theme_style)
        },

        /**
         * add a new style
         * @param {*} event 
         */
        _on_add_new_style: function (event) {
            event.preventDefault();

            var mode_id = this.$("input[name='theme_mode_radio']:checked").data('mode-id');
            var style_data = this._get_setting_style_data(mode_id);

            var self = this;
            this._rpc({
                "model": "awesome_theme_pro.theme_style",
                "method": "add_new_style",
                "args": [mode_id, style_data]
            }).then(function (new_style) {

                var mode = _.find(self.user_setting.theme_modes, function (tmp_mode) {
                    return tmp_mode.id == mode_id;
                })
                mode.theme_styles.push(new_style);
                self._add_new_tab(new_style);
            })
        },

        _get_setting_style_data: function (mode_id, style_id) {

            var mode = _.find(this.user_setting.theme_modes, function (tmp_mode) {
                return tmp_mode.id == mode_id
            })
            var theme_styles = mode.theme_styles
            if (!theme_styles || theme_styles.length <= 0) {
                return null;
            }

            if (!style_id) {
                return theme_styles[0]
            }

            var theme_style = _.find(theme_styles, function (tmp_style) {
                return tmp_style.id == style_id;
            })

            return theme_style;
        },

        _on_cancel_btn_click: function (event) {
            event.preventDefault();
            event.stopPropagation();

            this.$('.customizer').removeClass('open')
        },

        /**
         * save settings
         * @param {*} event 
         */
        _on_save_btn_click: function (event) {
            event.preventDefault();

            // save the style data
            this._save_style_data();
        },

        _get_mode_data: function (mode_id) {
            return _.find(this.user_setting.theme_modes, function (mode) {
                return mode.id == mode_id
            })
        },

        /**
         * change mode
         * @param {} event 
         */
        _onchange_theme_mode_radio: function (event) {
            event.stopPropagation();

            var mode_id = $(event.currentTarget).data('mode-id')

            this.$(".theme-mode-container").addClass("d-none")
            this.$(".theme-mode-container[data-mode-id=" + mode_id + "]").removeClass("d-none")

            // set the active style
            var active_item = this.$(
                '.theme-mode-container[data-mode-id=' + mode_id + '] .theme_styles .theme-style-contianer .theme_style_tab.active');
            if (active_item.length == 0) {
                var style_id = this.$(
                    '.theme-mode-container[data-mode-id=' + mode_id + '] .theme_styles .theme-style-nav-item').first().data('style-id');
                this._active_theme_style(style_id);
            }
        },

        /**
         * export style
         */
        _export_style: function (event) {

            var $target = $(event.currentTarget)
            var styleId = parseInt($target.data('style-id'));

            if (!styleId) {
                return
            }

            this.getSession().get_file({
                complete: framework.unblockUI,
                error: (error) => this.call('crash_manager', 'rpc_error', error),
                url: '/awesome_theme_pro/export_theme_style/' + styleId,
            });
        },

        /**
         * clone and create a new style from the current style
         */
        _clone_style: function (event) {

            var $target = $(event.currentTarget)
            var styleId = parseInt($target.data('style-id'));

            var self = this;
            var mode_id = this.$("input[name='theme_mode_radio']:checked").data('mode-id');
            this._rpc({
                "model": "awesome_theme_pro.theme_style",
                "method": "clone_style",
                "args": [styleId]
            }).then(function (new_style) {
                var mode = _.find(self.user_setting.theme_modes, function (tmp_mode) {
                    return tmp_mode.id == mode_id;
                })
                mode.theme_styles.push(new_style);
                self._add_new_tab(new_style);
            })
        },

        _select_style: function (style_id) {
            this.$(".theme_style_tab[data-style-id=" + style_id + "]").tab('show')
        },

        _update_style_pane: function (theme_style) {
            var style_id = theme_style.id
            var $old_pane = this.$('.theme-style-tab-pane[data-style-id=' + style_id + ']');
            var $tab_pane = $(core.qweb.render('awesome_theme_pro.theme_style_tab_pane', { theme_style: theme_style }))
            if ($old_pane.hasClass('show')) {
                $tab_pane.addClass('show')
            }
            if ($old_pane.hasClass('active')) {
                $tab_pane.addClass('active')
            }
            $old_pane.replaceWith($tab_pane)
            this._init_color_picker($tab_pane);
        },

        /**
         * refresh the style item
         * @param {*} style_id 
         */
        _refresh_style_items: function (theme_style) {
            this._update_style_pane(theme_style)
            this._select_style(theme_style.id);
        },

        /**
         * replace style item
         */
        _replace_style_data: function (theme_style) {
            var modes = this.user_setting.theme_modes
            var mode_count = this.user_setting.theme_modes.length;
            for (var index = 0; index < mode_count; index++) {
                var mode = modes[index];
                var theme_styles = mode.theme_styles
                var style_index = _.findIndex(theme_styles, function (style) {
                    return style.id == theme_style.id;
                })
                if (style_index != -1) {
                    theme_styles[index] = theme_style;
                    break;
                }
            }
        },

        /**
         * add style item
         */
        _add_style_item: function (event) {
            event.preventDefault()

            var $target = $(event.currentTarget)

            var style_id = parseInt($target.attr('data-style-id'));
            var group_id = parseInt($target.attr('data-group-id'));
            var sub_group_id = parseInt($target.attr('data-sub-group-id'))

            var self = this
            this._set_in_action_flag()
            this.do_action({
                type: 'ir.actions.act_window',
                view_type: 'form',
                view_mode: 'form',
                res_model: "awesome_theme_pro.style_item",
                target: 'new',
                context: {
                    "default_theme_style": style_id,
                    "default_item_group": group_id,
                    "default_sub_group": sub_group_id
                },
                views: [[false, 'form']],
            }, {
                on_close: function (res) {
                    if (!res || res.special) {
                        self._defer_remove_in_action_flag();
                        return;
                    }

                    var style_item_id = res.res_id
                    self._rpc({
                        "model": "awesome_theme_pro.style_item",
                        "method": "get_style_item_data",
                        "args": [style_item_id]
                    }).then(function (style_item_data) {
                        style_item_data = style_item_data[0]
                        var sub_group = self._get_theme_item_sub_group(sub_group_id)
                        sub_group["style_items"].push(style_item_data);
                        var $new_style_item = $(core.qweb.render("awesome_theme_pro.style_item", {
                            style_item: style_item_data
                        }))
                        // show pannel
                        self._toggle_sub_group_pannel(style_id, group_id, sub_group_id, true)
                        var $sub_group = self.$('.sub-group-body[data-sub-group-id=' + sub_group_id + ']')
                        var $pannel = $sub_group.find('.sub_group_pannel');
                        $pannel.append($new_style_item);
                    })
                }
            });
        },

        _add_item_group: function (event) {
            var $target = $(event.currentTarget)
            var styleId = parseInt($target.data('style-id'));

            // bind window click
            this.bind_window_click(false);

            var self = this
            this.is_in_action = true;
            this.do_action({
                type: 'ir.actions.act_window',
                view_type: 'form',
                view_mode: 'form',
                res_model: "awesome_theme_pro.style_item_group",
                target: 'new',
                context: {
                    "default_theme_style": styleId,
                },
                views: [[false, 'form']],
            }, {
                on_close: function (res) {
                    if (!res || res.special) {
                        self._defer_remove_in_action_flag()
                        return
                    }
                    self._rpc({
                        "model": "awesome_theme_pro.theme_style",
                        "method": "get_style",
                        "args": [styleId]
                    }).then(function (theme_style) {
                        self._replace_style_data(theme_style);
                        self._refresh_style_items(theme_style);
                    }).finally(function () {
                        self._defer_remove_in_action_flag();
                    })
                }
            });
        },

        _delete_style_item_data: function (style_item_id) {
            var modes = self.user_setting.theme_modes
            var mode_count = self.user_setting.theme_modes.length;
            for (var index = 0; index < mode_count; index++) {
                var mode = modes[index];
                var theme_styles = mode.theme_styles
                for (var styleIndex = 0; styleIndex < theme_styles.length; styleIndex++) {
                    var theme_style = theme_styles[styleIndex];
                    var index = _.findIndex(theme_style.style_items, function (style_item) {
                        return style_item.id == style_item_id;
                    })
                    if (index != -1) {
                        // remove the style item
                        theme_style.style_items.splice(index, 1);
                        break;
                    }
                }
            }
        },

        _delete_style_item: function (event) {
            var self = this;
            var $target = $(event.currentTarget)
            var style_item_id = parseInt($target.data('style-item-id'));
            this._rpc({
                "model": "awesome_theme_pro.style_item",
                "method": "delete_style_item",
                "args": [style_item_id]
            }).then(function (rst) {
                self._delete_style_item_data(style_item_id);
                var $style_item = $target.parents('.style_item');
                $style_item.remove();
            })
        },

        _set_in_action_flag: function () {
            this.is_in_action = true;
        },

        _defer_remove_in_action_flag: function () {
            var self = this;
            _.defer(function () {
                self.is_in_action = false;
            })
        },

        _get_theme_style: function (style_id) {
            var modes = this.user_setting.theme_modes;
            for (var i = 0; i < modes.length; i++) {
                var mode_data = modes[i];
                for (var styleIndex = 0; styleIndex < mode_data.theme_styles.length; styleIndex++) {
                    var theme_style = mode_data.theme_styles[styleIndex]
                    if (theme_style.id == style_id) {
                        return theme_style
                    }
                }
            }
        },

        _get_theme_item_group: function (group_id) {
            var modes = this.user_setting.theme_modes;
            for (var i = 0; i < modes.length; i++) {
                var mode_data = modes[i];
                for (var styleIndex = 0; styleIndex < mode_data.theme_styles.length; styleIndex++) {
                    var theme_style = mode_data.theme_styles[styleIndex]
                    var groups = theme_style.groups || []
                    for (var group_index = 0; group_index < groups.length; group_index++) {
                        var group = groups[group_index];
                        if (group.id == group_id) {
                            return group;
                        }
                    }
                }
            }
        },

        _get_theme_item_sub_group: function (sub_group_id) {
            var modes = this.user_setting.theme_modes;
            for (var i = 0; i < modes.length; i++) {
                var mode_data = modes[i];
                for (var styleIndex = 0; styleIndex < mode_data.theme_styles.length; styleIndex++) {
                    var theme_style = mode_data.theme_styles[styleIndex]
                    var groups = theme_style.groups || []
                    for (var group_index = 0; group_index < groups.length; group_index++) {
                        var group = groups[group_index];
                        var sub_groups = group.sub_groups || []
                        for (var sub_group_index = 0; sub_group_index < sub_groups.length; sub_group_index++) {
                            var sub_group = sub_groups[sub_group_index];
                            if (sub_group.id == sub_group_id) {
                                return sub_group;
                            }
                        }
                    }
                }
            }
        },

        _get_style_item: function (item_id) {
            var modes = this.user_setting.theme_modes;
            for (var i = 0; i < modes.length; i++) {
                var mode_data = modes[i];
                for (var index = 0; index < mode_data.theme_styles.length; index++) {
                    var theme_style = mode_data.theme_styles[index]
                    var groups = theme_style.groups || []
                    for (var group_index = 0; group_index < groups.length; group_index++) {
                        var group = groups[group_index];
                        var sub_groups = group.sub_groups || []
                        for (var sub_group_index = 0; sub_group_index < sub_groups.length; sub_group_index++) {
                            var sub_group = sub_groups[sub_group_index];
                            var style_items = sub_group.style_items || []
                            for (var item_index = 0; item_index < style_items.length; item_index++) {
                                var item = style_items[item_index];
                                if (item.id == item_id) {
                                    return item;
                                }
                            }
                        }
                    }
                }
            }
        },

        _get_item_group: function (group_id) {
            var modes = this.user_setting.theme_modes;
            for (var i = 0; i < modes.length; i++) {
                var mode_data = modes[i];
                for (var index = 0; index < mode_data.theme_styles.length; index++) {
                    var theme_style = mode_data.theme_styles[index]
                    var groups = theme_style['groups']
                    for (var group_index = 0; group_index < groups.length; group_index++) {
                        var group = groups[group_index];
                        if (group.id == group_id) {
                            return group;
                        }
                    }
                }
            }
        },

        /**
         * style item
         * @param {*} style_item 
         */
        _update_item_ui: function (style_item) {
            var $old_item = this.$('.style_item[data-style-item-id=' + style_item.id + ']');
            var $new_item = $(core.qweb.render('awesome_theme_pro.style_item', { style_item: style_item }))
            $old_item.replaceWith($new_item);
            this._init_color_picker($new_item);
        },

        /**
         * edit style item
         */
        _edit_style_item: function (event) {
            var self = this;
            var $target = $(event.currentTarget)
            var style_item_id = parseInt($target.data('style-item-id'));

            this.is_in_action = true;
            this.do_action({
                type: 'ir.actions.act_window',
                view_type: 'form',
                view_mode: 'form',
                res_id: style_item_id,
                res_model: "awesome_theme_pro.style_item",
                target: 'new',
                views: [[false, 'form']],
            }, {
                on_close: function (res) {

                    if (!res || res.special) {
                        self._defer_remove_in_action_flag();
                        return
                    }

                    // get style item data
                    self._rpc({
                        "model": "awesome_theme_pro.style_item",
                        "method": "get_style_item_data",
                        "args": [style_item_id]
                    }).then(function (style_items) {
                        var style_item = style_items[0]
                        // update the style item data
                        var $sub_group = $target.parents('.sub-group-body:first')
                        var sub_group_id = parseInt($sub_group.attr('data-sub-group-id'))
                        var sub_group = self._get_theme_item_sub_group(sub_group_id)
                        var index = _.findIndex(sub_group.style_items, function (tmp_style_item) {
                            return tmp_style_item.id == style_item_id;
                        })
                        sub_group.style_items.splice(index, 1, style_item)

                        // update the style item ui
                        self._update_item_ui(style_item)
                    }).finally(function () {
                        self._defer_remove_in_action_flag();
                    })
                }
            });
        },

        /**
         * toggle group pannel
         * @param {*} group_id 
         */
        _toggle_sub_group_pannel: function (style_id, group_id, sub_group_id, force_visible) {

            var $sub_group = this.$('.sub-group-body[data-sub-group-id=' + sub_group_id + ']')
            var $pannel = $sub_group.find('.sub_group_pannel');

            if ($pannel.length == 0) {
                var theme_style = this._get_theme_style(style_id)
                var groups = theme_style.groups || []
                var group = _.find(groups, function (group) {
                    return parseInt(group.id) == group_id;
                })
                if (group) {
                    var sub_groups = group.sub_groups || []
                    var sub_group = _.find(sub_groups, function (sub_group) {
                        return sub_group.id == sub_group_id;
                    })
                    if (sub_group) {
                        $pannel = $(core.qweb.render('awesome_theme_pro.sub_group_body', { sub_group: sub_group }))
                        $sub_group.append($pannel);
                        this._init_color_picker($pannel);
                    }
                }
            }

            var $icon = $sub_group.find('.style_sub_group_name i').first();
            if ($pannel.is(':visible') && !force_visible) {
                $icon.removeClass('fa-minus-square')
                $icon.addClass('fa-plus-square')
                $pannel.removeClass('d-flex')
                $pannel.addClass('d-none')
            } else {
                if (!$pannel.is(':visible')) {
                    $icon.addClass('fa-minus-square')
                    $icon.removeClass('fa-plus-square')
                    $pannel.addClass('d-flex')
                    $pannel.removeClass('d-none')
                }
            }
        },

        /**
         * show or hide sub group pannel
         */
        show_hide_sub_group_pannel: function (sub_group_id, show) {
            var $sub_group = this.$('.sub-group-body[data-sub-group-id=' + sub_group_id + ']')
            var $pannel = $sub_group.find('.sub_group_pannel');
            var $icon = $sub_group.find('.style_sub_group_name i').first();
            if (show) {
                $icon.removeClass('fa-minus-square')
                $icon.addClass('fa-plus-square')
                $pannel.removeClass('d-flex')
                $pannel.addClass('d-none')
            } else {
                $icon.addClass('fa-minus-square')
                $icon.removeClass('fa-plus-square')
                $pannel.addClass('d-flex')
                $pannel.removeClass('d-none')
            }
        },

        /**
         * expand or hide group
         * @param {*} event 
         */
        _on_click_group_toggler: function (event) {

            var $target = $(event.currentTarget);

            var group_id = parseInt($target.attr('data-group-id'));
            var style_id = parseInt($target.attr('data-style-id'));
            var $sub_group = parseInt($target.attr('data-sub-group-id'));

            this._toggle_sub_group_pannel(style_id, group_id, $sub_group);
        },

        /**
         * add a new group
         */
        _on_add_new_group: function (event) {
            var self = this;
            var $target = $(event.currentTarget);

            var style_id = $target.data('style-id')
            this._rpc({
                "model": "awesome_theme_pro.style_item_group",
                "method": "get_add_new_group_action",
                "args": [style_id]
            }).then(function (action) {
                self.do_action(action, {
                    on_close: function (res) {
                        if (!res || res.special) {
                            self._defer_remove_in_action_flag();
                            return;
                        }
                        self.is_in_action = true;
                        var group_id = res.res_id;
                        self._rpc({
                            "model": "awesome_theme_pro.style_item_group",
                            "method": "get_group_data",
                            "args": [group_id]
                        }).then(function (group_data) {

                            // add group data
                            var theme_style = self._get_theme_style(style_id)
                            theme_style['groups'].push(group_data[0])

                            var $container = $('<div class="style_item_group d-flex flex-column"></div>')
                            var $new_group = $(core.qweb.render('awesome_theme_pro.style_item_group', {
                                'group': group_data[0],
                                'theme_style': self._get_theme_style(style_id)
                            }))
                            $container.append($new_group)
                            $container.insertBefore($target.parent());

                        }).finally(function () {
                            self._defer_remove_in_action_flag()
                        })
                    }
                });
            })
        },

        /**
         * edit image var
         */
        _on_edit_item_var: function (event) {
            var self = this;
            var $target = $(event.currentTarget);

            var var_id = parseInt($target.attr('data-var-id'));
            var style_item_id = parseInt($target.attr("data-style-item-id"));

            this._rpc({
                "model": "awesome_theme_pro.theme_var",
                "method": "get_edit_var_action",
                "args": [var_id]
            }).then(function (action) {
                self.is_in_action = true;
                self.do_action(action, {
                    on_close: function (res) {

                        if (!res || res.special) {
                            self._defer_remove_in_action_flag();
                            return;
                        }

                        // get style item data
                        self._rpc({
                            "model": "awesome_theme_pro.style_item_var",
                            "method": "get_var_data",
                            "args": [style_item_id]
                        }).then(function (var_data) {
                            var_data = var_data[0];

                            var style_item = self._get_style_item(style_item_id);
                            var index = _.findIndex(style_item.vars, function (tmp_var) {
                                return tmp_var.id == var_id;
                            })
                            style_item.vars.splice(index, 1, var_data);
                            // update the var ui

                            var $var = $(core.qweb.render("awesome_theme_pro.style_item_var", {
                                style_item: style_item,
                                style_item_var: var_data
                            }))

                            var $old_var = $target.parents('.style-item-var:first');
                            $old_var.replaceWith($var);

                            self._defer_remove_in_action_flag();
                        })
                    }
                });
            })
        },

        /**
         * add sub group
         */
        _add_sub_group: function (event) {
            var self = this;
            var $target = $(event.currentTarget)

            var style_id = parseInt($target.attr('data-style-id'))
            var group_id = parseInt($target.attr('data-group-id'))

            this._set_in_action_flag();
            this._rpc({
                "model": "awesome_theme_pro.style_item_group",
                "method": "get_add_sub_group_action",
                "args": [group_id]
            }).then(function (action) {
                self.do_action(action, {
                    on_close: function (res) {
                        if (!res || res.special) {
                            self._defer_remove_in_action_flag();
                            return;
                        }
                        // get sub group data
                        self._rpc({
                            "model": "awesome_theme_pro.style_item_sub_group",
                            "method": "get_sub_group_data",
                            "args": [res.res_id]
                        }).then(function (sub_group) {
                            var theme_style = self._get_theme_style(style_id)
                            var group = _.find(theme_style.groups || [], function (tmp_group) {
                                return tmp_group.id == group_id
                            })
                            group["sub_groups"].push(sub_group[0])
                            var $group_container = $target.parents('.style_item_group:first')
                            // render the sub group
                            var $new_sub_group = $(core.qweb.render('awesome_theme_pro.sub_group', {
                                theme_style: theme_style,
                                group: group,
                                sub_group: sub_group[0]
                            }))
                            // append new sub group
                            $new_sub_group.appendTo($group_container)
                        }).finally(function () {
                            self._defer_remove_in_action_flag()
                        })
                    }
                });
            })
        },

        _on_delete_group: function (event) {
            var self = this;

            var $target = $(event.currentTarget)
            var group_id = parseInt($target.attr('data-group-id'))
            var style_id = parseInt($target.attr('data-style-id'))

            this._set_in_action_flag()
            // check the style items deleted
            this._rpc({
                "model": "awesome_theme_pro.style_item_sub_group",
                "method": "delete_sub_group",
                "args": [sub_group_id]
            }).then(function (rst) {
                var theme_style = self._get_theme_style(style_id);
                var groups = theme_style.groups
                var index = _.findIndex(groups, function (tmp_group) {
                    return tmp_group.id == group_id
                })
                // remove the data
                groups.splice(index, 1);
                // remove ite from ui
                $target.parents('.style_item_group').remove();
            }).finally(function () {
                self._defer_remove_in_action_flag()
            })

        },

        /**
         * delete sub group
         * @param {*} event 
         */
        _on_delete_sub_group: function (event) {
            var self = this;
            var $target = $(event.currentTarget)
            var sub_group_id = $target.attr('data-sub-group-id')
            var group_id = $target.attr('data-group-id')
            var style_id = $target.attr('data-style-id')
            // check the style items deleted
            this._rpc({
                "model": "awesome_theme_pro.style_item_sub_group",
                "method": "delete_sub_group",
                "args": [sub_group_id]
            }).then(function (rst) {
                var theme_style = self._get_theme_style(style_id);
                var groups = theme_style.groups
                var group = _.find(groups, function (tmp_group) {
                    return tmp_group.id == group_id
                })
                var sub_groups = group.sub_groups || []
                var index = _.find(sub_groups, function (tmp_sub_group) {
                    return tmp_sub_group.id == sub_group_id
                })
                // remove the data
                sub_groups.splice(index, 1);
                // remove ite from ui
                $target.parents('.sub-group-body').remove();
            }).finally(function () {
                self._defer_remove_in_action_flag()
            })
        },

        /**
         * delete item group
         */
        _delete_item_group: function (event) {
            var self = this;
            var $target = $(event.currentTarget);
            var group_id = $target.attr('data-group-id');
            var style_id = $target.attr('data-style-id');
            this._rpc({
                "model": "awesome_theme_pro.style_item_group",
                "method": "delete_item_group",
                "args": [group_id]
            }).then(function (rst) {
                // update data
                var theme_style = self._get_theme_style(style_id);
                var groups = theme_style.groups;
                var group_index = _.find(groups, function (group) {
                    return group.id == group_id;
                })
                groups.splice(group_index, 1)
                // remove group item
                var $style_item_group = self.$('.style_item_group["data-group-id"=' + group_id + ']');
                $style_item_group.remove();
            }).finally(function () {
                self._defer_remove_in_action_flag()
            })
        },

        /**
         * create a new theme mode
         * @param {*} event 
         */
        _create_new_theme_mode: function (event) {

            event.preventDefault()
            var self = this;

            this._set_in_action_flag()
            this.do_action({
                type: 'ir.actions.act_window',
                view_type: 'form',
                view_mode: 'form',
                res_model: "awesome_theme_pro.theme_mode_wizard",
                target: 'new',
                views: [[false, 'form']],
            }, {
                on_close: function (res) {
                    if (!res || res.special) {
                        self._defer_remove_in_action_flag();
                        self._on_reset_mode_preview()
                        return
                    }
                    self._rpc({
                        "model": "awesome_theme_pro.theme_mode_wizard",
                        "method": "create_mode",
                        "args": [res.res_id]
                    }).then(function (mode_datas) {

                        var mode_data = mode_datas[0]

                        // save mode data
                        self.user_setting.theme_modes.push(mode_data)

                        // update the mode ui
                        self._add_new_theme_mode_ui(mode_data);

                        // remove the action flag
                        self._defer_remove_in_action_flag();

                        // reset the preview
                        self._on_reset_mode_preview();
                    })
                }
            });
        },

        /**
         * preview the mode
         * @param {*} record 
         */
        _on_creating_mode_preview: function (record) {
            var res_id = record.res_id
            var $body = $('body')
            this._rpc({
                "model": "awesome_theme_pro.theme_mode_wizard",
                "method": "preview_mode",
                "args": [res_id]
            }).then(function (style_txt) {
                $body.addClass("mode_preview")
                var style = document.getElementById('awesome_theme_pro_preview_style_id');
                if (style.styleSheet) {
                    style.setAttribute('type', 'text/css');
                    style.styleSheet.cssText = style_txt;
                } else {
                    style.innerHTML = style_txt;
                }
                style && $body[0].removeChild(style);
                $body[0].appendChild(style);
            })
        },

        /**
         * reset preview mode
         */
        _on_reset_mode_preview: function () {
            $('body').removeClass("mode_preview")
        },

        _add_new_theme_mode_ui: function (mode) {
            var $tab_item = $(core.qweb.render('awesome_theme_pro.theme_mode_tab_item', {
                theme_modes: [mode]
            }))
            this.$('.theme_mode_name_container').append($tab_item)
            var $tab_pane = $(core.qweb.render('awesome_theme_pro.theme_mode', {
                theme_mode: mode
            }))
            this.$('.theme-modes-container').append($tab_pane)
        },

        _on_import_style: function (event) {

            event.preventDefault()

            var self = this;
            var $target = $(event.currentTarget);
            var mode_id = parseInt($target.attr('mode-id'));

            this._set_in_action_flag()

            this.do_action({
                type: 'ir.actions.act_window',
                view_type: 'form',
                view_mode: 'form',
                res_model: "awesome_theme_pro.import_theme_style",
                target: 'new',
                views: [[false, 'form']],
            }, {
                on_close: function (res) {
                    if (!res || res.special) {
                        self._defer_remove_in_action_flag();
                        return
                    }
                    self._rpc({
                        "model": "awesome_theme_pro.theme_style",
                        "method": "import_new_style",
                        "args": [mode_id, res.res_id]
                    }).then(function (new_style) {
                        var mode = _.find(self.user_setting.theme_modes, function (tmp_mode) {
                            return tmp_mode.id == mode_id;
                        })
                        mode.theme_styles.push(new_style);
                        self._add_new_tab(new_style);
                    }).finally(function () {
                        self._defer_remove_in_action_flag()
                    })
                }
            });
        },

        /**
         * change mode vars
         * @param {*} event 
         */
        _change_mode_setting: function (event) {

            event.preventDefault()

            var $target = $(event.currentTarget)
            var mode_id = parseInt($target.data('mode-id'))

            var self = this;

            this._set_in_action_flag();
            this._rpc({
                "model": "awesome_theme_pro.theme_mode_wizard",
                "method": "get_change_mode_setting_wizard",
                "context": {
                    "debug": config.debug
                },
                "args": [mode_id]
            }).then(function (action) {
                self.do_action(action, {
                    on_close: function (res) {

                        if (!res || res.special) {
                            self._defer_remove_in_action_flag();
                            return
                        }

                        self._rpc({
                            "model": "awesome_theme_pro.theme_mode_wizard",
                            "method": "update_mode",
                            "args": [res.res_id]
                        }).then(function (mode_datas) {

                            var mode_data = mode_datas[0]

                            // save mode data
                            var index = _.findIndex(self.user_setting.theme_modes, function (tmp_mode_data) {
                                return tmp_mode_data.id == mode_data.id
                            })
                            self.user_setting.theme_modes.splice(index, 1, mode_data);

                            // remove the action flag
                            self._defer_remove_in_action_flag();
                        })
                    }
                })
            })
        },

        /**
         * delete mode
         */
        _on_delete_mode: function (event) {
            event.preventDefault()

            var self = this;
            var $target = $(event.currentTarget)
            var mode_id = parseInt($target.data('mode-id'))
            var mode_data = this._get_mode_data(mode_id)

            Dialog.confirm(this, 'do want to delete this theme mode?', {
                confirm_callback: function () {
                    if (mode_data.mode_styles.length > 0) {
                        Dialog.alert(this, _t("Please delete the styles first..."));
                    }
                    self._rpc({
                        "model": "awesome_theme_pro.theme_mode",
                        "method": "delete_mode",
                        "args": [mode_id]
                    }).then(function (rst) {
                        // update the data
                        var index = _.findIndex(self.user_setting.theme_modes, function (mode) {
                            return mode.id == mode_id
                        })
                        self.user_setting.theme_modes.splice(index, 1)

                        // remove the name first
                        self.$('.theme-mode-radio[data-mode-id="'+ mode_id +'"]').remove()
                        // remove the content
                        self.$('.theme-mode-container[data-mode-id="'+ mode_id +'"]').remove()
                    })
                }
            });
        }
    });


    // add to the style setting, show if it is admin
    // just visitble when the user is admin or config as the user wide
    if ((BackendUserSetting.is_admin && BackendUserSetting.settings.theme_setting_mode == 'system')
        || BackendUserSetting.settings.theme_setting_mode == 'user') {
        SystrayMenu.Items.push(AwesomeCustomizer);
    }

    return AwesomeCustomizer;
});

