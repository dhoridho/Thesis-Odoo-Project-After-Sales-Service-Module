
odoo.define('translation_load_fix/static/src/js/core/translation.js', function (require) {
'use strict';

const { TranslationDataBase } = require('web.translation');

const { Component } = owl;



TranslationDataBase.include({
    /**
     * @override
     */
    load_translations: function(session, modules, lang, url) {

        var self = this;
        var cacheId = session.cache_hashes && session.cache_hashes.translations;
        url = url || '/web/webclient/translations';
        url += '/' + (cacheId ? cacheId : Date.now());
        return $.get(url, {
            mods: modules ? modules.slice(0, 200).join(',') : null,
            lang: lang || null,
        }).then(function (trans) {
            self.set_bundle(trans);
        });
    }
});


});
