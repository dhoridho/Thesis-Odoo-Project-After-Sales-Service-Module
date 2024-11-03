from odoo import fields, models, api
from odoo.addons.website.tools import get_video_embed_code



class YoutubePopupVideoWizard(models.TransientModel):
	_name = 'youtube.popup.video.wizard'

	name = fields.Char('Name')
	youtube_url = fields.Char('Video URL')
	embed_code = fields.Char(compute="_compute_embed_code")
	youtube_iframe = fields.Html('Preview')

	@api.depends('youtube_url')
	def _compute_embed_code(self):
		for data in self:
			data.embed_code = get_video_embed_code(data.youtube_url)


	@api.model
	def default_get(self, default_fields):
		vals = super(YoutubePopupVideoWizard, self).default_get(default_fields)
		active_id = self._context.get('active_id')
		data = self.env['survey.user_input.line'].browse([active_id])
		if data.answer_type == 'video' and not data.youtube_url:
			raise ValidationError(_('Video is required.'))
		vals['youtube_url'] = data.youtube_url
		return vals

   