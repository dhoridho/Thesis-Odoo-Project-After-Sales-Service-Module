odoo.define('equip3_manuf_other_operations.MaterialFormRenderer', function (require) {
"use strict";

var FormRenderer = require('web.FormRenderer');
var FormView = require('web.FormView');
var viewRegistry = require('web.view_registry');

var materialRenderer = FormRenderer.extend({
    _renderView: function(){
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            self.$el.find('div[name="material_line_ids"]').addClass('o_simulation_material_tab');
            self.$el.find('th[data-name="active_for_create"]').empty().append(self.$el.find('div[name="active_all"]'));
        });
    },

    confirmChange: function () {
        var self = this;
        var checkbox = self.$el.find('div[name="active_all"]');
        return this._super.apply(this, arguments).then(function (Widgets) {
            _.each(Widgets, function (widget) {
                widget.$el.find('th[data-name="active_for_create"]').removeClass('o_column_sortable');
                if (checkbox.length){
                    widget.$el.find('th[data-name="active_for_create"]').empty().append(checkbox);
                }
            });
            return Widgets;
        });
    },

    _postProcessField: function (widget, node) {
        this._super.apply(this, arguments);
        widget.$el.find('th[data-name="active_for_create"]').removeClass('o_column_sortable');
    }
});

var materialFormView = FormView.extend({
    config: _.extend({}, FormView.prototype.config, {
        Renderer: materialRenderer,
    }),
});

viewRegistry.add('fg_simulation_material_view', materialFormView);

return {
    materialRenderer: materialRenderer,
};
});
