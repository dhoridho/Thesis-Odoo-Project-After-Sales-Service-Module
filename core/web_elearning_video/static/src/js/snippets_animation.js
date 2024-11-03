odoo.define('web_elearning_video.snippets_animations', function (require) {
  'use strict';

  var publicWidget = require('web.public.widget');

  publicWidget.registry.mediaVideo.include({

    start: function () {
      if(this.$target.hasClass('iframe_custom')) return;
      return this._super.apply(this, arguments);;
    },
  });
});

