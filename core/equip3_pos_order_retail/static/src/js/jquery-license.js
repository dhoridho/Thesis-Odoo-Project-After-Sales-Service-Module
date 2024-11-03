odoo.define('equip3_pos_order_retail.license', function(require) {
    const models = require('point_of_sale.models');
    const {
        Gui
    } = require('point_of_sale.Gui');

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