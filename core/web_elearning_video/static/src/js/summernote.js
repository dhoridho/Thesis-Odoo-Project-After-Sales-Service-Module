odoo.define('web_elearning_video.summernote', function (require) {
    'use strict';
    var core = require('web.core');
    require('web_editor.wysiwyg');
    var handler = $.summernote.eventHandler;
    var lang = $.summernote.lang.odoo;
    var _t = core._t;
    var tmpl = $.summernote.renderer.getTemplate();
    const topBus = window.top.odoo.__DEBUG__.services['web.core'].bus;
    var summernoteManager = require('web_editor.rte.summernote');
    var weWidgets = require('wysiwyg.widgets');

    $.extend(lang, {
        video: {
            video: _t('Add Video'),
        },
        audio: {
            audio: _t('Add Audio')
        }
    })
    $.summernote.addPlugin({
        buttons: {
            "video": function (lang, options) {
                var button = tmpl.iconButton(options.iconPrefix + 'video-camera', {
                    event: 'showVideoDialog',
                    hide: true,
                    title: lang.video.video,
                });
                return button;
            },
            // "audio": function (lang, options) {
            //     var button = tmpl.iconButton(options.iconPrefix + 'microphone', {
            //         event: 'showAudioDialog',
            //         hide: true,
            //         title: lang.audio.video,
            //     });
            //     return button;
            // }
        },
        events: {
            "showVideoDialog": function (layoutInfo, value) {
                var dom = $.summernote.core.dom;
                var layoutInfoCustom = dom.makeLayoutInfo(layoutInfo.currentTarget);
                var $dialog = layoutInfoCustom.dialog(),
                    $editable = layoutInfoCustom.editable();
                var header = $dialog.find('.note-video-dialog').find('.modal-header');
                header.find('.close').attr('aria-hidden', false);
                handler.invoke('editor.saveRange', $editable);
                this.videoDialog($editable, $dialog).then(function (data) {
                    handler.invoke('editor.restoreRange', $editable);
                }).fail(function () {
                    handler.invoke('editor.restoreRange', $editable);
                });
            },
            "videoDialog": function ($editable, $dialog) {
                return $.Deferred(function (deferred) {
                    var $videoDialog = $dialog.find('.note-video-dialog');
                    $videoDialog.one('shown.bs.modal', function () {
                    }).one('hidden.bs.modal', function () {
                        if (deferred.state() === 'pending') {
                            deferred.reject();
                        }
                    }).modal('show');
                });
            },
            "showAudioDialog": function (layoutInfo, value) {
                var dom = $.summernote.core.dom;
                var layoutInfoCustom = dom.makeLayoutInfo(layoutInfo.target);
                var $dialog = layoutInfoCustom.dialog(),
                    $editable = layoutInfoCustom.editable();
                var header = $dialog.find('.note-audio-dialog').find('.modal-header');
                header.find('.close').attr('aria-hidden', false);
                handler.invoke('editor.saveRange', $editable);
                this.audioDialog($dialog).then(function (data) {
                    handler.invoke('editor.restoreRange', $editable);
                    let url = window.location.origin + '/web/content/' + data.id + '?autoplay=0&rel=0';
                    let audioUrl = `
                    <div class="media_iframe_video iframe_custom">
                      <audio controls="true" class="embed-responsive-item" contenteditable="false">
                        <source src="${url}" type="audio/webm" />
                      </audio>
                    </div><br/>`;
                    let textVal = $dialog.parent().parent().children(':first-child').val();
                    textVal = textVal + audioUrl
                    $dialog.parent().parent().children(':first-child').val(textVal);
                    $editable.append(audioUrl);
                }).fail(function () {
                    handler.invoke('editor.restoreRange', $editable);
                });
            },
            "audioDialog": function ($dialog) {
                return $.Deferred(function (deferred) {
                    var $audioDialog = $dialog.find('.note-audio-dialog');
                    $audioDialog.one('shown.bs.modal', function () {
                    }).one('hidden.bs.modal', function () {
                        if (deferred.state() === 'pending') {
                            deferred.reject();
                        }
                    }).modal('show');
                });
            },
        },
        dialogs: {
            videoDialog: function (lang, options) {
                var body =
                    `<div id="container">
                    <div class="videos" style="display:flex;justify-content:space-between;margin-bottom:10px;flex-wrap:wrap;">
                      <video class="gum" autoplay muted playsinline style="width:49%"></video>
                      <video class="note-video-input" autoplay playsinline style="width:49%;background: #222;"></video>
                    </div>
                    <div>
                        <button class="note-record-btn">Start Recording</button>
                        <button class="note-video-play" disabled>Play</button>
                        <button class="note-video-download" disabled>Download</button>
                    </div>
                </div>
                `;
                var footer = '<button href="#" class="btn btn-primary note-video-btn" disabled>' + 'Add Video' + '</button>';
                return tmpl.dialog('note-video-dialog', 'Add Video', body, footer);
            },
            audioDialog: function (lang, options) {
                var body =
                    `<div id="container">
                  <div>
                    <audio class="recorded" autoplay playsinline class="note-audio-input" controls></audio>
                  </div>
                  <div style="margin-top: 20px;margin-left: 10px;">
                      <button class="note-record-audio-btn">Start Recording</button>
                      <button class="note-audio-play" disabled>Play</button>
                      <button class="note-audio-download" disabled>Download</button>
                  </div>
              </div>
              `;
                var footer = '<button href="#" class="btn btn-primary note-audio-btn" disabled>' + 'Add Audio' + '</button>';
                return tmpl.dialog('note-audio-dialog', 'Add Audio', body, footer);
            }
        }
    });

    $.summernote.pluginEvents.showVideoDialog = function (event, editor, layoutInfo, sorted) {
        var $editable = layoutInfo.editable();
        var $selection = layoutInfo.handle().find('.note-control-selection');
        topBus.trigger('video_dialog_demand', {
            $editable: $editable,
            media: $selection.data('target'),
        });
    };
    $.summernote.pluginEvents.showAudioDialog = function (event, editor, layoutInfo, sorted) {
        var $editable = layoutInfo.editable();
        var $selection = layoutInfo.handle().find('.note-control-selection');
        topBus.trigger('audio_dialog_demand', {
            $editable: $editable,
            media: $selection.data('target'),
        });
    };
    summernoteManager.include({
        init: function (parent) {
            var res = this._super.apply(this, arguments);
            topBus.on('video_dialog_demand', this, this._onVideoDialogDemand);
            topBus.on('audio_dialog_demand', this, this._onAudioDialogDemand);
            return res;
        },
        destroy: function () {
            topBus.off('video_dialog_demand', this, this._onVideoDialogDemand);
            topBus.off('audio_dialog_demand', this, this._onAudioDialogDemand);
            return this._super.apply(this, arguments);
        },
        _onVideoDialogDemand: function (data) {
            if (data.__alreadyDone) {
                return;
            }
            data.__alreadyDone = true;
            var videoDialog = new weWidgets.VideoDialog(this,
                data.media,
                data.$editable,
            );
            videoDialog.open();
        },
        _onAudioDialogDemand: function (data) {
            if (data.__alreadyDone) {
                return;
            }
            data.__alreadyDone = true;
            var audioDialog = new weWidgets.AudioDialog(this,
                data.media,
                data.$editable,
            );
            audioDialog.open();
        },
    })
});

