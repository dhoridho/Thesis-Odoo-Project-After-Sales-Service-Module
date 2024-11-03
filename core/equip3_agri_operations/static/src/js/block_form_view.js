odoo.define('equip3_agri_operations.BlockFormRenderer', function (require) {
    "use strict";
    
    var FormRenderer = require('web.FormRenderer');
    var FormView = require('web.FormView');
    var viewRegistry = require('web.view_registry');
    
    var blockRenderer = FormRenderer.extend({
        _renderView: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function () {
                self.$el.find('div[name="scheduled_ids"]').addClass('o_agriculture_scheduled_tab');
            });
        }
    });
    
    var blockFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Renderer: blockRenderer,
        }),
    });
    
    viewRegistry.add('agriculture_block_form_view', blockFormView);
    
    return {
        blockRenderer: blockRenderer,
    };
});
    