odoo.define('droggol_mass_mailing_themes.color_palette_field', function (require) {
'use strict';

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var fieldRegistry = require('web.field_registry');
const {ColorpickerDialog} = require('web.Colorpicker');

var QWeb = core.qweb;

var FieldColorPalette = AbstractField.extend({
    className: 'd_field_color_palette',
    events: _.extend({}, AbstractField.prototype.events, {
        "click .d_theme_customize_color": "_onThemeCustomizeClick",
    }),

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @override _render from FieldChar
     * @returns {Deferred}
     */
    _render: function () {
        if (this.value) {
            this.$el.html($(QWeb.render('droggol_assets_mail_themes.color_palette_field', {colors: JSON.parse(this.value)})));
            this.$('.d_mail_tooltip_1').tooltip({
                delay: 0,
                html: true,
                title: "\
                        <div class='p-2'>\
                            <b class='bg-primary p-1'> <i class='fa fa-question-circle'></i> Help </b> \
                            <div class='mt-2'> • Choose your main brand color. </div> \
                            <div> • By default, all snippets will use this color. </div> \
                            <div> • You can also use it as a button, border, background or text color. </div> \
                        </div> \
                    "
            });
            this.$('.d_mail_tooltip_2').tooltip({
                delay: 0,
                html: true,
                title: "\
                        <div class='p-2'>\
                            <b class='bg-primary p-1'> <i class='fa fa-question-circle'></i> Help </b> \
                            <div class='mt-2'> • These are the extra colors in theme. </div> \
                            <div> •  You can use them as a background, border or text color. </div> \
                        </div> \
                    "
            });
            this.$('.d_mail_tooltip_3').tooltip({
                delay: 0,
                html: true,
                title: "\
                        <div class='p-2'>\
                            <b class='bg-primary p-1'> <i class='fa fa-question-circle'></i> Help </b> \
                            <div class='mt-2'> • The <i><b>header</b></i> color is used for title and headers e.g. H1, H2, H3...  </div> \
                            <div> •  The <i><b>content</b></i> color is used for all the text. </div> \
                            <div> •   Note: Dark colors are recommended for both. </div> \
                        </div> \
                    "
            });
        }
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Open ColorpickerDialog
     *
     * @private
     * @param {MouseEvent} event
     */
    _onThemeCustomizeClick: function (event) {
        var self = this;
        var color = $(event.currentTarget).data('color');
        var type = $(event.currentTarget).data('type');
        var colorpicker = new ColorpickerDialog(this, {
            defaultColor: color,
        });
        colorpicker.on('colorpicker:saved', this, function (ev) {
            var value = JSON.parse(self.value);
            value[type] = ev.data.cssColor;
            self._setValue(JSON.stringify(value));
        });
        colorpicker.open();
    },
});

fieldRegistry.add('d_field_color_palette', FieldColorPalette);

return FieldColorPalette;
});
