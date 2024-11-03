odoo.define('setu.cash.flow.forecasting', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var field_registry = require('web.field_registry');
var field_utils = require('web.field_utils');

var QWeb = core.qweb;
var _t = core._t;

var ShowForcastingFormulaWidget = AbstractField.extend({
    events: _.extend({
        'click .forcasting_formula': '_onShowForcastingFormula',
    }, AbstractField.prototype.events),
    supportedFieldTypes: ['char'],

    isSet: function() {
        return true;
    },

    _render: function() {
        var self = this;
        var info = JSON.parse(this.value);
        if (!info) {
            this.$el.html('');
            return;
        }
        this.$el.html(QWeb.render('SetuShowForcastingFormula', {
            lines: info.content
        }));
        _.each(this.$('.js_show_forcasting_formula'), function (k, v){
            var isRTL = _t.database.parameters.direction === "rtl";
            var content = info.content;
            var options = {
                content: function () {
                    var $content = $(QWeb.render('SetuShowForcastingFormulaPopOver', {content: content}));
                    return $content;
                },
                html: true,
                placement: 'right',
                title: 'Help',
                 trigger: 'hover',
//                trigger: 'focus',
                delay: { "show": 0, "hide": 100 },
                container: $(k).parent(),
            };
            $(k).popover(options);
        });
    }
});

field_registry.add('show_forcasting_formula_widget', ShowForcastingFormulaWidget);

return {
    ShowForcastingFormulaWidget: ShowForcastingFormulaWidget
};

});
