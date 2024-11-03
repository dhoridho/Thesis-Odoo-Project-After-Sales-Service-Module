odoo.define('equip3_kitchen_operations.MaterialFormRenderer', function (require) {
    "use strict";
    
    var FormRenderer = require('web.FormRenderer');
    var FormView = require('web.FormView');
    var viewRegistry = require('web.view_registry');
    
    var materialRenderer = FormRenderer.extend({
        _renderView: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self.$el.find('div[name="move_raw_ids"]').addClass('o_kitchen_material_tab');
            });
        }
    });
    
    var materialFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Renderer: materialRenderer,
        }),
    });
    
    viewRegistry.add('kitchen_material_view', materialFormView);
    
    return {
        materialRenderer: materialRenderer,
    };
});
    