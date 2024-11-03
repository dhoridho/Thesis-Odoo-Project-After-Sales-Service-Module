odoo.define('equip3_hashmicro_ui.UserMenu', function(require){
    "use strict";
    
    var UserMenu = require('web.UserMenu');
    var session = require('web.session');
    var equipTheme = require('equip3_hashmicro_ui.equipTheme');

    UserMenu.include({
        events: _.extend({}, UserMenu.prototype.events, {
            'click .color_change_theme': '_onChangeTheme',
        }),

        _onChangeTheme: function(event) {
            event.preventDefault();

            var $target = $(event.target); 
            var theme = $target.data('theme-color');
            var self = this;
            return this._rpc({
                model: 'res.users',
                method: 'change_equip_theme',
                args: [session.uid, theme]
            }).then(function(result) {
                if (result){
                    self._setActiveTheme(theme);
                }
            });
        },

        _setActiveTheme: function(theme){
            var $themes = this.$el.find('.color_change_theme:not([data-theme-color='+ theme + '])');
            var $activeTheme = this.$el.find('.color_change_theme[data-theme-color='+ theme + ']');
            if ($themes.length){
                $themes.find('i').addClass('d-none');
            }
            if ($activeTheme.length){
                $activeTheme.find('i').removeClass('d-none');
            }
            if (theme !== 'white'){
                $('#company_logo').attr('src', '/equip3_hashmicro_ui/static/src/img/hashmicro_other_logo.png');
            } else {
                $('#company_logo').attr('src', '/equip3_hashmicro_ui/static/src/img/hashmicro-logo-white.png');
            }

            for (var propertyName in equipTheme[theme]){
                var propertyValue = equipTheme[theme][propertyName];
                document.documentElement.style.setProperty('--o-theme-' + propertyName, propertyValue);
            }
        }
    });

    return UserMenu;
});