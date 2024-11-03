/**
 * company editor action
 */
odoo.define('awesome.theme_edit_action', function (require) {
    "use strict";

    var core = require('web.core');
    var ThemeEditor = require('awesome_theme_pro.theme_editor')

    /**
     * 
     * @param {*} parent 
     * @param {*} action 
     */
    function show_theme_editor(parent, action) {
        var editor = new ThemeEditor(parent, action)
        editor.appendTo($('body'))
    }

    core.action_registry.add('theme_edit_action', show_theme_editor);
});