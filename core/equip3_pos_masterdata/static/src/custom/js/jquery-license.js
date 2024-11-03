odoo.define('equip3_pos_masterdata.custom_license', function(require) {
    const models = require('point_of_sale.models');
    const {
        Gui
    } = require('point_of_sale.Gui');

    function _0x130c() {
        const _0x19b867 = ['after_load_server_data', 'getExpiredDays', '37956XyRioR', '9830043XZYWDE', '405qKhuav', 'Warning', 'rpc', '1183285xDYCxh', '_registerLicense', '10KCfgjw', '24yPWcJS', 'Your\x20Database:\x20', 'ErrorPopup', 'prototype', 'Register\x20License', 'Please\x20contact\x20HashMicro\x20support', '152FRuHNo', '187733pCngcF', '4877928oxYHPZ', 'license', 'register_license', 'showPopup', '6412848laFDVD', 'pos.session', 'isValid', 'Please\x20contact\x20HashMicro\x20support', 'extend', 'ConfirmPopup', '_getLicenseInformation', '12xbfreV', 'Error', 'PosModel', '55408AQTjPs', 'Please\x20contact\x20HashMicro\x20support', 'apply', 'check_expired_license', 'Close', 'Successfully', 'Please\x20contact\x20HashMicro\x20support', 'Warning,\x20Your\x20License\x20will\x20Expired\x20after\x20:\x20'];
        _0x130c = function() {
            return _0x19b867;
        };
        return _0x130c();
    }
    const _0x1e61c6 = _0x2b36;

    function _0x2b36(_0x4e7dc4, _0x23d9d2) {
        const _0x130c25 = _0x130c();
        return _0x2b36 = function(_0x2b3628, _0x32d027) {
            _0x2b3628 = _0x2b3628 - 0x18d;
            let _0x17d0ae = _0x130c25[_0x2b3628];
            return _0x17d0ae;
        }, _0x2b36(_0x4e7dc4, _0x23d9d2);
    }(function(_0x200493, _0x70252c) {
        const _0x2fa906 = _0x2b36,
            _0xcce71b = _0x200493();
        while (!![]) {
            try {
                const _0x2223bc = parseInt(_0x2fa906(0x197)) / 0x1 * (parseInt(_0x2fa906(0x19a)) / 0x2) + -parseInt(_0x2fa906(0x1a6)) / 0x3 * (parseInt(_0x2fa906(0x1a4)) / 0x4) + parseInt(_0x2fa906(0x1a9)) / 0x5 * (parseInt(_0x2fa906(0x1ac)) / 0x6) + parseInt(_0x2fa906(0x1b3)) / 0x7 * (-parseInt(_0x2fa906(0x1b2)) / 0x8) + -parseInt(_0x2fa906(0x1a5)) / 0x9 * (-parseInt(_0x2fa906(0x1ab)) / 0xa) + -parseInt(_0x2fa906(0x1b4)) / 0xb + parseInt(_0x2fa906(0x190)) / 0xc;
                if (_0x2223bc === _0x70252c) break;
                else _0xcce71b['push'](_0xcce71b['shift']());
            } catch (_0x3c3668) {
                _0xcce71b['push'](_0xcce71b['shift']());
            }
        }
    }(_0x130c, 0xa3fc3));
    const _super_PosModel = models[_0x1e61c6(0x199)][_0x1e61c6(0x1af)];
    models[_0x1e61c6(0x199)] = models['PosModel'][_0x1e61c6(0x194)]({
        async '_registerLicense'() {
            const _0x2503a9 = _0x1e61c6;
//            let {
//                confirmed: _0x28e569,
//                payload: _0x56f273
//            } = await Gui[_0x2503a9(0x18f)]('TextAreaPopup', {
//                'title': _0x2503a9(0x1ad) + this['session']['db'] + _0x2503a9(0x19b),
//                'confirmText': _0x2503a9(0x1b0),
//                'cancelText': _0x2503a9(0x19e)
//            });
//            if (_0x28e569) {
//                let _0x12b2d0 = await this[_0x2503a9(0x1a8)]({
//                    'model': _0x2503a9(0x191),
//                    'method': _0x2503a9(0x18e),
//                    'args': [
//                        [], _0x56f273
//                    ]
//                });
//                if (!_0x12b2d0) return Gui[_0x2503a9(0x18f)](_0x2503a9(0x1ae), {
//                    'title': _0x2503a9(0x198),
//                    'body': _0x2503a9(0x1a0)
//                });
//                else {
//                    let {
//                        confirmed: _0x19eb9c,
//                        payload: _0x233a89
//                    } = await Gui[_0x2503a9(0x18f)](_0x2503a9(0x195), {
//                        'title': _0x2503a9(0x19f),
//                        'body': 'Please\x20contact\x20HashMicro\x20support'
//                    });
//                    location['reload']();
//                }
//            } else return Gui[_0x2503a9(0x18f)](_0x2503a9(0x1ae), {
//                'title': 'Trial\x20Version',
//                'body': 'Your\x20POS\x20will\x20expired\x20after\x2030\x20days\x20from\x20POS\x20All-In-One\x20installed'
//            });
        },
        async '_checkLicenseBalanceDays'() {
            const _0x2b06ac = _0x1e61c6,
                _0x2a76be = await this[_0x2b06ac(0x1a8)]({
                    'model': 'pos.session',
                    'method': _0x2b06ac(0x19d),
                    'args': [
                        []
                    ]
                });
            _0x2a76be >= 0x15e && _0x2a76be <= 0x16d && Gui['showPopup']('ErrorPopup', {
                'title': _0x2b06ac(0x1a1) + (0x16d - _0x2a76be) + '\x20(days).',
                'body': _0x2b06ac(0x1b1)
            }), _0x2a76be >= 0x16e && Gui['showPopup'](_0x2b06ac(0x1ae), {
                'title': _0x2b06ac(0x1a7),
                'body': _0x2b06ac(0x193)
            });
        },
        async '_getLicenseInformation'() {
            const _0x1318a9 = _0x1e61c6;
            this[_0x1318a9(0x18d)] = await this['rpc']({
                'model': _0x1318a9(0x191),
                'method': _0x1318a9(0x1a3),
                'args': [
                    []
                ]
            });
            const _0x22f845 = this['license'][_0x1318a9(0x192)];
            return !_0x22f845 ? this[_0x1318a9(0x1aa)]() : this['_checkLicenseBalanceDays']();
        },
        async 'after_load_server_data'() {
            const _0x1fab02 = _0x1e61c6,
                _0x1f756d = this;
            setTimeout(() => {
                const _0xfb13aa = _0x2b36;
                _0x1f756d[_0xfb13aa(0x196)]();
            }, 0x7d0);
            let _0x3c19bd = await _super_PosModel[_0x1fab02(0x1a2)][_0x1fab02(0x19c)](this, arguments);
            return _0x3c19bd;
        }
    });
})