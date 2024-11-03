odoo.define('equip3_manuf_sale.OrderLineBom', function (require) {
    "use strict";
    
    var Widget = require('web.Widget');
    var widget_registry = require('web.widget_registry');

    var OrderLineBom = Widget.extend({
        template: 'equip3_manuf_operations.LineBom',
        events: _.extend({}, Widget.prototype.events, {
            'click .fa-flask': '_onClickButton',
        }),
    
        /**
         * @override
         * @param {Widget|null} parent
         * @param {Object} params
         */
        init: function (parent, params) {
            this.data = params.data;
            this.fields = params.fields;
            this._super(parent);
        },
        
        updateState: function (state) {
            var candidate = state.data[this.getParent().currentRow];
            if (candidate) {
                this.data = candidate.data;
            }
        },
    
        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
        _onClickButton: function (ev) {
            var grandParent = this.getParent();
            var state = grandParent.state;

            if (grandParent.currentRow == undefined){
                return;
            }
            if (grandParent.editable !== "bottom"){
                return;
            }
            var parent = state.data[grandParent.currentRow];
            this.trigger_up('open_record', {id: parent.id});
        },
    });
    
    widget_registry.add('order_line_bom', OrderLineBom);
    
    return OrderLineBom;
});
