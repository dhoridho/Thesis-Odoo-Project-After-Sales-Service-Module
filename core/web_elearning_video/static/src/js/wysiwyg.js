odoo.define('web_elearning_video.wysiwyg', function (require) {
  'use strict';

  var wysiwyg = require('web_editor.wysiwyg');
  var weWidgets = require('wysiwyg.widgets');
  var VideoDialog = require('wysiwyg.widgets.VideoDialog');
  var AudioDialog = require('wysiwyg.widgets.AudioDialog');
  $.extend(weWidgets, {VideoDialog: VideoDialog, AudioDialog: AudioDialog});
  wysiwyg.extend({
    defaultOptions: wysiwyg.prototype.defaultOptions.toolbar.push([
      'video', ['video', 'audio']
    ])
  })
});

