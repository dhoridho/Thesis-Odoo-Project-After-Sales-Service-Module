odoo.define('general_template.biz_color', function(require) {
    "use strict";

    var core = require('web.core');
    var form_widgets = require('web.basic_fields');
    var field_registry = require('web.field_registry');
    var _t = core._t;

    // for colorpicker library import
    var colpick = window.colpick;

    core.action_registry.add('biz_color', 'instance.web.search.CharField');

    var BizColorPicker = form_widgets.FieldChar.extend({
        template: 'BizColorPicker',
        widget_class: 'oe_form_biz_color_picker',

        _getValue: function () {
            if (this && this.$input){
                return this.$input.val();
            }
            else{
                return this.$('input').val()
            }
        },
        _onNavigationMove: function (ev) {
            // the following code only makes sense in edit mode, with an input
            if (this.mode === 'edit') {
                if (this && this.$input){
                    var input = this.$input[0];
                var selecting = (input.selectionEnd !== input.selectionStart);
                if ((ev.data.direction === "left" && (selecting || input.selectionStart !== 0))
                 || (ev.data.direction === "right" && (selecting || input.selectionStart !== input.value.length))) {
                    ev.stopPropagation();
                }}
            }
        },
        _render: function() {
            var show_value = this._formatValue(this.value);
            if (this.mode == 'edit') {
                var $input = this.$el.find('input');
                $input.val(show_value);
                $input.css("background-color", show_value)
                var $element= this;
                $input.colpick({
                    onSubmit:function(hsb,hex,rgb,el,bySetColor) {
                        $(el).val('#'+hex);
                        $(el).colpickHide();
                        $element._setValue('#' + hex);
                    },
                    onChange:function(hsb,hex,rgb,el,bySetColor) {
                        $(el).val('#'+hex);
                        $input.css('backgroundColor', '#' + hex);
                        $element._setValue('#' + hex);
                    },
                });
            } else if(this.mode == 'readonly') {
                this.$(".oe_form_char_content").text(show_value);
                this.$('div').css("background-color", show_value)
            }
        }
    });

    field_registry.add('biz_color', BizColorPicker);
});
