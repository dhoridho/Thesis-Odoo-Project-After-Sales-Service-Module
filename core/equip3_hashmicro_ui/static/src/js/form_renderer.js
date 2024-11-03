odoo.define('equip3_hashmicro_ui.FormRenderer', function (require) {
    "use strict";

    var FormRenderer = require('web.FormRenderer');
    var BooleanToggle = require('web.basic_fields').BooleanToggle;

    FormRenderer.include({

        _renderFieldWidget: function (node, record, options) {
            if (node.tag === 'field' && record.fields[node.attrs.name].type === 'boolean' && !node.attrs.widget){
                record.fieldsInfo[this.viewType][node.attrs.name].Widget = BooleanToggle;
            }
            return this._super.apply(this, arguments);
        },

        _renderStatButton: function (node) {
            var $button = this._super.apply(this, arguments);
            var $img = $button.find('img');
            if ($img.length){
                var imgClass = $img.attr('src');
                if (imgClass.includes('o-hm')) {
                    if (imgClass.includes('o-hm-icon ')){
                        imgClass = imgClass.replace('o-hm-icon ', '');
                    } else if (imgClass.includes(' o-hm-icon')){
                        imgClass = imgClass.replace(' o-hm-icon', '');
                    }
                    $img.replaceWith('<i class="o_button_icon o-hm-icon ' + imgClass + '"/>');
                }
            }
            return $button;
        },

        _getInlineClassList: function(){
            return ['oe_force_inline', 'oe_subtotal_footer'];
        },

        _shouldInline: function(node){
            let nodeClass = node.attrs.class;
            if (nodeClass){
                if (_.filter(this._getInlineClassList(), function(cls){return nodeClass.includes(cls);}).length){
                    return true;
                }
            }
            return false;
        },

        _changeTrElement: function($tr, force){
            var $currentTd;
            var i = 0;
            _.each($tr.children(), function (td) {
                var $td = $(td);
                if ($td.hasClass('o_td_label') || (force && i === 0)){
                    if (force){
                        $td.children().addClass('o_td_label');
                    } else {
                        $td.children().wrapAll('<div class="o_td_label"/>');
                        $td.removeClass('o_td_label');
                    }
                    $currentTd = $td;
                } else if ($currentTd) {
                    var $div = $('<div class="o_td_widget"/>');
                    $div.append($td.children());
                    $currentTd.append($div);
                    $currentTd.css('width', force ? '100%' : $td.css('width'));
                    $td.remove();
                }
                i += 1;
            });
        },

        _renderInnerGroup: function (node) {
            var $result = this._super.apply(this, arguments);
            var $trs = $result.find('tbody > tr');
            if (this._shouldInline(node)){
                $trs.children('td:not(.o_td_label)').addClass('o_td_widget');
                return $result;
            }
            var self = this;
            _.each($trs, function (tr) {
                var $tr = $(tr);
                self._changeTrElement($tr, false);
                if ($tr.children().length === 2 && !$tr.find('.o_td_label').length){
                    self._changeTrElement($tr, true);
                }
            });
            return $result;
        },

        _addFieldTooltip: function (widget, $node) {
            this._super.apply(this, arguments);
            if (widget.field.help && !$node.hasClass('o_form_label_help')){
                var $help = $('<span class="o-hm2-question o_field_help" title="' + widget.field.help + '"></span>');
                $node.addClass('o_form_label_help')
                $node.append($help);
            }
        },

        _renderView: function () {
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                var $ribbons = self.$el.find('.ribbon:not(.o_invisible_modifier)');
                self.$el.toggleClass('o_ribbon_active', $ribbons.length > 0);
            });
        }
    });
    return FormRenderer;
});