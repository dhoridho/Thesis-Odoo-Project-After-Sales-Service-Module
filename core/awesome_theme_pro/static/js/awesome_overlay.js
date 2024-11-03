odoo.define('awesome_theme_pro.overlay', function (require) {
    "use strict";

    var Widget = require('web.Widget');

    var AwsomeOverlay = Widget.extend({
        template: 'awesome_theme_pro.overlay',
        z_index: 990,

        events: _.extend({}, Widget.prototype.events, {
            "click": "_on_click"
        }),

        init: function (parent, z_index) {
            this.z_index = z_index
            this._super.apply(this, arguments);
        },

        is_visible: function() {
            return this.$el.is(':visible')
        },

        show: function() {
            this.$el.show();
        },

        hide: function() {
            this.$el.hide();
        },

        _on_click: function() {
            this.trigger_up('awesome_overlay_clicked');
        },

        start: function() {
            var self = this
            return this._super.apply(this, arguments).then(function(){
                self.$el.css('z-index', self.z_index)
            })
        }
    });

    return AwsomeOverlay;
});
