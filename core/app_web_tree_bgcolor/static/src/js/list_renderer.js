odoo.define('app_web_tree_bgcolor.ListRenderer', function (require) {
    "use strict";

    var core = require('web.core');
    var ListRenderer = require('web.ListRenderer');

    var DECORATIONS = [
        'decoration-bf',
        'decoration-it',
        'decoration-danger',
        'decoration-info',
        'decoration-muted',
        'decoration-primary',
        'decoration-success',
        'decoration-warning',
        'decoration-black',
        'decoration-white',
        'bg-danger',
        'bg-info',
        'bg-muted',
        'bg-primary',
        'bg-success',
        'bg-warning',
        'bg-black',
        'bg-white',
    ];

    ListRenderer.include({
        init: function (parent, state, params) {
            this._super.apply(this, arguments);
            //处理bg-color
            this.rowDecorations = _.chain(this.arch.attrs)
                .pick(function (value, key) {
                    return DECORATIONS.indexOf(key) >= 0;
                }).mapObject(function (value) {
                    return py.parse(py.tokenize(value));
                }).value();
        },
    });
});

