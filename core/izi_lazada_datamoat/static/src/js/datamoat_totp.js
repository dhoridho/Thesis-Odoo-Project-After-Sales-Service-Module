odoo.define('izi_lazada_datamoat.datamoat_totp', function (require) {
  "use strict";

  let rpc = require('web.rpc');
  let core = require('web.core');

  // noinspection JSIgnoredPromiseFromCall
  require('web.dom_ready');
  let $totp_ask_btn = $('#totp_ask');

  function waitAskOTP(wait_time) {
    let askingOTP = setInterval(function () {
      if (wait_time <= 0) {
        clearInterval(askingOTP);
        $totp_ask_btn.html('<i class="fa fa-envelope"></i> Resend the code');
        $totp_ask_btn.removeClass('disabled');
      } else {
        $totp_ask_btn.html(wait_time + " seconds to ask new code");
        $totp_ask_btn.addClass('disabled');
      }
      wait_time -= 1;
    }, 1000);
  }

  $totp_ask_btn.on('click', function (ev) {
    ev.preventDefault();
    $totp_ask_btn.addClass('disabled');
    rpc.query({
      route: '/web/login/datamoat/totp/ask',
      params: {
        csrf_token: core.csrf_token,
        time: +new Date
      }
    }, {}).then(function (data) {
      waitAskOTP(data.wait_time);
    })
  });
});