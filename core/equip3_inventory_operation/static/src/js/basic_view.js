odoo.define('equip3_inventory_operation.BasicView', function(require){
    "use strict";

    var BasicView = require('web.BasicView');
    var pyUtils = require('web.py_utils');

    BasicView.include({
        _processField: function (viewType, field, attrs) {
            if (!_.isObject(attrs.options) && attrs.options) {
                attrs.options = attrs.options ? pyUtils.py_eval(attrs.options, {context: py.dict.fromJSON(this.loadParams.context)}) : {};
            }
            return this._super.apply(this, arguments);
        }
    });

    return BasicView;
});