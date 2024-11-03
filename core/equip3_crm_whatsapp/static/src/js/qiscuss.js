odoo.define('equip3_crm_whatsapp/static/src/js/qiscus-sdk-core.js', function (require) {
    'use strict';
//    const qiscus = require("https://unpkg.com/qiscus-sdk-core"), framework = require("web.framework");
    const qiscus = new QiscusSDKCore()
    const env = require('web.commonEnv');
    const { Store } = owl;
    const { EventBus } = owl.core;
    document.addEventListener('DOMContentLoaded', function () {
        qiscus.init({
            AppId: 'ublch-mqh1qsdhhbd1rj2',
            mode: 'widget',
            options: {
                presenceCallback(data) {
                    console.info('presence data', data);
                },
//                loginSuccessCallback(data) {
//                    console.info('Login success callback', data);
//                },
            }
        })
//        qiscus.setUser('Saepi.Ridwan@hashmicro.com.sg', 'AdminHM123456#', 'Saepi Ridwan', '', {})
//            .then(function (authData) {
//                console.info('Login success callback', authData);
//            })
//            .catch(function (error) {
//                console.info('Login error callback', error);
//            })
    });
});