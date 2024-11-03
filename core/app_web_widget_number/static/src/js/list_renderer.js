odoo.define('app_web_widget_number.ListRenderer', function (require) {
    "use strict";

    var ListRenderer = require('web.ListRenderer');
    ListRenderer.include({
        _renderBodyCell: function (record, node, colIndex, options) {
            var name = node.attrs.name;
            var value = record.data[name];
            var $td = this._super.apply(this, arguments);
            if (options.mode == "readonly" && node.attrs.options) {
                try {
                    var nodeOptions = py.eval(node.attrs.options);
                    if (nodeOptions.nozero) {
                        if (parseInt(value) === 0) {
                            $td.text("");
                        }
                    }
                } catch(e) {}
            }
            return $td;
        }
    });

});