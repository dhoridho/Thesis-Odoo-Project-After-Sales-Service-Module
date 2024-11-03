odoo.define('equip3_manuf_operations.RowDecoration', function (require) {
    "use strict";
    
    var ListRenderer = require('web.ListRenderer');
    
    ListRenderer.include({
        _renderRow: function (record, index) {
            var $row = this._super.apply(this, arguments);
            if ('decoration-bold' in this.arch.attrs){
                var expr = py.parse(py.tokenize(this.arch.attrs['decoration-bold']));
                $row.toggleClass('font-weight-bold', py.PY_isTrue(py.evaluate(expr, record.evalContext)));
            }
            return $row;
        },
    });
    return ListRenderer;

});